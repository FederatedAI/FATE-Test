import glob as glob_
import importlib
import os
import time
import uuid
from pathlib import Path

import click

from fate_test._client import Clients
from fate_test._config import Config
from fate_test._flow_client import DataProgress, UploadDataResponse, QueryJobResponse, Status
from fate_test._io import echo, LOGGER, set_logger
from fate_test._parser import (Testsuite, BenchmarkSuite, PerformanceSuite, FinalStatus,
                               DATA_LOAD_HOOK, CONF_LOAD_HOOK, DSL_LOAD_HOOK, Data)


def _big_data_task(includes, guest_data_size, host_data_size, guest_feature_num, host_feature_num, host_data_type,
                   config_inst, encryption_type, match_rate, sparsity, force, split_host, output_path):
    from fate_test.scripts import generate_mock_data

    def _find_testsuite_files(path):
        suffix = ["testsuite.yaml", "benchmark.yaml", "performance.yaml", "llmsuite.yaml"]
        if isinstance(path, str):
            path = Path(path)
        if path.is_file():
            if path.name.endswith(suffix[0]) or path.name.endswith(suffix[1]) or path.name.endswith(suffix[2]):
                paths = [path]
            else:
                LOGGER.warning(f"{path} is file, but not end with `{suffix}`, skip")
                paths = []
            return [p.resolve() for p in paths]
        else:
            os.path.abspath(path)
            paths = glob_.glob(f"{path}/*{suffix[0]}") + glob_.glob(f"{path}/*{suffix[1]}")
            return [Path(p) for p in paths]

    for include in includes:
        if isinstance(include, str):
            include_paths = Path(include)
            include_paths = _find_testsuite_files(include_paths)
            for include_path in include_paths:
                generate_mock_data.get_big_data(guest_data_size, host_data_size, guest_feature_num, host_feature_num,
                                                include_path, host_data_type, config_inst, encryption_type,
                                                match_rate, sparsity, force, split_host, output_path)


def _load_testsuites(includes, excludes, glob, provider=None, suffix="testsuite.yaml", suite_type="testsuite"):
    def _find_testsuite_files(path):
        if isinstance(path, str):
            path = Path(path)
        if path.is_file():
            if path.name.endswith(suffix):
                paths = [path]
            else:
                LOGGER.warning(f"{path} is file, but not end with `{suffix}`, skip")
                paths = []
        else:
            paths = path.glob(f"**/*{suffix}")
        return [p.resolve() for p in paths]

    excludes_set = set()
    for exclude in excludes:
        excludes_set.update(_find_testsuite_files(exclude))

    suite_paths = set()
    for include in includes:
        if isinstance(include, str):
            include = Path(include)

        # glob
        if glob is not None and include.is_dir():
            include_list = include.glob(glob)
        else:
            include_list = [include]
        for include_path in include_list:
            for suite_path in _find_testsuite_files(include_path):
                if suite_path not in excludes_set:
                    suite_paths.add(suite_path)
    suites = []
    for suite_path in suite_paths:
        try:
            if suite_type == "testsuite":
                suite = Testsuite.load(suite_path.resolve(), provider)
            elif suite_type == "benchmark":
                suite = BenchmarkSuite.load(suite_path.resolve())
            elif suite_type == "performance":
                suite = PerformanceSuite.load(suite_path.resolve())
            elif suite_type == "llmsuite":
                from ruamel import yaml
                from fate_llm.evaluate.utils import LlmSuite
                suite = LlmSuite.load(suite_path.resolve())
                # add data, if any provided
                with suite_path.resolve().open("r") as f:
                    suite_config = yaml.safe_load(f)
                dataset = []
                for d in suite_config.get("data", {}):
                    d = DATA_LOAD_HOOK.hook(d)
                    dataset.append(Data.load(d, suite_path, for_upload=False))
                suite.dataset = dataset
                # add job status
                suite_status = {}
                for pair in suite.pairs:
                    for job in pair.jobs:
                        if not job.evaluate_only:
                            suite_status[f"{pair.pair_name}-{job.job_name}"] = FinalStatus(f"{pair.pair_name}-{job.job_name}")
                suite._final_status = suite_status
            else:
                raise ValueError(f"Unsupported suite type: {suite_type}. Only accept type 'testsuite' or 'benchmark'.")
        except Exception as e:
            echo.stdout(f"load suite {suite_path} failed: {e}")
        else:
            suites.append(suite)
    return suites


@LOGGER.catch
def _bind_data(clients: Clients, suite, config: Config):
    if not suite.dataset:
        return
    with click.progressbar(length=len(suite.dataset),
                           label="dataset",
                           show_eta=False,
                           show_pos=True,
                           width=24) as bar:
        for i, data in enumerate(suite.dataset):
            data.update(config)
            data_progress = DataProgress(f"{data.role_str}<-{data.namespace}.{data.table_name}")

            def update_bar(n_step):
                bar.item_show_func = lambda x: data_progress.show()
                time.sleep(0.1)
                bar.update(n_step)

            def _call_back(resp):
                if isinstance(resp, Status):
                    echo.file(f"[table] bind: {resp}")
                update_bar(0)

            try:
                echo.stdout_newline()
                status = clients[data.role_str].bind_table(data,_call_back)
                time.sleep(1)
                if status != 'success':
                    raise RuntimeError(f"binding {i + 1}th data for {suite.path} {status}")
                bar.update(1)

            except Exception:
                exception_id = str(uuid.uuid1())
                echo.file(f"exception({exception_id})")
                LOGGER.exception(f"exception id: {exception_id}")
                echo.echo(f"bind {i + 1}th data {data.config} to {data.role_str} fail, exception_id: {exception_id}")
                # raise RuntimeError(f"exception uploading {i + 1}th data") from e



@LOGGER.catch
def _upload_data(clients: Clients, suite, config: Config, output_path=None, **kwargs):
    if kwargs.get("partitions") is not None:
        _update_data_config(suite, partitions=kwargs.get("partitions"))
    with click.progressbar(length=len(suite.dataset),
                           label="dataset",
                           show_eta=False,
                           show_pos=True,
                           width=24) as bar:
        for i, data in enumerate(suite.dataset):
            data.update(config)
            data_progress = DataProgress(f"{data.role_str}<-{data.namespace}.{data.table_name}")

            def update_bar(n_step):
                bar.item_show_func = lambda x: data_progress.show()
                time.sleep(0.1)
                bar.update(n_step)

            def _call_back(resp):
                if isinstance(resp, UploadDataResponse):
                    data_progress.submitted(resp.job_id)
                    echo.file(f"[dataset]{resp.job_id}")
                if isinstance(resp, QueryJobResponse):
                    data_progress.update()
                update_bar(0)

            try:
                echo.stdout_newline()
                # role, idx = data.role_str.lower().split("_")
                # party_id = config.role[role][int(idx)]
                status = clients[data.role_str].transform_local_file_to_dataframe(data,
                                                                                  _call_back,
                                                                                  output_path)
                time.sleep(1)
                data_progress.update()
                if status != 'success':
                    raise RuntimeError(f"uploading {i + 1}th data for {suite.path} {status}")
                bar.update(1)

                """if _config.data_switch:
                    from fate_test.scripts import generate_mock_data

                    generate_mock_data.remove_file(data_path)"""
            except Exception:
                exception_id = str(uuid.uuid1())
                echo.file(f"exception({exception_id})")
                LOGGER.exception(f"exception id: {exception_id}")
                echo.echo(f"upload {i + 1}th data {data.config} to {data.role_str} fail, exception_id: {exception_id}")
                # raise RuntimeError(f"exception uploading {i + 1}th data") from e


def _delete_data(clients: Clients, suite: Testsuite):
    with click.progressbar(length=len(suite.dataset),
                           label="delete ",
                           show_eta=False,
                           show_pos=True,
                           width=24) as bar:
        for data in suite.dataset:
            # noinspection PyBroadException
            try:
                table_name = data.config['table_name'] if data.config.get(
                    'table_name', None) is not None else data.config.get('name')
                bar.item_show_func = \
                    lambda x: f"delete table: name={table_name}, namespace={data.config['namespace']}"
                clients[data.role_str].delete_data(data)
            except Exception:
                LOGGER.exception(
                    f"delete failed: name={table_name}, namespace={data.config['namespace']}")

            time.sleep(0.5)
            bar.update(1)
            echo.stdout_newline()


def _load_module_from_script(script_path):
    module_name = str(script_path).split("/", -1)[-1].split(".")[0]
    loader = importlib.machinery.SourceFileLoader(module_name, str(script_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _set_namespace(data_namespace_mangling, namespace):
    Path(f"logs/{namespace}").mkdir(exist_ok=True, parents=True)
    set_logger(f"logs/{namespace}/exception.log")
    echo.set_file(click.open_file(f'logs/{namespace}/stdout', "a"))

    if data_namespace_mangling:
        echo.echo(f"add data_namespace_mangling: _{namespace}")
        DATA_LOAD_HOOK.add_extend_namespace_hook(namespace)
        CONF_LOAD_HOOK.add_extend_namespace_hook(namespace)


def _add_replace_hook(replace):
    DATA_LOAD_HOOK.add_replace_hook(replace)
    CONF_LOAD_HOOK.add_replace_hook(replace)
    DSL_LOAD_HOOK.add_replace_hook(replace)


def _update_data_path(suite, output_dir):
    for data in suite.dataset:
        data_name = os.path.basename(data.file)
        data_file_path = os.path.join(str(output_dir), data_name)
        data.file = data_file_path
        data.config['file'] = data_file_path


def _update_data_config(suite, partitions=None):
    if partitions is not None:
        for data in suite.dataset:
            data.config['partitions'] = partitions
            data.partitions = partitions


def _obtain_model_output_path(config, job_id, task_name, client, role, party_id):

    output_path = os.path.join(config.data_base_dir, "fate_flow",
                             "model", job_id, role, party_id, task_name, "0", "output", "output_model")
    return output_path

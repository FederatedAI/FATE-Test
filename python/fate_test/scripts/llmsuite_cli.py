#
#  Copyright 2019 The FATE Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import time
import uuid
from datetime import timedelta
from inspect import signature

import click

from fate_test._client import Clients
from fate_test._config import Config
from fate_test._io import LOGGER, echo
from fate_test._parser import record_non_success_jobs, non_success_summary
from fate_test.scripts._options import SharedOptions
from fate_test.scripts._utils import _load_testsuites, _load_module_from_script, _bind_data
from fate_test.utils import extract_job_status


@click.command("llmsuite")
@click.option('-i', '--include', required=False, type=click.Path(exists=True), multiple=True,
              metavar="<include>",
              help="include *llmsuite.yaml under these paths")
@click.option('-e', '--exclude', type=click.Path(exists=True), multiple=True,
              help="exclude *llmsuite.yaml under these paths")
@click.option('-a', '--algorithm-suite', type=str, multiple=True,
              help="run built-in algorithm suite, if given, ignore include/exclude")
@click.option('-p', '--task-cores', type=int, help="processors per node")
@click.option('-m', '--timeout', type=int,
              help="maximum running time of job")
@click.option("-g", '--glob', type=str,
              help="glob string to filter sub-directory of path specified by <include>")
@click.option("--provider", type=str,
              help="Select the fate version, for example: fate@2.0-beta")
@click.option('--eval-config', type=click.Path(exists=True),
              help='Path to FATE Llm evaluation config. If none, use default config.')
@click.option('--skip-evaluate', is_flag=True, default=False,
              help="skip evaluation after training model")
@click.option("--skip-data", is_flag=True, default=False,
              help="skip binding table specified in llmsuite")
@click.option("--data-only", is_flag=True, default=False,
              help="bind data only")
@SharedOptions.get_shared_options(hidden=True)
@click.pass_context
def run_llmsuite(ctx, include, exclude, algorithm_suite, glob, provider, task_cores, timeout, eval_config, skip_evaluate,
                 skip_data, data_only, **kwargs):
    """
    process llmsuite
    """
    ctx.obj.update(**kwargs)
    ctx.obj.post_process()
    config_inst = ctx.obj["config"]
    if ctx.obj["engine_run"][0] is not None:
        config_inst.update_conf(engine_run=dict(ctx.obj["engine_run"]))
    if task_cores is not None:
        config_inst.update_conf(task_cores=task_cores)
    if timeout is not None:
        config_inst.update_conf(timeout=timeout)


    namespace = ctx.obj["namespace"]
    yes = ctx.obj["yes"]
    data_namespace_mangling = ctx.obj["namespace_mangling"]
    # prepare output dir and json hooks
    # _add_replace_hook(replace)
    echo.welcome()
    echo.echo(f"llmsuite namespace: {namespace}", fg='red')
    echo.echo("loading llmsuites:")
    if algorithm_suite:
        algorithm_suite_path_dict = {"pellm": os.path.join(config_inst.fate_base, "fate_llm", "examples", "pellm")}
        # algorithm_suite_path_dict = {"pellm": os.path.join(config_inst.fate_base,"examples", "pellm")}
        suite_paths = []
        for alg in algorithm_suite:
            algorithm_suite_path = algorithm_suite_path_dict.get(alg, None)
            if algorithm_suite_path is None:
                echo.echo(f"algorithm suite {alg} not found", fg='red')
            else:
                suite_paths.append(algorithm_suite_path)
        suites = _load_testsuites(includes=suite_paths, excludes=[], glob=None, provider=provider,
                                  suffix="llmsuite.yaml", suite_type="llmsuite")
    elif len(include) > 0:
        suites = _load_testsuites(includes=include, excludes=exclude, glob=glob, provider=provider,
                                  suffix="llmsuite.yaml", suite_type="llmsuite")
        for suite in suites:
            echo.echo(f"\tllm suite count: ({len(suite.pairs)}) from {suite.path}")
        if not yes and not click.confirm("running?"):
            return
    else:
        return

    echo.stdout_newline()
    # with Clients(config_inst) as client:
    client = Clients(config_inst)
    from fate_llm.evaluate.utils import llm_evaluator
    llm_evaluator.init_tasks()
    for i, suite in enumerate(suites):
        # noinspection PyBroadException
        try:
            start = time.time()
            echo.echo(f"[{i + 1}/{len(suites)}]start at {time.strftime('%Y-%m-%d %X')} {suite.path}", fg='red')
            os.environ['enable_pipeline_job_info_callback'] = '1'
            if not skip_data:
                try:
                    _bind_data(client, suite, config_inst)
                except Exception as e:
                    raise RuntimeError(f"exception occur while uploading data for {suite.path}") from e
            if data_only:
                continue
            try:
                # eval_config_dict = {}
                if not eval_config:
                    from fate_llm.evaluate.utils.config import default_eval_config
                    eval_config = default_eval_config()
                    if not os.path.exists(eval_config):
                        eval_config = None
                _run_llmsuite_pairs(config_inst, suite, namespace, data_namespace_mangling, client,
                                    skip_evaluate, eval_config)
            except Exception as e:
                raise RuntimeError(f"exception occur while running llmsuite jobs for {suite.path}") from e

            echo.echo(f"[{i + 1}/{len(suites)}]elapse {timedelta(seconds=int(time.time() - start))}", fg='red')
        except Exception:
            exception_id = uuid.uuid1()
            echo.echo(f"exception in {suite.path}, exception_id={exception_id}")
            LOGGER.exception(f"exception id: {exception_id}")
        finally:
            echo.stdout_newline()
        suite_file = str(suite.path).split("/")[-1]
        record_non_success_jobs(suite, suite_file)
    non_success_summary()
    echo.farewell()
    echo.echo(f"llmsuite namespace: {namespace}", fg='red')


@LOGGER.catch
def _run_llmsuite_pairs(config: Config, suite, namespace: str,
                        data_namespace_mangling: bool, clients: Clients, skip_evaluate: bool, eval_conf: str,
                        output_path: str = None):
    from fate_llm.evaluate.scripts.eval_cli import run_job_eval
    client = clients['guest_0']
    guest_party_id = config.parties.role_to_party("guest")[0]
    pair_n = len(suite.pairs)
    # fate_base = config.fate_base
    # PYTHONPATH = os.environ.get('PYTHONPATH') + ":" + os.path.join(fate_base, "python")
    # os.environ['PYTHONPATH'] = PYTHONPATH
    suite_results = dict()
    for i, pair in enumerate(suite.pairs):
        echo.echo(f"Running [{i + 1}/{pair_n}] group: {pair.pair_name}")
        job_n = len(pair.jobs)
        # time_dict = dict()
        job_results = dict()
        for j, job in enumerate(pair.jobs):
            echo.echo(f"Running [{j + 1}/{job_n}] job: {job.job_name}")

            def _raise(err_msg, status="failed", job_id=None, event=None, time_elapsed=None):
                exception_id = str(uuid.uuid1())
                if status is not None:
                    suite.update_status(pair_name=pair.pair_name, job_name=job_name, job_id=job_id, exception_id=exception_id, status=status,
                                        event=event, time_elapsed=time_elapsed)
                echo.file(f"exception({exception_id}), error message:\n{err_msg}")
            # evaluate_only
            if job.evaluate_only and not skip_evaluate:
                echo.echo(f"Evaluating job: {job.job_name} with tasks: {job.tasks}")
                job_results[job.job_name] = run_job_eval(job, eval_conf)
            # run pipeline job then evaluate
            else:
                try:
                    job_name, script_path, conf_path = job.job_name, job.script_path, job.conf_path
                    param = Config.load_from_file(conf_path)
                    mod = _load_module_from_script(script_path)
                    input_params = signature(mod.main).parameters

                    try:
                        # pipeline should return pretrained model path
                        pretrained_model_path = _run_mod(mod, input_params, config, param,
                                                         namespace, data_namespace_mangling)
                        job.pretrained_model_path = pretrained_model_path
                        job_info = os.environ.get("pipeline_job_info")
                        job_id, status, time_elapsed, event = extract_job_status(job_info, client, guest_party_id)
                        suite.update_status(pair_name=pair.pair_name, job_name=job_name,
                                            job_id=job_id, status=status,
                                            time_elapsed=time_elapsed,
                                            event=event)
                    except Exception as e:
                        job_info = os.environ.get("pipeline_job_info")
                        if job_info is None:
                            job_id, status, time_elapsed, event = None, 'failed', None, None
                        else:
                            job_id, status, time_elapsed, event = extract_job_status(job_info, client, guest_party_id)
                        _raise(e, job_id=job_id, status=status, event=event, time_elapsed=time_elapsed)
                        os.environ.pop("pipeline_job_info")
                        continue
                except Exception as e:
                    _raise(f"pipeline failed: {e}", status="not submitted")
                    continue
                if not skip_evaluate:
                    try:
                        model_task_name = "nn_0"
                        if job.model_task_name:
                            model_task_name = job.model_task_name
                        from lm_eval.utils import apply_template
                        peft_path = apply_template(job.peft_path_format,
                                                   {"fate_base": config.fate_base,
                                                    "job_id": job_id[0],
                                                    "party_id": guest_party_id,
                                                    "model_task_name": model_task_name}
                                                   )
                        job.peft_path = peft_path
                        echo.echo(f"Evaluating job: {job.job_name} with tasks: {job.tasks}")
                        result = run_job_eval(job, eval_conf)
                        job_results[job_name] = result
                    except Exception as e:
                        _raise(f"evaluate failed: {e}", status=None)
                os.environ.pop("pipeline_job_info")
        suite_results[pair.pair_name] = job_results

    from fate_llm.evaluate.utils.llm_evaluator import aggregate_table
    suite_writers = aggregate_table(suite_results)
    for pair_name, pair_writer in suite_writers.items():
        echo.sep_line()
        echo.echo(f"Pair: {pair_name}")
        echo.sep_line()
        echo.echo(pair_writer.dumps())
        echo.stdout_newline()

    if output_path:
        with open(output_path, 'w') as f:
            for pair_name, pair_writer in suite_writers.items():
                pair_writer.dumps(f)


def _run_mod(mod, input_params, config, param, namespace, data_namespace_mangling):
    if len(input_params) == 1:
        return mod.main(param=param)
    elif len(input_params) == 2:
        return mod.main(config=config, param=param)
    # pipeline script
    elif len(input_params) == 3:
        if data_namespace_mangling:
            return mod.main(config=config, param=param, namespace=f"_{namespace}")
        else:
            return mod.main(config=config, param=param)
    else:
        return mod.main()

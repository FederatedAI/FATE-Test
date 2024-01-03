import os
import re
import uuid

import click
from ruamel import yaml

from fate_test._client import Clients
from fate_test._config import Config
from fate_test._io import LOGGER, echo
from fate_test.scripts._options import SharedOptions
from fate_test.scripts._utils import _load_testsuites, _delete_data, _big_data_task, _upload_data, _update_data_path


@click.group(name="data")
def data_group():
    """
    upload or delete data in suite config files
    """
    ...


@data_group.command("upload")
@click.option('-i', '--include', required=False, type=click.Path(exists=True), multiple=True, metavar="<include>",
              help="include *benchmark.yaml under these paths")
@click.option('-e', '--exclude', type=click.Path(exists=True), multiple=True,
              help="exclude *benchmark.yaml under these paths")
@click.option("-t", "--config-type", type=click.Choice(["min_test", "all_examples"]), default="min_test",
              help="config file")
@click.option('-g', '--glob', type=str,
              help="glob string to filter sub-directory of path specified by <include>")
@click.option('-s', '--suite-type', required=False, type=click.Choice(["testsuite", "benchmark", "performance"]),
              default="testsuite",
              help="suite type")
@click.option('-r', '--role', type=str, default='all', help="role to process, default to `all`. "
                                                            "use option likes: `guest_0`, `host_0`, `host`")
@SharedOptions.get_shared_options(hidden=True)
@click.pass_context
def upload(ctx, include, exclude, glob, suite_type, role, config_type, **kwargs):
    """
    upload data defined in suite config files
    """
    ctx.obj.update(**kwargs)
    ctx.obj.post_process()
    namespace = ctx.obj["namespace"]
    config_inst = ctx.obj["config"]
    if ctx.obj["extend_sid"] is not None:
        config_inst.extend_sid = ctx.obj["extend_sid"]
    """if ctx.obj["auto_increasing_sid"] is not None:
        config_inst.auto_increasing_sid = ctx.obj["auto_increasing_sid"]"""
    yes = ctx.obj["yes"]
    echo.welcome()
    echo.echo(f"testsuite namespace: {namespace}", fg='red')
    client = Clients(config_inst)
    if len(include) != 0:
        echo.echo("loading testsuites:")
        if suite_type == "benchmark":
            suffix = "benchmark.yaml"
        elif suite_type == "testsuite":
            suffix = "testsuite.yaml"
        elif suite_type == "performance":
            suffix = "performance.yaml"
        else:
            raise ValueError(f"unknown suite type: {suite_type}")
        suites = _load_testsuites(includes=include, excludes=exclude, glob=glob,
                                  suffix=suffix, suite_type=suite_type)
        for suite in suites:
            if role != "all":
                suite.dataset = [d for d in suite.dataset if re.match(d.role_str, role)]
            echo.echo(f"\tdataset({len(suite.dataset)}) {suite.path}")
        if not yes and not click.confirm("running?"):
            return

        for suite in suites:
            _upload_data(client, suite, config_inst, partitions=ctx.obj["partitions"])
    else:
        config = get_config(config_inst)
        if config_type == 'min_test':
            config_file = config.min_test_data_config
        else:
            config_file = config.all_examples_data_config

        with open(config_file, 'r', encoding='utf-8') as f:
            upload_data = yaml.safe_load(f.read())

        echo.echo(f"\tdataset({len(upload_data['data'])}) {config_file}")
        if not yes and not click.confirm("running?"):
            return
        _upload_data(client, upload_data, config_inst)
        echo.farewell()
        echo.echo(f"testsuite namespace: {namespace}", fg='red')


@data_group.command("delete")
@click.option('-i', '--include', required=True, type=click.Path(exists=True), multiple=True, metavar="<include>",
              help="include *benchmark.yaml under these paths")
@click.option('-e', '--exclude', type=click.Path(exists=True), multiple=True,
              help="exclude *benchmark.yaml under these paths")
@click.option('-g', '--glob', type=str,
              help="glob string to filter sub-directory of path specified by <include>")
@click.option('-s', '--suite-type', required=True, type=click.Choice(["testsuite", "benchmark"]), help="suite type")
@SharedOptions.get_shared_options(hidden=True)
@click.pass_context
def delete(ctx, include, exclude, glob, yes, suite_type, **kwargs):
    """
    delete data defined in suite config files
    """
    ctx.obj.update(**kwargs)
    ctx.obj.post_process()
    namespace = ctx.obj["namespace"]
    config_inst = ctx.obj["config"]
    echo.welcome()
    echo.echo(f"testsuite namespace: {namespace}", fg='red')
    echo.echo("loading testsuites:")
    suffix = "benchmark.yaml" if suite_type == "benchmark" else "testsuite.yaml"

    suites = _load_testsuites(includes=include, excludes=exclude, glob=glob,
                              suffix=suffix, suite_type=suite_type)
    if not yes and not click.confirm("running?"):
        return

    for suite in suites:
        echo.echo(f"\tdataset({len(suite.dataset)}) {suite.path}")
    if not yes and not click.confirm("running?"):
        return
    client = Clients(config_inst)
    for i, suite in enumerate(suites):
        _delete_data(client, suite)
    echo.farewell()
    echo.echo(f"testsuite namespace: {namespace}", fg='red')


@data_group.command("generate")
@click.option('-i', '--include', required=True, type=click.Path(exists=True), multiple=True, metavar="<include>",
              help="include *testsuite.yaml / *benchmark.yaml under these paths")
@click.option('-ht', '--host-data-type', default='tag_value', type=click.Choice(['dense', 'tag', 'tag_value']),
              help="Select the format of the host data")
@click.option('-p', '--encryption-type', type=click.Choice(['sha256', 'md5']),
              help="ID encryption method, choose between sha256 and md5")
@click.option('-m', '--match-rate', default=1.0, type=float,
              help="Intersection rate relative to guest, between [0, 1]")
@click.option('-s', '--sparsity', default=0.2, type=float,
              help="The sparsity of tag data, The value is between (0-1)")
@click.option('-ng', '--guest-data-size', type=int, default=10000,
              help="Set guest data set size, not less than 100")
@click.option('-nh', '--host-data-size', type=int,
              help="Set host data set size, not less than 100")
@click.option('-fg', '--guest-feature-num', type=int, default=20,
              help="Set guest feature dimensions")
@click.option('-fh', '--host-feature-num', type=int, default=200,
              help="Set host feature dimensions; the default is equal to the number of guest's size")
@click.option('-o', '--output-path', type=click.Path(exists=True),
              help="Customize the output path of generated data")
@click.option('--force', is_flag=True, default=False,
              help="Overwrite existing file")
@click.option('--split-host', is_flag=True, default=False,
              help="Divide the amount of host data equally among all the host tables in TestSuite")
@click.option('--upload-data', is_flag=True, default=False,
              help="Generated data will be uploaded")
@click.option('--remove-data', is_flag=True, default=False,
              help="The generated data will be deleted")
# @click.option('--use-local-data', is_flag=True, default=False,
#               help="The existing data of the server will be uploaded, This parameter is not recommended for "
#                    "distributed applications")
# @click.option('--parallelize', is_flag=True, default=False,
#               help="It is directly used to upload data, and will not generate data")
@SharedOptions.get_shared_options(hidden=True)
@click.pass_context
def generate(ctx, include, host_data_type, encryption_type, match_rate, sparsity, guest_data_size,
             host_data_size, guest_feature_num, host_feature_num, output_path, force, split_host, upload_data,
             **kwargs):
    """
    create data defined in suite config files
    """
    ctx.obj.update(**kwargs)

    ctx.obj.post_process()
    namespace = ctx.obj["namespace"]
    config_inst = ctx.obj["config"]
    if ctx.obj["extend_sid"] is not None:
        config_inst.extend_sid = ctx.obj["extend_sid"]
    """if ctx.obj["auto_increasing_sid"] is not None:
        config_inst.auto_increasing_sid = ctx.obj["auto_increasing_sid"]
    if parallelize and upload_data:
        upload_data = False
    """
    yes = ctx.obj["yes"]
    echo.welcome()
    echo.echo(f"testsuite namespace: {namespace}", fg='red')
    echo.echo("loading testsuites:")
    if host_data_size is None:
        host_data_size = guest_data_size
    suites = _load_testsuites(includes=include, excludes=tuple(), glob=None)
    suites += _load_testsuites(includes=include, excludes=tuple(), glob=None,
                               suffix="benchmark.yaml", suite_type="benchmark")
    suites += _load_testsuites(includes=include, excludes=tuple(), glob=None,
                               suffix="performance.yaml", suite_type="performance")
    for suite in suites:
        if upload_data:
            echo.echo(f"\tdataget({len(suite.dataset)}) dataset({len(suite.dataset)}) {suite.path}")
        else:
            echo.echo(f"\tdataget({len(suite.dataset)}) {suite.path}")
    if not yes and not click.confirm("running?"):
        return

    _big_data_task(include, guest_data_size, host_data_size, guest_feature_num, host_feature_num, host_data_type,
                   config_inst, encryption_type, match_rate, sparsity, force, split_host, output_path)
    if upload_data:
        client = Clients(config_inst)
        for suite in suites:
            output_dir = output_path if output_path else os.path.abspath(config_inst.cache_directory)
            _update_data_path(suite, output_dir)
            # echo.echo(f"data files: {[data.file for data in suite.dataset]}")
            _upload_data(client, suite, config_inst, partitions=ctx.obj["partitions"])


@data_group.command("query_schema")
@click.option('-cpn', '--component-name', required=True, type=str, help="component name(task name)")
@click.option('-j', '--job-id', required=True, type=str, help="job id")
@click.option('-r', '--role', required=True, type=click.Choice(["guest", "host", "arbiter"]), help="role")
@click.option('-p', '--party-id', required=True, type=str, help="party id")
@click.option('-dn', '--output-data-name', required=True, type=str, help="output data name, e.g. 'train_output_data'")
@SharedOptions.get_shared_options(hidden=True)
@click.pass_context
def query_schema(ctx, component_name, job_id, role, party_id, output_data_name, **kwargs):
    """
    query the meta of the output data of a component
    """
    ctx.obj.update(**kwargs)
    ctx.obj.post_process()
    config_inst = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    echo.echo(f"testsuite namespace: {namespace}", fg='red')
    """
    yes = ctx.obj["yes"]
    echo.welcome()

    if not yes and not click.confirm("running?"):
        return"""
    client = Clients(config_inst)
    query_component_output_data(client, config_inst, component_name, job_id, role, party_id, output_data_name)
    # echo.farewell()
    # echo.echo(f"testsuite namespace: {namespace}", fg='red')


def get_config(conf: Config):
    return conf


def query_component_output_data(clients, config: Config, component_name, job_id, role, party_id, output_data_name):
    roles = config.role
    clients_role = None
    for k, v in roles.items():
        if int(party_id) in v and k == role:
            clients_role = role + "_" + str(v.index(int(party_id)))
    try:
        if clients_role is None:
            raise ValueError(f"party id {party_id} does not exist")

        try:
            table_info = clients[clients_role].output_data_table(job_id=job_id, role=role, party_id=party_id,
                                                                 task_name=component_name,
                                                                 output_data_name=output_data_name)
            table_info = clients[clients_role].table_query(table_name=table_info['name'],
                                                           namespace=table_info['namespace'])
        except Exception as e:
            raise RuntimeError(f"An exception occurred while getting data {clients_role}<-{component_name}") from e

        echo.echo("query_component_output_data result: {}".format(table_info))
        try:
            header = table_info['data']['schema']['header']
        except ValueError as e:
            raise ValueError(f"Obtain header from table error, error msg: {e}")

        result = []
        for idx, header_name in enumerate(header[1:]):
            result.append((idx, header_name))
        echo.echo("Queried header is {}".format(result))
    except Exception:
        exception_id = uuid.uuid1()
        echo.echo(f"exception_id={exception_id}")
        LOGGER.exception(f"exception id: {exception_id}")
    finally:
        echo.stdout_newline()


def download_mnist(base, name, is_train=True):
    import torchvision

    dataset = torchvision.datasets.MNIST(
        root=base.joinpath(".cache"), train=is_train, download=True
    )
    converted_path = base.joinpath(name)
    converted_path.mkdir(exist_ok=True)

    inputs_path = converted_path.joinpath("images")
    inputs_path.mkdir(exist_ok=True)
    targets_path = converted_path.joinpath("targets")
    config_path = converted_path.joinpath("config.yaml")
    filenames_path = converted_path.joinpath("filenames")

    with filenames_path.open("w") as filenames:
        with targets_path.open("w") as targets:
            for idx, (img, target) in enumerate(dataset):
                filename = f"{idx:05d}"
                # save img
                img.save(inputs_path.joinpath(f"{filename}.jpg"))
                # save target
                targets.write(f"{filename},{target}\n")
                # save filenames
                filenames.write(f"{filename}\n")

    config = {
        "type": "vision",
        "inputs": {"type": "images", "ext": "jpg", "PIL_mode": "L"},
        "targets": {"type": "integer"},
    }
    with config_path.open("w") as f:
        yaml.safe_dump(config, f, indent=2, default_flow_style=False)


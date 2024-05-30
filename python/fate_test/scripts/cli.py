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

import click

from fate_test.scripts._options import SharedOptions

commands_alias = {
    "bq": "benchmark-quality",
    "bp": "performance"
}


class MultiCLI(click.MultiCommand):
    def __init__(self, *args, **kwargs):
        super(MultiCLI, self).__init__(*args, **kwargs)
        self.plugin_folder = os.path.dirname(__file__)
        """self._commands =  {
            "config": config_group,
            "suite": run_suite,
            "performance": run_task,
            "benchmark-quality": run_benchmark,
            "data": data_group}
        self._load_extra_commands()
        
    def _load_extra_commands(self):
        from fate_test.scripts.llmsuite_cli import run_llmsuite
        self._commands["llmsuite"] = run_llmsuite"""

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(self.plugin_folder):
            if filename.endswith("_cli.py"):
                rv.append(filename[:-7])
        rv.sort()
        print(f"rv: {rv}")
        return rv

    def get_command(self, ctx, name):
        name = commands_alias.get(name, name).replace("-", "_")
        ns = {}
        fn = os.path.join(self.plugin_folder, name + "_cli.py")
        with open(fn) as f:
            code = compile(f.read(), fn, 'exec')
            eval(code, ns, ns)
        command_name = f"{name}_group" if name in ["data", "config"] else f"run_{name}"
        return ns[command_name]


@click.command(cls=MultiCLI, help="A collection of useful tools to running FATE's test.",
               context_settings=dict(help_option_names=["-h", "--help"]))
@SharedOptions.get_shared_options()
@click.pass_context
def cli(ctx, **kwargs):
    ctx.ensure_object(SharedOptions)
    ctx.obj.update(**kwargs)


if __name__ == '__main__':
    cli(obj=SharedOptions())

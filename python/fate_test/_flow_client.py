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
import json
import os
import time
import typing
from datetime import timedelta
from pathlib import Path

from fate_client.flow_sdk import FlowClient
from fate_test import _config
from fate_test._parser import Data


class FLOWClient(object):

    def __init__(self,
                 address: typing.Optional[str],
                 data_base_dir: typing.Optional[Path],
                 cache_directory: typing.Optional[Path]):
        self.address = address
        self.version = "v2"
        self._client = FlowClient(self.address.split(':')[0], self.address.split(':')[1], self.version)
        self._data_base_dir = data_base_dir
        self._cache_directory = cache_directory
        self.data_size = 0

    def set_address(self, address):
        self.address = address

    def bind_table(self, data: Data, callback=None):
        conf = data.config
        conf['file'] = os.path.join(str(self._data_base_dir), conf.get('file'))
        path = Path(conf.get('file'))
        if not path.exists():
            raise Exception('The file is obtained from the fate flow client machine, but it does not exist, '
                            f'please check the path: {path}')
        response = self._client.table.bind_path(path=str(path),
                                                namespace=data.namespace,
                                                name=data.table_name)
        try:
            if callback is not None:
                callback(response)
                status = str(response['message']).lower()
            else:
                status = response["message"]
            code = response["code"]
            if code != 0:
                raise RuntimeError(f"Return code {code} != 0, bind path failed")
        except BaseException:
            raise ValueError(f"Bind path failed, response={response}")
        return status

    def transform_local_file_to_dataframe(self, data: Data, callback=None, output_path=None):
        #data_warehouse = self.upload_data(data, callback, output_path)
        #status = self.transform_to_dataframe(data.namespace, data.table_name, data_warehouse, callback)
        status = self.upload_file_and_convert_to_dataframe(data, callback, output_path)
        return status

    def upload_file_and_convert_to_dataframe(self, data: Data, callback=None, output_path=None):
        conf = data.config
        # if conf.get("engine", {}) != "PATH":
        if output_path is not None:
            conf['file'] = os.path.join(os.path.abspath(output_path), os.path.basename(conf.get('file')))
        else:
            if _config.data_switch is not None:
                conf['file'] = os.path.join(str(self._cache_directory), os.path.basename(conf.get('file')))
            else:
                conf['file'] = os.path.join(str(self._data_base_dir), conf.get('file'))
        path = Path(conf.get('file'))
        if not path.exists():
            raise Exception('The file is obtained from the fate flow client machine, but it does not exist, '
                            f'please check the path: {path}')
        response = self._client.data.upload_file(file=str(path),
                                                 head=data.head,
                                                 meta=data.meta,
                                                 extend_sid=data.extend_sid,
                                                 partitions=data.partitions,
                                                 namespace=data.namespace,
                                                 name=data.table_name)
        try:
            if callback is not None:
                callback(response)
                status = self._awaiting(response["job_id"], "local", 0)
                status = str(status).lower()
            else:
                status = response["retmsg"]

        except Exception as e:
            raise RuntimeError(f"upload data failed") from e
        job_id = response["job_id"]
        self._awaiting(job_id, "local", 0)
        return status

    def delete_data(self, data: Data):
        try:
            table_name = data.config['table_name'] if data.config.get(
                'table_name', None) is not None else data.config.get('name')
            self._client.table.delete(name=table_name, namespace=data.config['namespace'])
        except Exception as e:
            raise RuntimeError(f"delete data failed") from e

    def output_data_table(self, job_id, role, party_id, task_name, output_data_name):
        data_info = self._output_data_table(job_id=job_id, role=role, party_id=party_id, task_name=task_name)
        output_data_info = data_info.get(output_data_name)[0]
        if output_data_info is None:
            raise ValueError(f"output data name {output_data_name} not found")
        return output_data_info

    def table_query(self, table_name, namespace):
        result = self._table_query(name=table_name, namespace=namespace)
        return result

    def add_notes(self, job_id, role, party_id, notes):
        self._client.job.add_notes(job_id, role=role, party_id=party_id, notes=notes)

    """def add_notes(self, job_id, role, party_id, notes):
        self._add_notes(job_id=job_id, role=role, party_id=party_id, notes=notes)"""

    def _awaiting(self, job_id, role, party_id, callback=None):
        while True:
            response = self._query_job(job_id, role=role, party_id=party_id)
            if response.status.is_done():
                return response.status
            if callback is not None:
                callback(response)
            time.sleep(1)

    def _output_data_table(self, job_id, role, party_id, task_name):
        response = self._client.output.data_table(job_id, role=role, party_id=party_id, task_name=task_name)
        if response.get("code") is not None:
            raise ValueError(f"Query output data table failed, response={response}")

        return response

    def _table_query(self, name, namespace):
        response = self._client.table.query(namespace=namespace, name=name)
        try:
            code = response["code"]
            if code != 0:
                raise ValueError(f"Return code {code}!=0")
            return json.dumps(response["data"], indent=4)
        except BaseException:
            raise ValueError(f"Query table fails, response={response}")

    def _delete_data(self, table_name, namespace):
        response = self._client.table.delete(namespace=namespace, table_name=table_name)
        return response

    def query_task(self, job_id, role, party_id):
        response = self._client.task.query(job_id, role=role, party_id=party_id)
        return response

    def query_job(self, job_id, role, party_id):
        response = self._client.job.query(job_id, role=role, party_id=party_id)
        return QueryJobResponse(response)

    def _query_job(self, job_id, role, party_id):
        response = self._client.job.query(job_id, role, party_id)
        return QueryJobResponse(response)

    def get_version(self):
        response = self._client.provider.query(name="fate")
        try:
            retcode = response['code']
            retmsg = response['message']
            if retcode != 0 or retmsg != 'success':
                raise RuntimeError(f"get version error: {response}")
            fate_version = response["data"][0]["provider_name"]
        except Exception as e:
            raise RuntimeError(f"get version error: {response}") from e
        return fate_version

    """def _add_notes(self, job_id, role, party_id, notes):
        data = dict(job_id=job_id, role=role, party_id=party_id, notes=notes)
        response = AddNotesResponse(self._post(url='job/update', json=data))
        return response

    def _table_bind(self, data):
        response = self._post(url='table/bind', json=data)
        try:
            retcode = response['retcode']
            retmsg = response['retmsg']
            if retcode != 0 or retmsg != 'success':
                raise RuntimeError(f"table bind error: {response}")
        except Exception as e:
            raise RuntimeError(f"table bind error: {response}") from e
        return response
    """


class Status(object):
    def __init__(self, status: str):
        self.status = status

    def is_done(self):
        return self.status.lower() in ['complete', 'success', 'canceled', 'failed', "timeout"]

    def is_success(self):
        return self.status.lower() in ['complete', 'success']

    def __str__(self):
        return self.status

    def __repr__(self):
        return self.__str__()


class QueryJobResponse(object):
    def __init__(self, response: dict):
        try:
            status = Status(response.get('data')[0]["status"])
            progress = response.get('data')[0]['progress']
            elapsed = response.get('data')[0]['elapsed']
            if elapsed is not None:
                elapsed = elapsed / 1000
        except Exception as e:
            raise RuntimeError(f"query job error, response: {json.dumps(response, indent=4)}") from e
        self.status = status
        self.progress = progress
        self.elapsed = elapsed


class UploadDataResponse(object):
    def __init__(self, response: dict):
        try:
            self.job_id = response["jobId"]
        except Exception as e:
            raise RuntimeError(f"upload error, response: {response}") from e
        self.status: typing.Optional[Status] = None


class AddNotesResponse(object):
    def __init__(self, response: dict):
        try:
            retcode = response['retcode']
            retmsg = response['retmsg']
            if retcode != 0 or retmsg != 'success':
                raise RuntimeError(f"add notes error: {response}")
        except Exception as e:
            raise RuntimeError(f"add notes error: {response}") from e


class DataProgress(object):
    def __init__(self, role_str):
        self.role_str = role_str
        self.start = time.time()
        self.show_str = f"[{self.elapse()}] {self.role_str}"
        self.job_id = ""

    def elapse(self):
        return f"{timedelta(seconds=int(time.time() - self.start))}"

    def submitted(self, job_id):
        self.job_id = job_id
        self.show_str = f"[{self.elapse()}]{self.job_id} {self.role_str}"

    def update(self):
        self.show_str = f"[{self.elapse()}]{self.job_id} {self.role_str}"

    def show(self):
        return self.show_str


class JobProgress(object):
    def __init__(self, name):
        self.name = name
        self.start = time.time()
        self.show_str = f"[{self.elapse()}] {self.name}"
        self.job_id = ""
        self.progress_tracking = ""

    def elapse(self):
        return f"{timedelta(seconds=int(time.time() - self.start))}"

    def set_progress_tracking(self, progress_tracking):
        self.progress_tracking = progress_tracking + " "

    def submitted(self, job_id):
        self.job_id = job_id
        self.show_str = f"{self.progress_tracking}[{self.elapse()}]{self.job_id} submitted {self.name}"

    def running(self, status, progress):
        if progress is None:
            progress = 0
        self.show_str = f"{self.progress_tracking}[{self.elapse()}]{self.job_id} {status} {progress:3}% {self.name}"

    def exception(self, exception_id):
        self.show_str = f"{self.progress_tracking}[{self.elapse()}]{self.name} exception({exception_id}): {self.job_id}"

    def final(self, status):
        self.show_str = f"{self.progress_tracking}[{self.elapse()}]{self.job_id} {status} {self.name}"

    def show(self):
        return self.show_str


class JobStatus(object):
    WAITING = 'waiting'
    READY = 'ready'
    RUNNING = "running"
    CANCELED = "canceled"
    TIMEOUT = "timeout"
    FAILED = "failed"
    PASS = "pass"
    SUCCESS = "success"

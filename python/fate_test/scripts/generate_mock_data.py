import hashlib
import os
import random
import sys
import threading
import time
import uuid

import numpy as np
import pandas as pd
from fate_test._config import Config
from fate_test._io import echo, LOGGER
from ruamel import yaml

sys.setrecursionlimit(1000000)


class data_progress:
    def __init__(self, down_load, time_start):
        self.time_start = time_start
        self.down_load = down_load
        self.time_percent = 0
        self.switch = True

    def set_switch(self, switch):
        self.switch = switch

    def get_switch(self):
        return self.switch

    def set_time_percent(self, time_percent):
        self.time_percent = time_percent

    def get_time_percent(self):
        return self.time_percent

    def progress(self, percent):
        if percent > 100:
            percent = 100
        end = time.time()
        if percent != 100:
            print(f"\r{self.down_load}  %.f%s  [%s]  running" % (percent, '%', self.timer(end - self.time_start)),
                  flush=True, end='')
        else:
            print(f"\r{self.down_load}  %.f%s  [%s]  success" % (percent, '%', self.timer(end - self.time_start)),
                  flush=True, end='')

    @staticmethod
    def timer(times):
        hours, rem = divmod(times, 3600)
        minutes, seconds = divmod(rem, 60)
        return "{:0>2}:{:0>2}:{:0>2}".format(int(hours), int(minutes), int(seconds))


def remove_file(path):
    os.remove(path)


def id_encryption(encryption_type, start_num, end_num):
    if encryption_type == 'md5':
        return [hashlib.md5(bytes(str(value), encoding='utf-8')).hexdigest() for value in range(start_num, end_num)]
    elif encryption_type == 'sha256':
        return [hashlib.sha256(bytes(str(value), encoding='utf-8')).hexdigest() for value in range(start_num, end_num)]
    else:
        return [str(value) for value in range(start_num, end_num)]


def get_big_data(guest_data_size, host_data_size, guest_feature_num, host_feature_num, include_path, host_data_type,
                 conf: Config, encryption_type, match_rate, sparsity, force, split_host, output_path):
    global big_data_dir

    def list_tag_value(feature_nums, head):
        # data = ''
        # for f in range(feature_nums):
        #     data += head[f] + ':' + str(round(np.random.randn(), 4)) + ";"
        # return data[:-1]
        return ";".join([head[k] + ':' + str(round(v, 4)) for k, v in enumerate(np.random.randn(feature_nums))])

    def list_tag(feature_nums, data_list):
        data = ''
        for f in range(feature_nums):
            data += random.choice(data_list) + ";"
        return data[:-1]

    def _generate_tag_value_data(data_path, start_num, end_num, feature_nums, progress):
        data_num = end_num - start_num
        section_data_size = round(data_num / 100)
        iteration = round(data_num / section_data_size)
        head = ['x' + str(i) for i in range(feature_nums)]
        for batch in range(iteration + 1):
            progress.set_time_percent(batch)
            output_data = pd.DataFrame(columns=["id"])
            if section_data_size * (batch + 1) <= data_num:
                output_data["id"] = id_encryption(encryption_type, section_data_size * batch + start_num,
                                                  section_data_size * (batch + 1) + start_num)
                slicing_data_size = section_data_size
            elif section_data_size * batch < data_num:
                output_data['id'] = id_encryption(encryption_type, section_data_size * batch + start_num, end_num)
                slicing_data_size = data_num - section_data_size * batch
            else:
                break
            feature = [list_tag_value(feature_nums, head) for i in range(slicing_data_size)]
            output_data['feature'] = feature
            output_data.to_csv(data_path, mode='a+', index=False, header=False)

    def _generate_dens_data(data_path, start_num, end_num, feature_nums, label_flag, progress):
        if label_flag:
            head_1 = ['id', 'y']
        else:
            head_1 = ['id']
        data_num = end_num - start_num
        head_2 = ['x' + str(i) for i in range(feature_nums)]
        df_data_1 = pd.DataFrame(columns=head_1)
        head_data = pd.DataFrame(columns=head_1 + head_2)
        head_data.to_csv(data_path, mode='a+', index=False)
        section_data_size = round(data_num / 100)
        iteration = round(data_num / section_data_size)
        for batch in range(iteration + 1):
            progress.set_time_percent(batch)
            if section_data_size * (batch + 1) <= data_num:
                df_data_1["id"] = id_encryption(encryption_type, section_data_size * batch + start_num,
                                                section_data_size * (batch + 1) + start_num)
                slicing_data_size = section_data_size
            elif section_data_size * batch < data_num:
                df_data_1 = pd.DataFrame(columns=head_1)
                df_data_1["id"] = id_encryption(encryption_type, section_data_size * batch + start_num, end_num)
                slicing_data_size = data_num - section_data_size * batch
            else:
                break
            if label_flag:
                df_data_1["y"] = [round(np.random.random()) for x in range(slicing_data_size)]
            feature = np.random.randint(-10000, 10000, size=[slicing_data_size, feature_nums]) / 10000
            df_data_2 = pd.DataFrame(feature, columns=head_2)
            output_data = pd.concat([df_data_1, df_data_2], axis=1)
            output_data.to_csv(data_path, mode='a+', index=False, header=False)

    def _generate_tag_data(data_path, start_num, end_num, feature_nums, sparsity, progress):
        data_num = end_num - start_num
        section_data_size = round(data_num / 100)
        iteration = round(data_num / section_data_size)
        valid_set = [x for x in range(2019120799, 2019120799 + round(feature_nums / sparsity))]
        data = list(map(str, valid_set))
        for batch in range(iteration + 1):
            progress.set_time_percent(batch)
            output_data = pd.DataFrame(columns=["id"])
            if section_data_size * (batch + 1) <= data_num:
                output_data["id"] = id_encryption(encryption_type, section_data_size * batch + start_num,
                                                  section_data_size * (batch + 1) + start_num)
                slicing_data_size = section_data_size
            elif section_data_size * batch < data_num:
                output_data["id"] = id_encryption(encryption_type, section_data_size * batch + start_num, end_num)
                slicing_data_size = data_num - section_data_size * batch
            else:
                break
            feature = [list_tag(feature_nums, data_list=data) for i in range(slicing_data_size)]
            output_data['feature'] = feature
            output_data.to_csv(data_path, mode='a+', index=False, header=False)

    def data_save(data_info, table_names, namespaces, partition_list):
        data_count = 0
        for idx, data_name in enumerate(data_info.keys()):
            label_flag = True if 'guest' in data_info[data_name] else False
            data_type = 'dense' if 'guest' in data_info[data_name] else host_data_type
            if split_host and ('host' in data_info[data_name]):
                host_end_num = int(np.ceil(host_data_size / len(data_info))) * (data_count + 1) if np.ceil(
                    host_data_size / len(data_info)) * (data_count + 1) <= host_data_size else host_data_size
                host_start_num = int(np.ceil(host_data_size / len(data_info))) * data_count
                data_count += 1
            else:
                host_end_num = host_data_size
                host_start_num = 0
            out_path = os.path.join(str(big_data_dir), data_name)
            if os.path.exists(out_path) and os.path.isfile(out_path):
                if force:
                    remove_file(out_path)
                else:
                    echo.echo('{} Already exists'.format(out_path))
                    continue
            data_i = (idx + 1) / len(data_info)
            downLoad = f'dataget  [{"#" * int(24 * data_i)}{"-" * (24 - int(24 * data_i))}]  {idx + 1}/{len(data_info)}'
            start = time.time()
            progress = data_progress(downLoad, start)
            thread = threading.Thread(target=run, args=[progress])
            thread.start()

            try:
                if 'guest' in data_info[data_name]:
                    _generate_dens_data(out_path, guest_start_num, guest_end_num,
                                        guest_feature_num, label_flag, progress)
                else:
                    # if data_type == 'tag' and not parallelize:
                    if data_type == 'tag':
                        _generate_tag_data(out_path, host_start_num, host_end_num, host_feature_num, sparsity, progress)
                    # elif data_type == 'tag_value' and not parallelize:
                    elif data_type == 'tag_value':
                        _generate_tag_value_data(out_path, host_start_num, host_end_num, host_feature_num, progress)
                    # elif data_type == 'dense' and not parallelize:
                    elif data_type == 'dense':
                        _generate_dens_data(out_path, host_start_num, host_end_num,
                                            host_feature_num, label_flag, progress)

                progress.set_switch(False)
                time.sleep(1)
            except Exception:
                exception_id = uuid.uuid1()
                echo.echo(f"exception_id={exception_id}")
                LOGGER.exception(f"exception id: {exception_id}")
            finally:
                progress.set_switch(False)
                echo.stdout_newline()

    def run(p):
        while p.get_switch():
            time.sleep(1)
            p.progress(p.get_time_percent())

    if not match_rate > 0 or not match_rate <= 1:
        raise Exception(f"The value is between (0-1), Please check match_rate:{match_rate}")
    guest_start_num = host_data_size - int(guest_data_size * match_rate)
    guest_end_num = guest_start_num + guest_data_size

    if os.path.isfile(include_path):
        with include_path.open("r") as f:
            testsuite_config = yaml.safe_load(f)
    else:
        raise Exception(f'Input file error, please check{include_path}.')
    try:
        if output_path is not None:
            big_data_dir = os.path.abspath(output_path)
        else:
            big_data_dir = os.path.abspath(conf.cache_directory)
    except Exception:
        raise Exception('{}path does not exist'.format(big_data_dir))
    date_set = {}
    table_name_list = []
    table_namespace_list = []
    partition_list = []
    for upload_dict in testsuite_config.get('data'):
        date_set[os.path.basename(upload_dict.get('file'))] = upload_dict.get('role')
        table_name_list.append(upload_dict.get('table_name'))
        table_namespace_list.append(upload_dict.get('namespace'))
        partition_list.append(upload_dict.get('partitions', 8))

    data_save(
        data_info=date_set,
        table_names=table_name_list,
        namespaces=table_namespace_list,
        partition_list=partition_list)
    echo.echo(f'Data storage address, please check{big_data_dir}')

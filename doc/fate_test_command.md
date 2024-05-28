# FATE Test

A collection of useful tools to running FATE's test.

## Testsuite

Testsuite is used for running a collection of jobs in sequence. Data
used for jobs could be uploaded before jobs are submitted and,
optionally, be cleaned after jobs finish. This tool is useful for FATE's
release test.

### command options

```bash
fate_test suite --help
```

1. include:

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml>
   ```

   will run testsuites in
   *path1*

2. exclude:

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml> -e <path2 to exclude> -e <path3 to exclude> ...
   ```

   will run testsuites in *path1* but not in *path2* and *path3*

3. glob:

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml> -g "hetero*"
   ```

   will run testsuites in sub directory start with *hetero* of
   *path1*

4. replace:

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml> -r '{"maxIter": 5}'
   ```

   will find all key-value pair with key "maxIter" in
   <span class="title-ref">data conf</span> or
   <span class="title-ref">conf</span> or
   <span class="title-ref">dsl</span> and replace the value with 5

5. timeout:

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml> -m 3600
   ```

   will run testsuites in *path1* and timeout when job does not finish
   within 3600s; if tasks need more time, use a larger threshold

6. task-cores

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml> -p 4
   ```

   will run testsuites in *path1* with script config "task-cores" set to 4;
   only effective for DSL conf

7. update-job-parameters

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml> -uj {}
   ```

   will run testsuites in *path1* with respective job parameters set to
   provided values

8. update-component-parameters

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml> -uc {}
   ```

   will run testsuites in *path1* with respective component parameters
   set to provided values

9. skip-jobs:

    ```bash
    fate_test suite -i <path1 contains *testsuite.yaml> --skip-pipeline-jobs
    ```

   will run testsuites in *path1* but skip all *pipeline tasks* in
   testsuites.

10. skip-data:

    ```bash
    fate_test suite -i <path1 contains *testsuite.yaml> --skip-data
    ```

    will run testsuites in *path1* without uploading data specified in
    *testsuite.yaml*.

11. data only:

    ```bash
    fate_test suite -i <path1 contains *testsuite.yaml> --data-only
    ```

    will only upload data specified in *testsuite.yaml* without running
    jobs

12. disable-clean-data:

    ```bash
    fate_test suite -i <path1 contains *testsuite.yaml> --disable-clean-data
    ```

    will run testsuites in *path1* without removing data from storage
    after tasks
    finish

13. enable-clean-data:

    ```bash
    fate_test suite -i <path1 contains *testsuite.yaml> --enable-clean-data
    ```

    will remove data from storage after finishing running testsuites

14. engine-run:

    ```bash
    fate_test suite -i *path1* --engine-run cores=4 --engine-run spark.driver.memory=8G --skip-data
    ```

    will run testsuites in *path1* with engine run params set to specified values

15. yes:

    ```bash
    fate_test suite -i <path1 contains *testsuite.yaml> --yes
    ```

    will run testsuites in *path1* directly, skipping double check

### testsuite configuration

Configuration of jobs should be specified in a testsuite whose file name
ends with "\*testsuite.yaml". For testsuite examples, please
refer [here](https://github.com/FederatedAI/FATE/tree/master/examples/pipeline.

A testsuite includes the following elements:

- data: list of local data to be uploaded before running FATE jobs

    - file: path to original data file to be uploaded, should be
      relative to testsuite or FATE installation path
    - meta: meta info on table, including data type and file format
    - head: whether file includes header
    - partitions: number of partition for data storage
    - table\_name: table name in storage
    - namespace: table namespace in storage
    - role: which role to upload the data, as specified in
      fate\_test.config; naming format is:
      "{role\_type}\_{role\_index}", index starts at 0

  ```yaml
    - file: examples/data/breast_hetero_guest.csv
      meta:
        delimiter: ","
        dtype: float64
        input_format: dense
        label_type: int64
        label_name: y
        match_id_name: id
        match_id_range: 0
        tag_value_delimiter: ":"
        tag_with_value: false
        weight_type: float64
      partitions: 4
      head: true
      extend_sid: true
      table_name: breast_hetero_guest
      namespace: experiment
      role: guest_0
  ```

- tasks: includes arbitrary number of pipeline jobs with
  paths to corresponding python script

    - job: name of job to be run, must be unique within each group
      list

        - script: path to pipeline script, should be relative to
          testsuite

      ```yaml
      tasks:
        normal-lr:
          script: test_lr.py
        lr-cv:
          script: test_lr_cv.py
      ```

## Benchmark Quality

Benchmark-quality is used for comparing modeling quality between FATE
and other machine learning systems. Benchmark produces a metrics
comparison summary for each benchmark job group.

Benchmark can also compare metrics of different models from the same
script/PipeLine job. Please refer to the [script writing
guide](#testing-script) below for
instructions.

```bash
fate_test benchmark-quality -i examples/benchmark_quality/hetero_linear_regression
```

```bash
|----------------------------------------------------------------------|
|                             Data Summary                             |
|-------+--------------------------------------------------------------|
|  Data |                         Information                          |
|-------+--------------------------------------------------------------|
| train | {'guest': 'motor_hetero_guest', 'host': 'motor_hetero_host'} |
|  test | {'guest': 'motor_hetero_guest', 'host': 'motor_hetero_host'} |
|-------+--------------------------------------------------------------|


|-------------------------------------------------------------------------------------------------------------------------------------|
|                                                           Metrics Summary                                                           |
|-------------------------------------------+-------------------------+--------------------+---------------------+--------------------|
|                 Model Name                | root_mean_squared_error |      r2_score      |  mean_squared_error | explained_variance |
|-------------------------------------------+-------------------------+--------------------+---------------------+--------------------|
| local-hetero_linear_regression-regression |    0.312552080517407    | 0.9040310440206087 | 0.09768880303575968 | 0.9040312584426697 |
|  FATE-hetero_linear_regression-regression |    0.3139977881119483   | 0.9031411831961411 | 0.09859461093919598 | 0.903146386539082  |
|-------------------------------------------+-------------------------+--------------------+---------------------+--------------------|
|-------------------------------------|
|            Match Results            |
|-------------------------+-----------|
|          Metric         | All Match |
| root_mean_squared_error |    True   |
|         r2_score        |    True   |
|    mean_squared_error   |    True   |
|    explained_variance   |    True   |
|-------------------------+-----------|


|-------------------------------------------------------------------------------------|
|                             FATE Script Metrics Summary                             |
|--------------------+---------------------+--------------------+---------------------|
| Script Model Name  |         min         |        max         |         mean        |
|--------------------+---------------------+--------------------+---------------------|
|  linr_train-FATE   | -1.5305666678748353 | 1.4968292506353484 | 0.03948016870496807 |
| linr_validate-FATE | -1.5305666678748353 | 1.4968292506353484 | 0.03948016870496807 |
|--------------------+---------------------+--------------------+---------------------|
|---------------------------------------|
|   FATE Script Metrics Match Results   |
|----------------+----------------------|
|     Metric     |      All Match       |
|----------------+----------------------|
|      min       |         True         |
|      max       |         True         |
|      mean      |         True         |
|----------------+----------------------|
```

### command options

use the following command to show help message

```bash
fate_test benchmark-quality --help
```

1. include:

   ```bash
   fate_test benchmark-quality -i <path1 contains *benchmark.yaml>
   ```

   will run benchmark testsuites in
   *path1*

2. exclude:

   ```bash
   fate_test benchmark-quality -i <path1 contains *benchmark.yaml> -e <path2 to exclude> -e <path3 to exclude> ...
   ```

   will run benchmark testsuites in *path1* but not in *path2* and
   *path3*

3. glob:

   ```bash
   fate_test benchmark-quality -i <path1 contains *benchmark.yaml> -g "hetero*"
   ```

   will run benchmark testsuites in sub directory start with *hetero*
   of
   *path1*

4. tol:

   ```bash
   fate_test benchmark-quality -i <path1 contains *benchmark.yaml> -t 1e-3
   ```

   will run benchmark testsuites in *path1* with absolute tolerance of
   difference between metrics set to 0.001. If absolute difference
   between metrics is smaller than *tol*, then metrics are considered
   almost equal. Check benchmark testsuite [writing
   guide](#benchmark-testsuite) on setting alternative tolerance.

5. storage-tag

   ```bash
   fate_test performance -i <path1 contains *benchmark.yaml> -s test
   ```

   will run benchmark testsuites in *path1* with performance stored
   under provided tag for future comparison; note that FATE-Test
   always records the most recent run for each tag; if the same tag
   is used more than once, only metrics from the latest job is
   kept

6. history-tag

   ```bash
   fate_test performance -i <path1 contains *benchmark.yaml> -v test1 -v test2
   ```

   will run benchmark testsuites in *path1* with performance compared
   to history jobs under provided
   tag(s)

7. skip-data:

   ```bash
   fate_test benchmark-quality -i <path1 contains *benchmark.yaml> --skip-data
   ```

   will run benchmark testsuites in *path1* without uploading data
   specified in
   *benchmark.yaml*.

8. disable-clean-data:

   ```bash
   fate_test suite -i <path1 contains *benchmark.yaml> --disable-clean-data
   ```

   will run benchmark testsuites in *path1* without removing data from
   storage after tasks
   finish

9. enable-clean-data:

   ```bash
   fate_test suite -i <path1 contains *benchmark.yaml> --enable-clean-data
   ```

   will remove data from storage after finishing running benchmark
   testsuites

11. engine-run:

    ```bash
    fate_test benchmark-quality -i *path1* --engine-run cores=4 --engine-run spark.driver.memory=8G --skip-data
    ```

    will run testsuites in *path1* with engine run params set to specified values

12. yes:
    ```bash
    fate_test benchmark-quality -i <path1 contains *benchmark.yaml> --yes
    ```

    will run benchmark testsuites in *path1* directly, skipping double
    check

### benchmark job configuration

Configuration of jobs should be specified in a benchmark testsuite whose
file name ends with "\*benchmark.yaml". For benchmark testsuite example,
please refer [here](https://github.com/FederatedAI/FATE/tree/master/examples/benchmark_quality).

A benchmark testsuite includes the following elements:

- data: list of local data to be uploaded before running FATE jobs

    - file: path to original data file to be uploaded, should be
      relative to testsuite or FATE installation path
    - meta: meta info on table, including data type and file format
    - head: whether file includes header
    - partitions: number of partition for data storage
    - table\_name: table name in storage
    - namespace: table namespace in storage
    - role: which role to upload the data, as specified in
      fate\_test.config; naming format is:
      "{role\_type}\_{role\_index}", index starts at 0

  ```yaml
    - file: examples/data/breast_hetero_guest.csv
      meta:
        delimiter: ","
        dtype: float64
        input_format: dense
        label_type: int64
        label_name: y
        match_id_name: id
        match_id_range: 0
        tag_value_delimiter: ":"
        tag_with_value: false
        weight_type: float64
      partitions: 4
      head: true
      extend_sid: true
      table_name: breast_hetero_guest
      namespace: experiment
      role: guest_0
  ```

- job group: each group includes arbitrary number of jobs with paths
  to corresponding script and configuration

    - job: name of job to be run, must be unique within each group
      list

        - script: path to [testing script](#testing-script), should be
          relative to testsuite
        - conf: path to job configuration file for script, should be
          relative to testsuite

      ```yaml
        local:
          script: "./sklearn-lr-binary.py"
          conf: "./breast_lr_sklearn_config.yaml"

      ```

    - compare\_setting: additional setting for quality metrics
      comparison, currently only takes `relative_tol`

      If metrics *a* and *b* satisfy *abs(a-b) \<= max(relative\_tol
      \* max(abs(a), abs(b)), absolute\_tol)* (from [math
      module](https://docs.python.org/3/library/math.html#math.isclose)),
      they are considered almost equal. In the below example, metrics
      from "local" and "FATE" jobs are considered almost equal if
      their relative difference is smaller than *0.05 \*
      max(abs(local\_metric), abs(pipeline\_metric)*.

  ```yaml
     hetero_lr-binary-0-breast:
        local:
          script: "./sklearn-lr-binary.py"
          conf: "./breast_lr_sklearn_config.yaml"
        FATE-hetero-lr:
          script: "./pipeline-lr-binary.py"
          conf: "./breast_config.yaml"
        FATE-hetero-sshe-lr:
          script: "./pipeline-sshe-lr-binary.py"
          conf: "./breast_config.yaml"
        compare_setting:
          relative_tol: 0.01
  ```

### testing script

All job scripts need to have `Main` function as an entry point for
executing jobs; scripts should return two dictionaries: first with data
information key-value pairs: {data\_type}: {data\_name\_dictionary}; the
second contains {metric\_name}: {metric\_value} key-value pairs for
metric comparison.

By default, the final data summary shows the output from the job named
"FATE"; if no such job exists, data information returned by the first
job is shown. For clear presentation, we suggest that user follow this
general [guideline](../../examples/data/README.md#data-set-naming-rule)
for data set naming. In the case of multi-host task, consider numbering
host as such:

    {'guest': 'default_credit_homo_guest',
     'host_1': 'default_credit_homo_host_1',
     'host_2': 'default_credit_homo_host_2'}

Returned quality metrics of the same key are to be compared. Note that
only **real-value** metrics can be compared.

To compare metrics of different models from the same script, metrics of
each model need to be wrapped into dictionary in the same format as the
general metric output above.

In the returned dictionary of script, use reserved key `script_metrics`
to indicate the collection of metrics to be compared.

- FATE script: `Main` should have three inputs:
    - config: job configuration,
      object loaded from "fate\_test\_config.yaml"
    - param: job parameter setting, dictionary loaded from "conf" file
      specified in benchmark testsuite
    - namespace: namespace suffix, user-given *namespace* or generated
      timestamp string when using *namespace-mangling*
- non-FATE script: `Main` should have one or two inputs:
    - param: job parameter setting, dictionary loaded from "conf" file
      specified in benchmark testsuite
    - (optional) config: job configuration,
      object loaded from "fate\_test\_config.yaml"

Note that `Main` in FATE & non-FATE scripts can also be set to not take any
input argument.

## Benchmark Performance

`Performance` sub-command is used to test
efficiency of designated FATE jobs.

Examples may be found [here](https://github.com/FederatedAI/FATE/tree/master/examples/benchmark_quality).

### command options

```bash
fate_test performance --help
```

1. job-type:

   ```bash
   fate_test performance -t intersect
   ```

   will run testsuites from intersect sub-directory (set in config) in
   the default performance directory; note that only one of `task` and
   `include` is
   needed

2. include:

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml>; note that only one of ``task`` and ``include`` needs to be specified.
   ```

   will run testsuites in *path1*. Note that only one of `task` and
   `include` needs to be specified; when both are given, path from
   `include` takes
   priority.

3. replace:

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml> -r '{"maxIter": 5}'
   ```

   will find all key-value pair with key "maxIter" in
   <span class="title-ref">data conf</span> or
   <span class="title-ref">conf</span> or
   <span class="title-ref">dsl</span> and replace the value with 5

4. timeout:

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml> -m 3600
   ```

   will run testsuites in *path1* and timeout when job does not finish
   within 3600s; if tasks need more time, use a larger threshold

5. max-iter:

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml> -e 5
   ```

   will run testsuites in *path1* with all values to key "max\_iter"
   set to 5

6. max-depth

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml> -d 4
   ```

   will run testsuites in *path1* with all values to key "max\_depth"
   set to 4

7. num-trees

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml> -nt 5
   ```

   will run testsuites in *path1* with all values to key "num\_trees"
   set to 5

8. task-cores

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml> -p 4
   ```

   will run testsuites in *path1* with "task\_cores" in script config set to 4

9. update-job-parameters

   ```bash
   fate_test performance -i <path1 contains *testsuite.yaml> -uj {}
   ```

   will run testsuites in *path1* with respective job parameters set to
   provided values

10. update-component-parameters

    ```bash
    fate_test performance -i <path1 contains *testsuite.yaml> -uc {}
    ```

    will run testsuites in *path1* with respective component parameters
    set to provided values

11. storage-tag

    ```bash
    fate_test performance -i <path1 contains *testsuite.yaml> -s test
    ```

    will run testsuites in *path1* with performance time stored under
    provided tag for future comparison; note that FATE-Test always
    records the most recent run for each tag; if the same tag is used
    more than once, only performance from the latest job is
    kept

12. history-tag

    ```bash
    fate_test performance -i <path1 contains *testsuite.yaml> -v test1 -v test2
    ```

    will run testsuites in *path1* with performance time compared to
    history jobs under provided
    tag(s)

13. skip-data:

    ```bash
    fate_test performance -i <path1 contains *testsuite.yaml> --skip-data
    ```

    will run testsuites in *path1* without uploading data specified in
    *testsuite.yaml*.

14. disable-clean-data:

    ```bash
    fate_test performance -i <path1 contains *testsuite.yaml> --disable-clean-data
    ```

    will run testsuites in *path1* without removing data from storage
    after tasks finish

15. engine-run:

    ```bash
    fate_test performance -i *path1* --engine-run cores=4 --engine-run spark.driver.memory=8G --skip-data
    ```

    will run testsuites in *path1* with engine run params set to specified values

16. yes:

    ```bash
    fate_test performance -i <path1 contains *testsuite.yaml> --yes
    ```

    will run testsuites in *path1* directly, skipping double check

## data

`Data` sub-command is used for upload,
delete, and generate
dataset.

### data command options

```bash
fate_test data --help
```

1. include:

    ```bash
    fate_test data [upload|delete] -i <path1 contains *testsuite.yaml | *benchmark.yaml>
    ```

   will upload/delete dataset in testsuites in
   *path1*

2. exclude:

    ```bash
    fate_test data [upload|delete] -i <path1 contains *testsuite.yaml | *benchmark.yaml> -e <path2 to exclude> -e <path3 to exclude> ...
    ```

   will upload/delete dataset in testsuites in *path1* but not in
   *path2* and
   *path3*

3. glob:

    ```bash
    fate_test data [upload|delete] -i <path1 contains \*testsuite.yaml | \*benchmark.yaml> -g "hetero*"
    ```

   will upload/delete dataset in testsuites in sub directory start with
   *hetero* of
   *path1*

### generate command options

```bash
fate_test data --help
```

1. include:

   ```bash
   fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml>
   ```

   will generate dataset in testsuites in *path1*; note that only one
   of `type` and `include` is
   needed

2. host-data-type:

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml | *benchmark.yaml> -ht {tag-value | dense | tag }
   ```

   will generate dataset in testsuites *path1* where host data are of
   selected
   format

3. sparsity:

   ```bash
   fate_test suite -i <path1 contains *testsuite.yaml | *benchmark.yaml> -s 0.2
   ```

   will generate dataset in testsuites in *path1* with sparsity at 0.1;
   useful for tag-formatted
   data

4. encryption-type:

   ```bash
   fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -p {sha256 | md5}
   ```

   will generate dataset in testsuites in *path1* with hash id using
   SHA256
   method

5. match-rate:

   ```bash
   fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -m 1.0
   ```

   will generate dataset in testsuites in *path1* where generated host
   and guest data have intersection rate of
   1.0

6. guest-data-size:

   ```bash
   fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -ng 10000
   ```

   will generate dataset in testsuites *path1* where guest data each
   have 10000
   entries

7. host-data-size:

   ```bash
   fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -nh 10000
   ```

   will generate dataset in testsuites *path1* where host data have
   10000
   entries

8. guest-feature-num:

   ```bash
   fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -fg 20
   ```

   will generate dataset in testsuites *path1* where guest data have 20
   features

9. host-feature-num:

   ```bash
   fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -fh 200
   ```

   will generate dataset in testsuites *path1* where host data have 200
   features

10. output-path:

    ```bash
    fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -o <path2>
    ```

    will generate dataset in testsuites *path1* and write file to
    *path2*

11. force:

    ```bash
    fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -o <path2> --force
    ```

    will generate dataset in testsuites *path1* and write file to
    *path2*; will overwrite existing file(s) if designated file name
    found under
    *path2*

12. split-host:

    ```bash
    fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> -nh 10000 --split-host
    ```

    will generate dataset in testsuites *path1*; 10000 entries will be
    divided equally among all host data
    sets

13. upload-data

    ```bash
    fate_test data generate  -i <path1 contains *testsuite.yaml | *benchmark.yaml> --upload-data
    ```

    will generate dataset in testsuites *path1* and upload generated
    data for all parties to
    FATE

14. remove-data

    ```bash
    fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml> --upload-data --remove-data
    ```

    (effective with `upload-data` set to True) will delete generated
    data after generate and upload dataset in testsuites
    *path1*


## FATE Llmsuite

FATE Llmsuite is used for running a collection of FATE-Llm jobs in sequence and then evaluate them on user-specified tasks.
It also allows users to compare the results of different llm jobs.

### command options

```bash
fate_test llmsuite --help
```

1. include:

   ```bash
   fate_test llmsuite -i <path1 contains *llmsuite.yaml>
   ```

   will run llm testsuites in
   *path1*

2. exclude:

   ```bash
   fate_test llmsuite -i <path1 contains *llmsuite.yaml> -e <path2 to exclude> -e <path3 to exclude> ...
   ```

   will run llm testsuites in *path1* but not in *path2* and *path3*

3. glob:

   ```bash
   fate_test llmsuite -i <path1 contains *llmsuite.yaml> -g "hetero*"
   ```

   will run llm testsuites in sub directory start with *hetero* of
   *path1*

4. algorithm-suite:

   ```bash
   fate_test llmsuite -a "pellm"
   ```

   will run built-in 'pellm' llm testsuite, which will train and evaluate a FATE-Llm model and a zero-shot model

5. timeout:

   ```bash
   fate_test llmsuite -i <path1 contains *llmsuite.yaml> -m 3600
   ```

   will run llm testsuites in *path1* and timeout when job does not finish
   within 3600s; if tasks need more time, use a larger threshold

6. task-cores

   ```bash
   fate_test llmsuite -i <path1 contains *llmsuite.yaml> -p 4
   ```

   will run llm testsuites in *path1* with script config "task-cores" set to 4

7. eval-config:

    ```bash
    fate_test llmsuite -i <path1 contains *llmsuite.yaml> --eval-config <path2>
    ```

   will run llm testsuites in *path1* with evaluation configuration set to *path2*

8. skip-evaluate:

    ```bash
    fate_test llmsuite -i <path1 contains *llmsuite.yaml> --skip-evaluate
    ```

    will run llm testsuites in *path1* without running evaluation

9. provider:

    ```bash
    fate_test llmsuite -i <path1 contains *llmsuite.yaml> --provider <provider_name>
    ```

    will run llm testsuites in *path1* with FATE provider set to *provider_name*

10. yes:

    ```bash
    fate_test llmsuite -i <path1 contains *llmsuite.yaml> --yes
    ```

    will run llm testsuites in *path1* directly, skipping double check


### FATE-Llm job configuration

Configuration of jobs should be specified in a llm testsuite whose
file name ends with "\*llmsuite.yaml". For llm testsuite example,
please refer [here](https://github.com/FederatedAI/FATE-LLM).

A FATE-Llm testsuite includes the following elements:

- job group: each group includes arbitrary number of jobs with paths
  to corresponding script and configuration

    - job: name of evaluation job to be run, must be unique within each group
      list

        - script: path to [testing script](#testing-script), should be
          relative to testsuite, optional for evaluation-only jobs;
          note that pretrained model, if available, should be returned at the end of the script
        - conf: path to job configuration file for script, should be
          relative to testsuite, optional for evaluation-only jobs
        - pretrained: path to pretrained model, should be either model name from Huggingface or relative path to
          testsuite, optional for jobs needed to run FATE-Llm training job, where the 
          script should return path to the pretrained model
        - peft: path to peft file, should be relative to testsuite, 
          optional for jobs needed to run FATE-Llm training job
        - tasks: list of tasks to be evaluated, optional for jobs skipping evaluation
        - include_path: should be specified if tasks are user-defined
        - eval_conf: path to evaluation configuration file, should be
          relative to testsuite; if not provided, will use default conf

      ```yaml
          bloom_lora:
            pretrained: "models/bloom-560m"
            script: "./test_bloom_lora.py"
            conf: "./bloom_lora_config.yaml"
            peft_path_format: "{{fate_base}}/fate_flow/model/{{job_id}}/guest/{{party_id}}/{{model_task_name}}/0/output/output_model/model_directory"
            tasks:
              - "dolly-15k"

      ```

- llm suite

  ```yaml
     hetero_nn_sshe_binary_0:
      bloom_lora: 
        pretrained: "bloom-560m"
        script: "./test_bloom_lora.py"
        conf: "./bloom_lora_config.yaml"
        peft_path_format: "{{fate_base}}/fate_flow/model/{{job_id}}/guest/{{party_id}}/{{model_task_name}}/0/output/output_model/model_directory"
        tasks:
          - "dolly-15k"
      bloom_zero_shot:
        pretrained: "bloom-560m"
        tasks:
          - "dolly-15k"
  ```

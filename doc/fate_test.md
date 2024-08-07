# FATE Test Tutorial

A collection of useful tools to running FATE tests and PipeLine tasks.

## quick start

1. install

    ```bash
    pip install -e python/fate_test
    ```
2. edit default fate\_test\_config.yaml; edit path to fate base/data base accordingly

   ```bash
   # edit priority config file with system default editor
   # filling some field according to comments
   fate_test config edit
   ```

3. configure FATE-Flow Commandline server setting

    ```bash
    # configure FATE-Flow Commandline server setting
    flow init --port 9380 --ip 127.0.0.1
    ```

4. run some fate\_test suite

   ```bash
   fate_test suite -i <path contains *testsuite.yaml>
   ```

5. run some fate\_test benchmark quality

   ```bash
   fate_test benchmark-quality -i <path contains *benchmark.yaml>
   ```

6. run some fate\_test benchmark performance

   ```bash
   fate_test benchmark-quality -i <path contains *performance.yaml>
   ```

7.  useful logs or exception will be saved to logs dir with namespace
shown in last step

## command types

- [suite](./fate_test_command.md#testsuite): used for running testsuites,
  collection of FATE jobs

  ```bash
  fate_test suite -i <path contains *testsuite.yaml>
  ```

- [data](./fate_test_command.md#data): used for upload, delete, and generate dataset

    - upload/delete data command:

      ```bash
      fate_test data [upload|delete] -i <path1 contains *testsuite.yaml | *benchmark.yaml>
      ```
    - upload example data of min_test/all_examples command:

      ```bash
      fate_test data upload -t min_test
      fate_test data upload -t all_examples
      ```

    - generate data command:

      ```bash
      fate_test data generate -i <path1 contains *testsuite.yaml | *benchmark.yaml>
      ```

- [benchmark-quality](./fate_test_command.md#benchmark-quality): used for comparing modeling quality between FATE
  and other machine learning systems

  ```bash
  fate_test bq -i <path contains *benchmark.yaml>
  ```

- [benchmark-performance](./fate_test_command.md#benchmark-performance): used for checking FATE algorithm performance;
  user
  should first generate and upload data before running performance testsuite

  ```bash
  fate_test data generate -i <path contains *performance.yaml> -ng 10000 -fg 10 -fh 10 -m 1.0 --upload-data
  fate_test performance -i <path contains *performance.yaml> --skip-data
  ```

- [llm-suite](./fate_test_command.md#llmsuite): used for running FATE-Llm testsuites, collection of FATE-Llm jobs and/or evaluations
  
  Before running llmsuite for the first time, make sure to install FATE-Llm and allow its import in FATE-Test scripts:

  ```bash
  fate_test config include fate-llm
  ```

  ```bash
  fate_test llmsuite -i <path contains *llmsuite.yaml>
  ```

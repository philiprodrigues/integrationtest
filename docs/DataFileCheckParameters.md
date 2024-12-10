# integrationtest: Helpers for pytest-based DUNE DAQ integration tests

Some of the data-file-check functions that are provided in this package (python/integrationtest/data_file_checks.py) expect a python dictionary with configuration parameters to be passed in.  These values for these parameters are specified in each of our automated integration and regression tests, and they can be used to fine-tune the data-quality tests that the data-file-check functions perform.

Here are the current set of supported parameters within these configuration dictionaries:


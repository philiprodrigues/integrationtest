# Parameters that can be used to control data-file-check behavior

This package (_integrationtest_) provides infrastructure that we use for developing and running automated integration and regression tests.

Part of what is provided is a set of functions that can be used to validate the DAQ data that is produced in such tests.  Many of these functions are contained in _data_file_checks.py_ (located in the _python/integrationtest_ subdirectory).

The functions that are provided in data_file_checks.py have been written in a way that they can be used for different types of DAQ data (for example, TriggerRecords and TimeSlices, and/or WIBEth data and data fragments produced by the Trigger system).  The way that integtest developers specify the type of data that should be tested and the success criteria that should be used is by passing in a Python dictionary that contains specific values for a set of expected parameters.  Here is a sample:

Here are the current set of supported parameters:


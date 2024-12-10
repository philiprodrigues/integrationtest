# Parameters that should be used to control data-file-check behavior

This package (_integrationtest_) provides infrastructure that we use for developing and running automated integration and regression tests.  Part of what is provided is a set of functions that can be used to validate the DAQ data that is produced in such tests.  Many of these functions are contained in _data_file_checks.py_ (located in the _python/integrationtest_ subdirectory).

The functions that are provided in _data_file_checks._py have been written in a way that they can be used for different types of DAQ data (for example, TriggerRecords and TimeSlices, and/or WIBEth data and data fragments produced by the Trigger system).  The way that integtest developers specify the type of data that should be tested, and the success criteria that should be used, is by passing in a Python dictionary that contains specific values for a set of expected parameters.  

Here is a simple example:
```
wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
    "debug_mask": 0x0,
}
```

Here is a more complicated sample:
```
wibeth_tpset_params = {
    "fragment_type_description": "TP Stream",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": number_of_readout_apps * 3,
    "frag_counts_by_record_ordinal": {"first": {"min_count": 1, "max_count": number_of_readout_apps * 3},
                                      "default": {"min_count": number_of_readout_apps * 3, "max_count": number_of_readout_apps * 3} },
    "min_size_bytes": 72,
    "max_size_bytes": 300000,
    "debug_mask": 0x0,
    "frag_sizes_by_record_ordinal": {  "first": {"min_size_bytes":    128, "max_size_bytes": 275000},
                                      "second": {"min_size_bytes":    128, "max_size_bytes": 275000},
                                        "last": {"min_size_bytes":    128, "max_size_bytes": 275000},
                                     "default": {"min_size_bytes": 190000, "max_size_bytes": 275000} }
}
```

The current set of supported parameters is the following:

- fragment_type - the value for this parameter needs to be a string that matches one of the defined ones in daqdataformats/FragmentHeader.hpp.
- fragment_type_description - this is a short string that will be used to describe the fragment type in general terms in console output from the data-file-checks.
- debug_mask - 

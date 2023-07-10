import pytest
import json

import dfmodules.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

# The name of the python module for the config generation
confgen_name="daqconf_multiru_gen"
timing_confgen_name="daqconf_timing_gen"
# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)
# confgen_arguments=[  ]
hardware_map_required = False
# The commands to run in nanorc, as a list
nanorc_command_list="boot init conf start 1 resume wait 10 stop scrap terminate".split()

# Set as optional argument
daq_conf_file = "/home/wx21978/projects/timing/daq_configs/daq-systemtest/config/timing_system_bris_daq_boreas_tlu_hsi.json"
timing_conf_file = "/home/wx21978/projects/timing/daq_configs/daq-systemtest/config/timing_system_bris_timing_boreas_tlu_hsi.json"

# Add a default, get this to override
with open(daq_conf_file) as f:
    conf_dict = json.load(f)
with open(timing_conf_file) as f:
    timing_conf_dict = json.load(f)

# The tests themselves

def test_nanorc_success(par_timing_and_daq):
    # Check that nanorc completed correctly
    assert (par_timing_and_daq.timing.completed_process.returncode==0
            and par_timing_and_daq.daq.completed_process.returncode==0)

def test_log_files(par_timing_and_daq):
    # Check that there are no warnings or errors in the log files
    assert (log_file_checks.logs_are_error_free(par_timing_and_daq.timing.log_files)
            and log_file_checks.logs_are_error_free(par_timing_and_daq.daq.log_files))

def test_data_file(par_timing_and_daq):
    # Run some tests on the output data file
    assert len(par_timing_and_daq.daq.data_files)==1

    data_file=data_file_checks.DataFile(par_timing_and_daq.daq.data_files[0])
    assert data_file_checks.sanity_check(data_file)
    assert data_file_checks.check_link_presence(data_file, n_links=1)
    assert data_file_checks.check_fragment_sizes(data_file, min_frag_size=22344, max_frag_size=22344)
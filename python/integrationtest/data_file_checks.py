import datetime
import h5py
import os.path
import re
from hdf5libs import HDF5RawDataFile
from integrationtest.data_file_check_utilities import (
    get_TC_type,
    get_record_ordinal_strings,
    get_fragment_count_limits,
    get_fragment_size_limits,
    record_ordinal_string_all_tests,
)

class DataFile:
    def __init__(self, filename):
        self.h5file=h5py.File(filename, 'r')
        self.events=self.h5file.keys()
        self.name=str(filename)

def sanity_check(datafile):
    "Very basic sanity checks on file"
    passed=True
    print("") # Clear potential dot from pytest

    # execute unit tests for local function(s)
    # (this is probably not the best place for these...)
    record_ordinal_string_all_tests()

    # Check that every event has a TriggerRecordHeader
    for event in datafile.events:
        triggerrecordheader_count = 0
        for key in datafile.h5file[event]["RawData"].keys():
            if "TriggerRecordHeader" in key:
                triggerrecordheader_count += 1
        if triggerrecordheader_count == 0:
            print(f"\N{POLICE CARS REVOLVING LIGHT} No TriggerRecordHeader in record {event} \N{POLICE CARS REVOLVING LIGHT}")
            passed=False
        if triggerrecordheader_count > 1:
            print(f"\N{POLICE CARS REVOLVING LIGHT} More than one TriggerRecordHeader in record {event} \N{POLICE CARS REVOLVING LIGHT}")
            passed=False
    if passed:
        print("\N{WHITE HEAVY CHECK MARK} Sanity-check passed")
    return passed

def check_file_attributes(datafile):
    "Checking that the expected Attributes exist within the data file"
    passed=True
    base_filename = os.path.basename(datafile.h5file.filename)
    if "tp" in base_filename:
        print("") # Clear potential dot from pytest
    expected_attribute_names = ["application_name", "closing_timestamp", "creation_timestamp", "file_index", "filelayout_params", "filelayout_version", "offline_data_stream", "operational_environment", "record_type", "recorded_size", "run_number", "run_was_for_test_purposes", "source_id_geo_id_map"]
    for expected_attr_name in expected_attribute_names:
        if expected_attr_name not in datafile.h5file.attrs.keys():
            passed=False
            print(f"\N{POLICE CARS REVOLVING LIGHT} Attribute '{expected_attr_name}' not found in file {base_filename} \N{POLICE CARS REVOLVING LIGHT}")
        elif expected_attr_name == "run_number":
            # value from the Attribute
            attr_value = datafile.h5file.attrs.get(expected_attr_name)
            # value from the filename
            pattern = r"_run\d+_"
            match_obj = re.search(pattern, base_filename)
            if match_obj:
                filename_value = int(re.sub('run','',re.sub('_','',match_obj.group(0))))
                if attr_value != filename_value:
                    passed=False
                    print(f"\N{POLICE CARS REVOLVING LIGHT} The value in Attribute '{expected_attr_name}' ({attr_value}) does not match the value in the filename ({base_filename}) \N{POLICE CARS REVOLVING LIGHT}")
        elif expected_attr_name == "file_index":
            # value from the Attribute
            attr_value = datafile.h5file.attrs.get(expected_attr_name)
            # value from the filename
            pattern = r"_\d+_"
            match_obj = re.search(pattern, base_filename)
            if match_obj:
                filename_value = int(re.sub('_','',match_obj.group(0)))
                if attr_value != filename_value:
                    passed=False
                    print(f"\N{POLICE CARS REVOLVING LIGHT} The value in Attribute '{expected_attr_name}' ({attr_value}) does not match the value in the filename ({base_filename}) \N{POLICE CARS REVOLVING LIGHT}")
        elif expected_attr_name == "creation_timestamp":
            attr_value = datafile.h5file.attrs.get(expected_attr_name)
            date_obj = datetime.datetime.fromtimestamp((int(attr_value)/1000)-1, datetime.timezone.utc)
            date_string = date_obj.strftime("%Y%m%dT%H%M%S")
            pattern_low = f".*{date_string}.*"
            date_obj = datetime.datetime.fromtimestamp((int(attr_value)/1000)+1, datetime.timezone.utc)
            date_string = date_obj.strftime("%Y%m%dT%H%M%S")
            pattern_high = f".*{date_string}.*"
            date_obj = datetime.datetime.fromtimestamp((int(attr_value)/1000)+0, datetime.timezone.utc)
            date_string = date_obj.strftime("%Y%m%dT%H%M%S")
            pattern_exact = f".*{date_string}.*"
            if not re.match(pattern_exact, base_filename) and not re.match(pattern_low, base_filename) and not re.match(pattern_high, base_filename):
                passed=False
                print(f"\N{POLICE CARS REVOLVING LIGHT} The value in Attribute '{expected_attr_name}' ({date_string}) does not match the value in the filename ({base_filename}) \N{POLICE CARS REVOLVING LIGHT}")
                print(f"\N{POLICE CARS REVOLVING LIGHT} Debug information: pattern_low={pattern_low} pattern_high={pattern_high} pattern_exact={pattern_exact} \N{POLICE CARS REVOLVING LIGHT}")
    if passed:
        print(f"\N{WHITE HEAVY CHECK MARK} All Attribute tests passed for file {base_filename}")
    return passed

def check_event_count(datafile, expected_value, tolerance):
    "Checking that the number of records in the file is within tolerance of the expected_value"
    passed=True
    event_count=len(datafile.events)
    min_event_count=expected_value-tolerance
    max_event_count=expected_value+tolerance
    if event_count<min_event_count or event_count>max_event_count:
        passed=False
        print(f"\N{POLICE CARS REVOLVING LIGHT} Record count {event_count} is outside the tolerance of {tolerance} from an expected value of {expected_value} \N{POLICE CARS REVOLVING LIGHT}")
    if passed:
        print(f"\N{WHITE HEAVY CHECK MARK} Record count {event_count} is within a tolerance of {tolerance} from an expected value of {expected_value}")
    return passed

# 18-Aug-2021, KAB: General-purposed test for fragment count.  The idea behind this test
# is that each type of fragment can be tested individually, by calling this routine for
# each type.  The test is driven by a set of parameters that describe both the fragments
# to be tested (e.g. the HDF5 Group names) and the characteristics that they should have
# (e.g. the number of fragments that should be present).
#
# The parameters that are required by this routine are the following:
# * fragment_type_description - descriptive text for the fragment type, e.g. "WIB" or "PDS" or "Raw TP"
# * fragment_type - Type of the Fragment, e.g. "ProtoWIB" or "Trigger_Primitive"
# * hdf5_source_subsystem - the Subsystem of the Fragments to find,
#                         e.g. "Detector_Readout" or "Trigger"
# * expected_fragment_count - the expected number of fragments of this type
def check_fragment_count(datafile, params):
    debug_mask = 0
    if 'debug_mask' in params:
        debug_mask = params['debug_mask']
    min_count_list = []
    max_count_list = []
    subdet_string = ""
    if 'subdetector' in params:
        subdet_string = params['subdetector']

    "Checking that there are {params['expected_fragment_count']} {params['fragment_type_description']} fragments in each record in the file"
    passed=True
    h5_file = HDF5RawDataFile(datafile.name)
    records = h5_file.get_all_record_ids()
    for rec in records:
        tc_type_string = get_TC_type(h5_file, rec)
        rno_strings = get_record_ordinal_strings(rec, records)
        fragment_count_limits = get_fragment_count_limits(params, tc_type_string, rno_strings)
        if (debug_mask & 0x1) != 0:
            print(f'DataFileChecks Debug: the fragment count limits are {fragment_count_limits} for TC type {tc_type_string} and record ordinal strings {rno_strings}')
        if fragment_count_limits[0] not in min_count_list:
            min_count_list.append(fragment_count_limits[0])
        if fragment_count_limits[1] not in max_count_list:
            max_count_list.append(fragment_count_limits[1])
        if subdet_string == "":
            src_ids = h5_file.get_source_ids_for_fragment_type(rec, params['fragment_type'])
        else:
            src_ids = h5_file.get_source_ids_for_fragtype_and_subdetector(rec, params['fragment_type'], subdet_string)
        fragment_count=len(src_ids)
        if (debug_mask & 0x2) != 0:
            print(f'  DataFileChecks Debug: fragment count is {fragment_count}')
        if fragment_count<fragment_count_limits[0] or fragment_count>fragment_count_limits[1]:
            passed=False
            print(f"\N{POLICE CARS REVOLVING LIGHT} Record {rec} has an unexpected number of {params['fragment_type_description']} fragments: {fragment_count} (outside range {fragment_count_limits}) \N{POLICE CARS REVOLVING LIGHT}")
    if passed:
        min_count_list.sort()
        max_count_list.sort()
        if len(min_count_list) > 1 or len(max_count_list) > 1 or min_count_list[0] != max_count_list[0]:
            print(f"\N{WHITE HEAVY CHECK MARK} {params['fragment_type_description']} fragment count in range {min_count_list} to {max_count_list} confirmed in all {len(records)} records")
        else:
            print(f"\N{WHITE HEAVY CHECK MARK} {params['fragment_type_description']} fragment count of {min_count_list[0]} confirmed in all {len(records)} records")
    return passed

# 18-Aug-2021, KAB: general-purposed test for fragment sizes.  The idea behind this test
# is that each type of fragment can be tested individually, by calling this routine for
# each type.  The test is driven by a set of parameters that describe both the fragments
# to be tested (e.g. the HDF5 Group names) and the characteristics that they should have
# (e.g. the minimum and maximum fragment size).
#
# The parameters that are required by this routine are the following:
# * fragment_type_description - descriptive text for the fragment type, e.g. "WIB" or "PDS" or "Raw TP"
# * fragment_type - Type of the Fragment, e.g. "ProtoWIB" or "Trigger_Primitive"
# * hdf5_source_subsystem - the Subsystem of the Fragments to find,
#                         e.g. "Detector_Readout" or "Trigger"
# * min_size_bytes - the minimum size of fragments of this type
# * max_size_bytes - the maximum size of fragments of this type
def check_fragment_sizes(datafile, params):
    if params['expected_fragment_count'] == 0:
        return True
    debug_mask = 0
    if 'debug_mask' in params:
        debug_mask = params['debug_mask']
    min_size_list = []
    max_size_list = []
    subdet_string = ""
    if 'subdetector' in params:
        subdet_string = params['subdetector']

    "Checking that every {params['fragment_type_description']} fragment size is within its allowed range"
    passed=True
    h5_file = HDF5RawDataFile(datafile.name)
    records = h5_file.get_all_record_ids()
    for rec in records:
        tc_type_string = get_TC_type(h5_file, rec)
        rno_strings = get_record_ordinal_strings(rec, records)
        size_limits = get_fragment_size_limits(params, tc_type_string, rno_strings)
        if (debug_mask & 0x4) != 0:
            print(f'DataFileChecks Debug: the fragment size limits are {size_limits} for TC type {tc_type_string} and record ordinal strings {rno_strings}')
        if size_limits[0] not in min_size_list:
            min_size_list.append(size_limits[0])
        if size_limits[1] not in max_size_list:
            max_size_list.append(size_limits[1])
        if subdet_string == "":
            src_ids = h5_file.get_source_ids_for_fragment_type(rec, params['fragment_type'])
        else:
            src_ids = h5_file.get_source_ids_for_fragtype_and_subdetector(rec, params['fragment_type'], subdet_string)
        for src_id in src_ids:
            frag=h5_file.get_frag(rec,src_id);
            size=frag.get_size()
            if (debug_mask & 0x8) != 0:
                print(f'  DataFileChecks Debug: fragment size for SourceID {src_id} is {size}')
            if size<size_limits[0] or size>size_limits[1]:
                passed=False
                print(f" \N{POLICE CARS REVOLVING LIGHT} {params['fragment_type_description']} fragment for SrcID {src_id.to_string()} in record {rec} has size {size} (outside range {size_limits}) \N{POLICE CARS REVOLVING LIGHT}")
    if passed:
        min_size_list.sort()
        max_size_list.sort()
        print(f"\N{WHITE HEAVY CHECK MARK} All {params['fragment_type_description']} fragments in {len(records)} records have sizes between {min_size_list[0] if len(min_size_list) == 1 else min_size_list} and {max_size_list[0] if len(max_size_list) == 1 else max_size_list}")
    return passed

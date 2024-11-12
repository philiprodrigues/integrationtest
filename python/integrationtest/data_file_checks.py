import datetime
import h5py
import os.path
import re
from hdf5libs import HDF5RawDataFile
import daqdataformats
import trgdataformats

class DataFile:
    def __init__(self, filename):
        self.h5file=h5py.File(filename, 'r')
        self.events=self.h5file.keys()
        self.name=str(filename)

def sanity_check(datafile):
    "Very basic sanity checks on file"
    passed=True
    print("") # Clear potential dot from pytest
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
    "Checking that there are {params['expected_fragment_count']} {params['fragment_type_description']} fragments in each record in the file"
    passed=True
    h5_file = HDF5RawDataFile(datafile.name)
    records = h5_file.get_all_record_ids()
    for rec in records:
        src_ids = h5_file.get_source_ids_for_fragment_type(rec, params['fragment_type'])
        fragment_count=len(src_ids)
        if fragment_count != params['expected_fragment_count']:
            passed=False
            print(f"\N{POLICE CARS REVOLVING LIGHT} Record {event} has an unexpected number of {params['fragment_type_description']} fragments: {fragment_count} (expected {params['expected_fragment_count']}) \N{POLICE CARS REVOLVING LIGHT}")
    if passed:
        print(f"\N{WHITE HEAVY CHECK MARK} {params['fragment_type_description']} fragment count of {params['expected_fragment_count']} confirmed in all {len(records)} records")
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

    "Checking that every {params['fragment_type_description']} fragment size is between {params['min_size_bytes']} and {params['max_size_bytes']}"
    passed=True
    h5_file = HDF5RawDataFile(datafile.name)
    records = h5_file.get_all_record_ids()
    for rec in records:
        src_ids = h5_file.get_source_ids_for_fragment_type(rec, params['fragment_type'])
        for src_id in src_ids:
            frag=h5_file.get_frag(rec,src_id);
            size=frag.get_size()
            if size<params['min_size_bytes'] or size>params['max_size_bytes']:
                passed=False
                print(f" \N{POLICE CARS REVOLVING LIGHT} {params['fragment_type_description']} fragment {frag.name} in record {event} has size {size}, outside range [{params['min_size_bytes']}, {params['max_size_bytes']}] \N{POLICE CARS REVOLVING LIGHT}")
    if passed:
        print(f"\N{WHITE HEAVY CHECK MARK} All {params['fragment_type_description']} fragments in {len(records)} records have sizes between {params['min_size_bytes']} and {params['max_size_bytes']}")
    return passed

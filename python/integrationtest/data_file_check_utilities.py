from hdf5libs import HDF5RawDataFile
from daqdataformats import FragmentErrorBits
import daqdataformats
import trgdataformats
from num2words import num2words

def get_TC_type(h5_file, record_id):
    src_ids = h5_file.get_source_ids_for_fragment_type(record_id, 'Trigger_Candidate')
    if len(src_ids) == 1:
        for src_id in src_ids:
            frag = h5_file.get_frag(record_id, src_id);
            if frag.get_size() > 72:
                tc = trgdataformats.TriggerCandidate(frag.get_data())
                return trgdataformats.trigger_candidate_type_to_string(tc.data.type)
    return "kUnknown"

def get_record_ordinal_strings(record_id, full_record_list):
    ordinal_strings = []
    try:
        index = full_record_list.index(record_id)
        ordinal_strings.append(num2words(index+1, lang='en', to='ordinal'))
        if index == (len(full_record_list)-1):
            if len(ordinal_strings) >= 1 and index != 0:
                ordinal_strings.insert(0, "last")
            else:
                ordinal_strings.append("last")
        if len(full_record_list) > 1 and index == (len(full_record_list)-2):
            if len(ordinal_strings) >= 1 and index >= 2:
                ordinal_strings.insert(0, "penultimate")
            else:
                ordinal_strings.append("penultimate")
    except:
        pass
    return ordinal_strings

def get_fragment_count_limits(params, tc_type_string, record_ordinal_strings):
    # set absurd initial values that will indicate a problem in what the user specified
    min_count = 9999999
    max_count = 0

    # get first-level defaults from any top-level parameter specified by the user
    if 'expected_fragment_count' in params.keys():
        min_count = params['expected_fragment_count']
        max_count = params['expected_fragment_count']

    # check for counts that are specified by TC type
    if 'frag_counts_by_TC_type' in params.keys():
        tc_type_dict = params['frag_counts_by_TC_type']
        if tc_type_string in tc_type_dict.keys():
            count_dict = tc_type_dict[tc_type_string]
            if 'min_count' in count_dict.keys():
                min_count = count_dict['min_count']
            if 'max_count' in count_dict.keys():
                max_count = count_dict['max_count']
        elif 'default' in tc_type_dict.keys():
            count_dict = tc_type_dict['default']
            if 'min_count' in count_dict.keys():
                min_count = count_dict['min_count']
            if 'max_count' in count_dict.keys():
                max_count = count_dict['max_count']

    # check for counts that are specified by record number
    # (obviously, if both counts-by-TC-type and counts-by-record-ordinal are
    # specfied, counts-by-record-ordinal wins because it is looked up last)
    if 'frag_counts_by_record_ordinal' in params.keys() and len(record_ordinal_strings) > 0:
        rno_string = record_ordinal_strings[0]
        record_number_dict = params['frag_counts_by_record_ordinal']
        if rno_string in record_number_dict.keys():
            count_dict = record_number_dict[rno_string]
            if 'min_count' in count_dict.keys():
                min_count = count_dict['min_count']
            if 'max_count' in count_dict.keys():
                max_count = count_dict['max_count']
        elif 'default' in record_number_dict.keys():
            count_dict = record_number_dict['default']
            if 'min_count' in count_dict.keys():
                min_count = count_dict['min_count']
            if 'max_count' in count_dict.keys():
                max_count = count_dict['max_count']

    return [min_count, max_count]

def get_fragment_size_limits(params, tc_type_string, record_ordinal_strings):
    # set absurd initial values that will indicate a problem in what the user specified
    min_size = 9999999
    max_size = 0

    # get first-level defaults from any top-level parameters specified by the user
    if 'min_size_bytes' in params.keys():
        min_size = params['min_size_bytes']
    if 'max_size_bytes' in params.keys():
        max_size = params['max_size_bytes']

    # check for sizes that are specified by TC type
    if 'frag_sizes_by_TC_type' in params.keys():
        tc_type_dict = params['frag_sizes_by_TC_type']
        if tc_type_string in tc_type_dict.keys():
            size_dict = tc_type_dict[tc_type_string]
            if 'min_size_bytes' in size_dict.keys():
                min_size = size_dict['min_size_bytes']
            if 'max_size_bytes' in size_dict.keys():
                max_size = size_dict['max_size_bytes']
        elif 'default' in tc_type_dict.keys():
            size_dict = tc_type_dict['default']
            if 'min_size_bytes' in size_dict.keys():
                min_size = size_dict['min_size_bytes']
            if 'max_size_bytes' in size_dict.keys():
                max_size = size_dict['max_size_bytes']

    # check for sizes that are specified by record number
    # (obviously, if both sizes-by-TC-type and sizes-by-record-ordinal are
    # specfied, sizes-by-record-ordinal wins because it is looked up last)
    if 'frag_sizes_by_record_ordinal' in params.keys() and len(record_ordinal_strings) > 0:
        rno_string = record_ordinal_strings[0]
        record_number_dict = params['frag_sizes_by_record_ordinal']
        if rno_string in record_number_dict.keys():
            size_dict = record_number_dict[rno_string]
            if 'min_size_bytes' in size_dict.keys():
                min_size = size_dict['min_size_bytes']
            if 'max_size_bytes' in size_dict.keys():
                max_size = size_dict['max_size_bytes']
        elif 'default' in record_number_dict.keys():
            size_dict = record_number_dict['default']
            if 'min_size_bytes' in size_dict.keys():
                min_size = size_dict['min_size_bytes']
            if 'max_size_bytes' in size_dict.keys():
                max_size = size_dict['max_size_bytes']

    return [min_size, max_size]

def get_fragment_error_bitmask(params, tc_type_string, record_ordinal_strings):
    # Set default value (all bits allowed)
    error_bitmask = 0xFFFFFFFF

    # get first-level defaults from any top-level parameters specified by the user
    if 'error_bitmask' in params.keys():
        error_bitmask = params['error_bitmask']

    # check for bitmasks that are specified by TC type
    if 'frag_bitmasks_by_TC_type' in params.keys():
        tc_type_dict = params['frag_bitmasks_by_TC_type']
        if tc_type_string in tc_type_dict.keys():
            bitmask_dict = tc_type_dict[tc_type_string]
            if 'error_bitmask' in bitmask_dict.keys():
                error_bitmask = bitmask_dict['error_bitmask']
        elif 'default' in tc_type_dict.keys():
            bitmask_dict = tc_type_dict['default']
            if 'error_bitmask' in bitmask_dict.keys():
                error_bitmask = bitmask_dict['error_bitmask']

    # check for bitmasks that are specified by record number
    # (obviously, if both bitmasks-by-TC-type and bitmasks-by-record-ordinal are
    # specfied, bitmasks-by-record-ordinal wins because it is looked up last)
    if 'frag_bitmasks_by_record_ordinal' in params.keys() and len(record_ordinal_strings) > 0:
        rno_string = record_ordinal_strings[0]
        record_number_dict = params['frag_bitmasks_by_record_ordinal']
        if rno_string in record_number_dict.keys():
            bitmask_dict = record_number_dict[rno_string]
            if 'error_bitmask' in bitmask_dict.keys():
                error_bitmask = bitmask_dict['error_bitmask']
        elif 'default' in record_number_dict.keys():
            bitmask_dict = record_number_dict['default']
            if 'error_bitmask' in bitmask_dict.keys():
                error_bitmask = bitmask_dict['error_bitmask']

    return error_bitmask

def get_set_error_bit_names(error_bits):
    error_bits_temp = error_bits
    names = []
    current_bit = 0
    while error_bits_temp != 0:
        if error_bits_temp & 0x1 == 0x1:
            names.append(FragmentErrorBits(current_bit).name)
        error_bits_temp = error_bits_temp >> 1
        current_bit = current_bit + 1
    return names
        

def record_ordinal_string_all_tests():
    record_ordinal_string_test01()
    record_ordinal_string_test02()
    record_ordinal_string_test03()
    record_ordinal_string_test04()
    record_ordinal_string_test05()
    record_ordinal_string_test06()
    record_ordinal_string_test07()

def record_ordinal_string_test01():
    test_list = [999]
    requested_value = 999
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "first" or ord_strings[1] != "last":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value=requested_value ordinal_strings={ord_strings}')

def record_ordinal_string_test02():
    test_list = [888, 999]
    requested_value = 888
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "first" or ord_strings[1] != "penultimate":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 999
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "last" or ord_strings[1] != "second":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')

def record_ordinal_string_test03():
    test_list = [777, 888, 999]
    requested_value = 777
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "first":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 888
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "second" or ord_strings[1] != "penultimate":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 999
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "last" or ord_strings[1] != "third":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')

def record_ordinal_string_test04():
    test_list = [666, 777, 888, 999]
    requested_value = 666
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "first":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 777
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "second":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 888
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "penultimate" or ord_strings[1] != "third":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 999
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "last" or ord_strings[1] != "fourth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')

def record_ordinal_string_test05():
    test_list = [555, 666, 777, 888, 999]
    requested_value = 555
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "first":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 666
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "second":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 777
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "third":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 888
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "penultimate" or ord_strings[1] != "fourth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 999
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "last" or ord_strings[1] != "fifth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')

def record_ordinal_string_test06():
    test_list = [111, 222, 333, 444, 555, 666, 777, 888, 999]
    requested_value = 111
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "first":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 222
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "second":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 333
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "third":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 444
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "fourth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 555
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "fifth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 666
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "sixth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 777
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 1 or ord_strings[0] != "seventh":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 888
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "penultimate" or ord_strings[1] != "eighth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 999
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 2 or ord_strings[0] != "last" or ord_strings[1] != "ninth":
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')

def record_ordinal_string_test07():
    test_list = [111, 222, 333, 444, 555, 666, 777, 888, 999]
    requested_value = 123
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 0:
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')
    requested_value = 9999
    ord_strings = get_record_ordinal_strings(requested_value, test_list)
    if len(ord_strings) != 0:
        print(f'\N{POLICE CARS REVOLVING LIGHT} UNIT TEST FAILURE: test_list={test_list} value={requested_value} ordinal_strings={ord_strings}')

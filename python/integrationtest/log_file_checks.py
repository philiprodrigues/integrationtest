from glob import glob
import re

def log_has_no_errors(log_file_name, print_logfilename_for_problems=True, excluded_substring_list=[], required_substring_list=[], print_required_message_report=False):
    ok=True
    ignored_problem_count=0
    required_counts={ss:0 for ss in required_substring_list}
    for line in open(log_file_name, errors='ignore').readlines():

        # First check if the line appears to be in the standard format of messages produced with our logging package
        # For lines produced with our logging package, the first two words in the line are the date and time, then the severity

        bad_line=False
        match_logline_prefix = re.search(r"^20[0-9][0-9]-[A-Z][a-z][a-z]-[0-9]+\s+[0-9:,]+\s+([A-Z]+)", line)
        if match_logline_prefix:
            severity=match_logline_prefix.group(1)
            if severity in ("WARNING", "ERROR", "FATAL"):
                bad_line=True
        else: # This line's not produced with our logging package, so let's just look for bad words
            if "WARN" in line or "Warn" in line or "warn" in line or \
               "ERROR" in line or "Error" in line or "error" in line or \
               "FATAL" in line or "Fatal" in line or "fatal" in line or \
               "egmentation fault" in line:
                bad_line=True

        if bad_line:
            ignore_this_problem=False
            for excluded_substring in excluded_substring_list:
                match_obj = re.search(excluded_substring, line)
                if match_obj:
                    ignore_this_problem=True
                    break
            if ignore_this_problem:
                bad_line=False
                ignored_problem_count+=1
        if bad_line:
            for substr in required_substring_list:
                match_obj = re.search(substr, line)
                if match_obj:
                    bad_line=False
                    break
        if bad_line:
            if ok and print_logfilename_for_problems:
                print("----------")
                print(f"\N{POLICE CARS REVOLVING LIGHT} Problem(s) found in logfile {log_file_name}:")
            print(line)
            ok=False

        for substr in required_substring_list:
            match_obj = re.search(substr, line)
            if match_obj:
                required_counts[substr] += 1
    if ignored_problem_count > 0:
        print(f"\N{CONSTRUCTION SIGN} Note: problems found in {ignored_problem_count} lines in {log_file_name} were ignored based on {len(excluded_substring_list)} phrase(s). \N{CONSTRUCTION SIGN}")
    overall_required_message_count = 0
    found_message_count = 0
    for (substr,count) in required_counts.items():
        if count == 0:
            print(f"\N{POLICE CARS REVOLVING LIGHT} Failure: Required log message \"{substr}\" was not found in {log_file_name} \N{POLICE CARS REVOLVING LIGHT}")
            ok=False
        elif print_required_message_report:
            print(f"\N{WHITE HEAVY CHECK MARK} Required log message \"{substr}\" occurred {count} times in {log_file_name}")
        overall_required_message_count += count
        if count > 0:
            found_message_count += 1
    if overall_required_message_count > 0:
        print(f"\N{WHITE HEAVY CHECK MARK} Note: required log messages were found in {overall_required_message_count} lines in {log_file_name} based on {found_message_count} required messages (of a total of {len(required_substring_list)} required messages).")
    return ok

# 23-Nov-2021, KAB: added the ability for users to specify sets of excluded substrings, to
# enable checking of all log files, and to print out the logfile name when there are problems.
#
# This function accepts the following arguments:
# * the list of logfiles to be checked (array of PythonPath objects)
# * a flag to control whether all logfiles are checked for problems or whether checking
#   stops as soon as one file with problems is found (default is to check them all)
# * a flag to control whether the logfile name is printed to the console when an a problem
#   is first found in that logfile (default is printout)
# * the sets of excluded substrings.  This goal of this argument is to allow certain
#   select messages to be ignored so that overall checking of logfiles can remain enabled
#   without being distracted by 'expected' problems.  This argument is expected to be a
#   dictionary keyed by strings that might appear in the logfile name and having values
#   that are lists of excluded phrases.  Both the logfile name key and the excluded phrases
#   support regular expressions.  Use r"<regex_pattern>" to handle any special patterns.
#   For example:
#   ex_sub_map = {"ruemu": ["expected problem phrase 1", "expected problem  phrase 2"]}
#   ex_sub_map = {"ruemu": [r"expected problem phrase \d+"]}
def logs_are_error_free(log_file_names, show_all_problems=True, print_logfilename_for_problems=True,
                        excluded_substring_map={}, required_substring_map={}, print_required_message_report=False):
    all_ok=True
    print("") # Clear potential dot from pytest
    for log in log_file_names:
        exclusions=[]
        requireds=[]
        for exclusion_key in excluded_substring_map.keys():
            #print(f"Checking for match for {exclusion_key} in {log.name}")
            match_obj = re.search(exclusion_key, log.name)
            if match_obj:
                exclusions += excluded_substring_map[exclusion_key]
                break
        for required_key in required_substring_map.keys():
            match_obj = re.search(required_key, log.name)
            if match_obj:
                requireds += required_substring_map[required_key]
                break
        
        single_ok=log_has_no_errors(log, print_logfilename_for_problems, exclusions, requireds, print_required_message_report)

        if not single_ok:
            all_ok=False
            if not show_all_problems:
                break
    return all_ok

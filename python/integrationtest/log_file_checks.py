from glob import glob
import re

def log_has_no_errors(log_file_name):
    ok=True
    for line in open(log_file_name).readlines():

        # First check if the line appears to be in the standard format of messages produced with our logging package
        # For lines produced with our logging package, the first two words in the line are the date and time, then the severity

        match_logline_prefix = re.search(r"^20[0-9][0-9]-[A-Z][a-z][a-z]-[0-9]+\s+[0-9:,]+\s+([A-Z]+)", line)
        if match_logline_prefix:
            severity=match_logline_prefix.group(1)
            if severity in ("WARN", "ERROR", "FATAL"):
                print(line)
                ok=False
        else: # This line's not produced with our logging package, so let's just look for bad words
            if "WARN" in line or "Warn" in line or "warn" in line or \
               "ERROR" in line or "Error" in line or "error" in line or \
               "FATAL" in line or "Fatal" in line or "fatal" in line or \
               "egmentation fault" in line:
                print(line)
                ok=False
            
    return ok

def logs_are_error_free(log_file_names):
    all_ok=True
    for log in log_file_names:
        all_ok=all_ok and log_has_no_errors(log)
    return all_ok

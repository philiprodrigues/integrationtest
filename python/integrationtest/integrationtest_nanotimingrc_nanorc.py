import pytest
import shutil
import filecmp
import subprocess
import os.path
import os
import pathlib
from integrationtest.config_file_gen import write_config
import time
import random
from subprocess import PIPE
from integrationtest.daq_conf_json_gen import create_daq_conf_json
from integrationtest.dro_map_gen import generate_default_dropmap_file
from integrationtest.timing_conf_json_gen import create_timing_conf_json
import json 

def file_exists(s):
    p=pathlib.Path(s)
    return p.exists() and p.is_file()

def parametrize_fixture_with_items(metafunc, fixture, itemsname):
    """Parametrize a fixture using the contents of variable `listname`
    from module scope. We want to distinguish between the cases where
    the list is a list of strings, and a list of lists of strings. We
    do this by checking whether the first item in the list is a
    string. Not perfect, but better than nothing

    """
    the_items=getattr(metafunc.module, itemsname)
    if isinstance(the_items, dict):
        metafunc.parametrize(fixture, the_items.values(), ids=the_items.keys(), indirect=True)
    elif isinstance(the_items, list) or isinstance(the_items, tuple):
        if type(the_items[0])==str:
            params=[the_items]
        else:
            params=the_items
        metafunc.parametrize(fixture, params, indirect=True)

def pytest_generate_tests(metafunc):
    # We want to be able to run multiple confgens and multiple nanorcs
    # from one pytest module, but the fixtures for running the
    # external commands are module-scoped, so we need to parametrize
    # the fixtures. This could be done by adding "params=..." to the
    # @pytest.fixture decorator at each fixture, but the user doesn't
    # have access to that point in the code. So instead we pull
    # variables from the module (which the user _does_ have access to)
    # and parametrize the fixtures here in pytest_generate_tests,
    # which is run at pytest startup

    parametrize_fixture_with_items(metafunc, "run_nanotimingrc_and_nanorc", "nanorc_command_list")
  
class CreateJsonResult:
        pass

class RunResult:
        pass

@pytest.fixture(scope="module")
def create_timing_conf_folder(request, tmp_path_factory):
    """Run the confgen to produce the configuration json files

    The name of the module to use is taken (indirectly) from the
    `confgen_name` variable in the global scope of the test module,
    and the arguments for the confgen are taken from the
    `confgen_arguments` variable in the same place. These variables
    are converted into parameters for this fixture by the
    pytest_generate_tests function, to allow multiple confgens to be
    produced by one pytest module

    """
    script_name=getattr(request.module, "timing_confgen_name")

    connections_filepath=getattr(request.module, "connections_filepath")
    # if timing_conf_file is not provided in test_timing.py, then default_timing_conf_file will be used 
    default_timing_conf_file =  create_timing_conf_json(tmp_path_factory.getbasetemp() / f"temp_timing_config_filepath.json", connections_filepath)
    timing_conf_file=getattr(request.module, "timing_conf_file", default_timing_conf_file)

    json_dir=tmp_path_factory.getbasetemp() / f"json{request.param_index}"
    logfile = tmp_path_factory.getbasetemp() / f"stdouterr{request.param_index}.txt"
    config_arg = ["-c", timing_conf_file]
    
    if not os.path.isdir(json_dir):
        print("Creating json files for nanotimingrc")
        try:
            with open(logfile, "wb") as outerr:
                subprocess.run([script_name] + config_arg + [str(json_dir)], check=True, stdout=outerr,stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as err:
            print(f"Generating json files failed with exit code {err.returncode}")
            pytest.fail()

    result=CreateJsonResult()
    result.confgen_name=script_name
    result.json_dir=json_dir
    result.log_file=logfile

    yield result

@pytest.fixture(scope="module")
def create_nanorc_conf_folder(request, tmp_path_factory):
    """Run the confgen to produce the configuration json files

    The name of the module to use is taken (indirectly) from the
    `confgen_name` variable in the global scope of the test module,
    and the arguments for the confgen are taken from the
    `confgen_arguments` variable in the same place. These variables
    are converted into parameters for this fixture by the
    pytest_generate_tests function, to allow multiple confgens to be
    produced by one pytest module

    """

    script_name=getattr(request.module, "confgen_name")
    # if getattr(request.module, "daqconf_filepath") is not None:

    json_dir=tmp_path_factory.getbasetemp() / f"daqconf{request.param_index}"
    logfile = tmp_path_factory.getbasetemp() / f"stdouterr{request.param_index}.txt"
    
    default_daq_conf = create_daq_conf_json(tmp_path_factory.getbasetemp() / f"temp_daqconf_filepath.json")
    # if daqconf_filepath is not provided in test_timing.py, then default_daq_conf will be used 
    daqconf_file_path = getattr(request.module, "daqconf_filepath", default_daq_conf)
    
    default_dro_map = generate_default_dropmap_file(tmp_path_factory.getbasetemp() / f"temp_dromap_filepath.json", 2)
    # if dro_map_filepath is not provided in test_timing.py, then default_dro_map will be used 
    dro_map_file_path = getattr(request.module, "dro_map_filepath", default_dro_map)

    config_arg = ["-c", daqconf_file_path]
    dro_map_file = ["--detector-readout-map-file", dro_map_file_path]
    
    if not os.path.isdir(json_dir):
        print("Creating json files for nanorc")
        try:
            with open(logfile, "wb") as outerr:
                subprocess.run([script_name] + config_arg + dro_map_file + [str(json_dir)], check=True, stdout=outerr,stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as err:
            print(f"Generating json files failed with exit code {err.returncode}")
            pytest.fail()

    result=CreateJsonResult()
    result.confgen_name=script_name
    result.confgen_config={}
    result.json_dir=json_dir
    result.log_file=logfile

    yield result


@pytest.fixture(scope="module")
def run_nanotimingrc_and_nanorc(request, create_timing_conf_folder, create_nanorc_conf_folder, tmp_path_factory):
    """Run nanorc with the json files created by `create_json_files`. The
    commands specified by the `nanorc_command_list` variable in the
    test module are executed. If `nanorc_command_list`'s items are
    themselves lists, then nanorc will be run multiple times, once for
    each set of arguments in the list

    """
    nanorc_command_list=request.param

    nanotimingrc="nanotimingrc"

    run_dir=tmp_path_factory.mktemp("run")

    session_name = ["nanotiming-test-session"]
    part_num = "--partition-number 7".split()
    run = subprocess.Popen([nanotimingrc] + part_num + [str(create_timing_conf_folder.json_dir)] + session_name, text=True, stdin=PIPE)
    run.stdin.write("boot\nconf\nstart\nstatus\n")
    run.stdin.flush()
    time.sleep(8) # this ensures that there is enough time for nanorc to run without interfering with the nanotimingrc run
    
    nanorc="nanorc"
    part_num_diff = "--partition-number 2".split()
    session_name_daq = ["daq-test-session"]

    if nanorc is None:
       nanorc="nanorc"
    run1 = subprocess.Popen([nanorc] + part_num_diff + [str(create_nanorc_conf_folder.json_dir)] + session_name_daq + nanorc_command_list)
    run1.wait()
    run1.terminate()
    run.communicate("status\nexit\n")
    run.terminate()

    nanotimingrc_command_list = "boot conf start status status exit".split()

    result_nanotimingrc=RunResult()
    result_nanotimingrc.completed_process=run
    result_nanotimingrc.confgen_name=create_timing_conf_folder.confgen_name
    result_nanotimingrc.nanotimingrc_commands=nanotimingrc_command_list
    result_nanotimingrc.run_dir=run_dir
    result_nanotimingrc.json_dir=create_timing_conf_folder.json_dir
    result_nanotimingrc.log_files=list(run_dir.glob("log_*.txt"))
    result_nanotimingrc.opmon_files=list(run_dir.glob("info_*.json"))

    result_nanorc=RunResult()
    result_nanorc.completed_process=run1
    result_nanorc.confgen_name=create_nanorc_conf_folder.confgen_name
    result_nanorc.nanorc_commands=nanorc_command_list
    result_nanorc.run_dir=run_dir
    result_nanorc.json_dir=create_nanorc_conf_folder.json_dir
    result_nanorc.log_files=list(run_dir.glob("log_*.txt"))
    result_nanorc.opmon_files=list(run_dir.glob("info_*.json"))

    yield result_nanotimingrc, result_nanorc

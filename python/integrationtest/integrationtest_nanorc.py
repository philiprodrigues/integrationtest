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

    parametrize_fixture_with_items(metafunc, "create_json_files", "confgen_arguments")
    parametrize_fixture_with_items(metafunc, "run_nanorc", "nanorc_command_list")


@pytest.fixture(scope="module")
def create_json_files(request, tmp_path_factory):
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
    conf_dict=request.param

    dro_map_required = getattr(request.module, "dro_map_required", True)

    disable_connectivity_service = request.config.getoption("--disable-connectivity-service")

    class CreateJsonResult:
        pass

    json_dir=tmp_path_factory.getbasetemp() / f"json{request.param_index}"
    logfile = tmp_path_factory.getbasetemp() / f"stdouterr{request.param_index}.txt"
    configfile = tmp_path_factory.getbasetemp() / f"daqconf{request.param_index}.json"
    dro_map_file = tmp_path_factory.getbasetemp() / f"DROMap{request.param_index}.json"
    config_arg = ["--config", configfile]
    if dro_map_required and not "detector_readout_map_file" in conf_dict["readout"].keys():
        config_arg += ["--detector-readout-map-file", dro_map_file]
    if dro_map_required and not file_exists(dro_map_file):
        dro_map_contents = getattr(request.module, "dro_map_contents", "[ ]")
        dro_map_contents = conf_dict["readout"].pop("dro_map", dro_map_contents)

        with open(dro_map_file, 'w+') as f:
            f.write(dro_map_contents)
            f.close()

    if disable_connectivity_service:
        conf_dict["boot"]["use_connectivity_service"] = False
        conf_dict["boot"]["start_connectivity_service"] = False

    if not "connectivity_service_port" in conf_dict["boot"].keys():
        conf_dict["boot"]["connectivity_service_port"] = 15000 + random.randrange(100)
    write_config(configfile, conf_dict)

    if not os.path.isdir(json_dir):
        print("Creating json files")
        try:
            with open(logfile, "wb") as outerr:
                subprocess.run([script_name] + config_arg + [str(json_dir)], check=True, stdout=outerr,stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as err:
            print(f"Generating json files failed with exit code {err.returncode}")
            pytest.fail()

    result=CreateJsonResult()
    result.confgen_name=script_name
    result.confgen_config=conf_dict
    result.json_dir=json_dir
    result.log_file=logfile

    yield result


@pytest.fixture(scope="module")
def create_minimal_json_files(request, tmp_path_factory):
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

    class CreateJsonResult:
        pass

    json_dir=tmp_path_factory.getbasetemp() / f"json_minimal_{request.param_index}"
    logfile = tmp_path_factory.getbasetemp() / f"stdouterr_minimal_{request.param_index}.txt"
    dro_map_file = tmp_path_factory.getbasetemp() / f"DROMap.json"
    config_arg = ["--detector-readout-map-file", dro_map_file]

    if not file_exists(dro_map_file):
        dro_map_contents = getattr(request.module, "dro_map_contents", "[ ]")
        with open(dro_map_file, 'w+') as f:
            f.write(dro_map_contents)
            f.close()

    if not os.path.isdir(json_dir):
        print("Creating json files")
        try:
            with open(logfile, "wb") as outerr:
                subprocess.run([script_name] + config_arg + [str(json_dir)], check=True, stdout=outerr,stderr=subprocess.STDOUT)
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
def run_nanorc(request, create_json_files, tmp_path_factory):
    """Run nanorc with the json files created by `create_json_files`. The
    commands specified by the `nanorc_command_list` variable in the
    test module are executed. If `nanorc_command_list`'s items are
    themselves lists, then nanorc will be run multiple times, once for
    each set of arguments in the list

    """
    command_list=request.param

    nanorc=request.config.getoption("--nanorc-path")
    if nanorc is None:
        nanorc="nanorc"
    nanorc_options=request.config.getoption("--nanorc-option")
    nanorc_option_strings = []
    if nanorc_options is not None:
        for opt in nanorc_options:
            if len(opt) > 2:
                print("Nanorc options take either 0 or 1 arguments!")
                pytest.fail()
            if len(opt[0]) == 1:
                nanorc_option_strings.append("-" + ''.join(opt))
            else:
                nanorc_option_strings.append("--"+ opt[0])
                if(len(opt) == 2):
                    nanorc_option_strings.append(opt[1])

    class RunResult:
        pass

    run_dir=tmp_path_factory.mktemp("run")

    # 28-Jun-2022, KAB: added the ability to handle a non-standard output directory
    rawdata_filename_prefix="swtest"
    rawdata_dirs=[run_dir]
    rawdata_paths=[]
    tpset_dir=run_dir
    tpset_path=""

    try:
        for config_section in create_json_files.confgen_config.keys():
            if "dataflow" in config_section:
                for app_idx, app_config in enumerate(create_json_files.confgen_config[config_section]["apps"]):
                    if "output_paths" in app_config.keys():
                        this_path = create_json_files.confgen_config[config_section]["apps"][app_idx]["output_paths"]
                        rawdata_paths = rawdata_paths + this_path
            if config_section == "trigger":
                if "tpset_output_path" in create_json_files.confgen_config[config_section].keys():
                    tpset_path = create_json_files.confgen_config[config_section]["tpset_output_path"]
    except ValueError:
        # nothing to do since we've already assigned a default value
        pass
    try:
        if "op_env" in create_json_files.confgen_config["detector"]:
            rawdata_filename_prefix = create_json_files.confgen_config["detector"]["op_env"]
            #print(f"The raw data filename prefix is {rawdata_filename_prefix}")
    except ValueError:
        # nothing to do since we've already assigned a default value
        pass
    for path in rawdata_paths:
        rawdata_dir=pathlib.Path(path)
        if rawdata_dir not in rawdata_dirs:
            rawdata_dirs.append(rawdata_dir)
        # deal with any pre-existing data files
        temp_suffix=".temp_saved"
        now=time.time()
        for file_obj in rawdata_dir.glob(f'{rawdata_filename_prefix}_*.hdf5'):
            print(f'Renaming raw data file from earlier test: {str(file_obj)}')
            new_name=str(file_obj) + temp_suffix
            file_obj.rename(new_name)
        for file_obj in rawdata_dir.glob(f'{rawdata_filename_prefix}_*.hdf5{temp_suffix}'):
            modified_time=file_obj.stat().st_mtime
            if (now-modified_time) > 3600:
                print(f'Deleting raw data file from earlier test: {str(file_obj)}')
                file_obj.unlink(True)  # missing is OK
    if (tpset_path != "" and tpset_path != "."):
        tpset_dir=pathlib.Path(tpset_path)
        # deal with any pre-existing data files
        temp_suffix=".temp_saved"
        now=time.time()
        for file_obj in tpset_dir.glob(f"tpstream_*.hdf5"):
            print(f'Renaming raw data file from earlier test: {str(file_obj)}')
            new_name=str(file_obj) + temp_suffix
            file_obj.rename(new_name)
        for file_obj in tpset_dir.glob(f"tpstream_*.hdf5{temp_suffix}"):
            modified_time=file_obj.stat().st_mtime
            if (now-modified_time) > 3600:
                print(f'Deleting raw data file from earlier test: {str(file_obj)}')
                file_obj.unlink(True)  # missing is OK

    print('++++++++++ NanoRC Run BEGIN ++++++++++', flush=True) # Apparently need to flush before subprocess.run
    result=RunResult()
    result.completed_process=subprocess.run([nanorc] + nanorc_option_strings + [str(create_json_files.json_dir)] + command_list, cwd=run_dir)
    result.confgen_name=create_json_files.confgen_name
    result.confgen_config=create_json_files.confgen_config
    result.nanorc_commands=command_list
    result.run_dir=run_dir
    result.json_dir=create_json_files.json_dir
    result.data_files=[]
    for rawdata_dir in rawdata_dirs:
        result.data_files += list(rawdata_dir.glob(f"{rawdata_filename_prefix}_*.hdf5"))
    result.tpset_files=list(tpset_dir.glob(f"tpstream_*.hdf5"))
    result.log_files=list(run_dir.glob("log_*.txt"))
    result.opmon_files=list(run_dir.glob("info_*.json"))
    print('---------- NanoRC Run END ----------',  flush=True)
    yield result


@pytest.fixture(scope="module")
def diff_conf_files(create_minimal_json_files, create_json_files):
    class DiffResult:
        pass

    left  = create_minimal_json_files.json_dir
    right = create_json_files        .json_dir

    result = DiffResult()
    result.diff = filecmp.dircmp(left, right).diff_files + filecmp.dircmp(left/'data', right/'data').diff_files
    yield result

import pytest
import shutil
import filecmp
import subprocess
import os.path
import os
import pathlib
import pkg_resources
import oksdbinterfaces
from integrationtest.integrationtest_commandline import file_exists
from integrationtest.oks_bootjson_gen import write_config, generate_boot_json
from oksconfgen.get_session_apps import get_session_apps, get_segment_apps
from oksconfgen.generate_hwmap import generate_hwmap
from oksconfgen.generate_readoutOKS import generate_readout
from oksconfgen.consolidate import consolidate_files
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

    parametrize_fixture_with_items(metafunc, "create_config_files", "confgen_arguments")
    parametrize_fixture_with_items(metafunc, "run_nanorc", "nanorc_command_list")


@pytest.fixture(scope="module")
def create_config_files(request, tmp_path_factory):
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

    class CreateConfigResult:
        pass

    config_dir=tmp_path_factory.mktemp("config")
    boot_file=config_dir / "boot.json"    
    configfile = config_dir / "config.json"
    dro_map_file = config_dir / "ReadoutMap.data.xml"
    readout_db = config_dir / "readout-segment.data.xml"    
    config_db = config_dir / "integtest-session.data.xml"    
    logfile = tmp_path_factory.getbasetemp() / f"stdouterr{request.param_index}.txt"
    
    if dro_map_required and not file_exists(dro_map_file):
        dro_map_contents = getattr(request.module, "dro_map_contents", None)
        if dro_map_contents != None:
            generate_hwmap(str(dro_map_file), *dro_map_contents)                    

    generate_readout(str(dro_map_file), str(readout_db), ["appdal/connections", "appdal/fsm", "appdal/data-store-params", "appdal/moduleconfs"], True, True)

    integtest_conf = os.path.dirname(__file__) + "/config/test-config.data.xml"
    print(f"Integtest consolidated config file: {integtest_conf}")    
    consolidate_files(str(config_db), str(readout_db), str(dro_map_file), integtest_conf)    

    db = oksdbinterfaces.Configuration("oksconfig:" + str(config_db))
    session = db.get_dals(class_name="Session")[0]
    root_segment = db.get_dal("Segment", "root-segment")
    ru_segment = db.get_dal("Segment", "ru-segment")
    root_segment.segments.append(ru_segment)
    db.update_dal(root_segment)         
    session.segment = root_segment
    session.id = "integtest"    
    db.update_dal(session)
    db.commit()        

    if disable_connectivity_service:
        conf_dict["boot"]["use_connectivity_service"] = False
        conf_dict["boot"]["start_connectivity_service"] = False

    if not "connectivity_service_port" in conf_dict["boot"].keys():
        conf_dict["boot"]["connectivity_service_port"] = 15000 + random.randrange(100)
    write_config(configfile, conf_dict)
    apps = get_session_apps(str(config_db))   
    write_config(boot_file, generate_boot_json(apps, conf_dict["boot"]["connectivity_service_port"], str(config_db)))    

    result=CreateConfigResult()
    result.confgen_config=conf_dict
    result.config_dir=config_dir
    result.log_file=logfile
    result.session = "integtest"    

    yield result

@pytest.fixture(scope="module")
def run_nanorc(request, create_config_files, tmp_path_factory):
    """Run nanorc with the OKS DB files created by `create_config_files`. The
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
        for config_section in create_config_files.confgen_config.keys():
            if "dataflow" in config_section:
                for app_idx, app_config in enumerate(create_config_files.confgen_config[config_section]["apps"]):
                    if "output_paths" in app_config.keys():
                        this_path = create_config_files.confgen_config[config_section]["apps"][app_idx]["output_paths"]
                        rawdata_paths = rawdata_paths + this_path
            if config_section == "trigger":
                if "tpset_output_path" in create_config_files.confgen_config[config_section].keys():
                    tpset_path = create_config_files.confgen_config[config_section]["tpset_output_path"]
    except ValueError:
        # nothing to do since we've already assigned a default value
        pass
    try:
        if "op_env" in create_config_files.confgen_config["detector"]:
            rawdata_filename_prefix = create_config_files.confgen_config["detector"]["op_env"]
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
    result.completed_process=subprocess.run([nanorc] + nanorc_option_strings + [str(create_config_files.config_dir)] + [str(create_config_files.session)] + command_list, cwd=run_dir)
    result.confgen_config=create_config_files.confgen_config
    result.session = create_config_files.session    
    result.nanorc_commands=command_list
    result.run_dir=run_dir
    result.config_dir=create_config_files.config_dir
    result.data_files=[]
    for rawdata_dir in rawdata_dirs:
        result.data_files += list(rawdata_dir.glob(f"{rawdata_filename_prefix}_*.hdf5"))
    result.tpset_files=list(tpset_dir.glob(f"tpstream_*.hdf5"))
    result.log_files=list(run_dir.glob("log_*.txt"))
    result.opmon_files=list(run_dir.glob("info_*.json"))
    print('---------- NanoRC Run END ----------',  flush=True)
    yield result


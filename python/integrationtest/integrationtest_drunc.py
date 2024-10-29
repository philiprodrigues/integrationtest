import pytest
import subprocess
import pathlib
import getpass
import os
import pkg_resources
import conffwk
from integrationtest.integrationtest_commandline import file_exists
from integrationtest.data_classes import CreateConfigResult
from daqconf.generate_hwmap import generate_hwmap
from daqconf.generate import (
    generate_readout,
    generate_fakedata,
    generate_trigger,
    generate_hsi,
    generate_dataflow,
    generate_session,
)
from daqconf.consolidate import consolidate_files, consolidate_db, copy_configuration
from daqconf.set_connectivity_service_port import (
    set_connectivity_service_port,
)
import time
import random


def parametrize_fixture_with_items(metafunc, fixture, itemsname):
    """Parametrize a fixture using the contents of variable `listname`
    from module scope. We want to distinguish between the cases where
    the list is a list of strings, and a list of lists of strings. We
    do this by checking whether the first item in the list is a
    string. Not perfect, but better than nothing

    """
    the_items = getattr(metafunc.module, itemsname)
    if isinstance(the_items, dict):
        metafunc.parametrize(
            fixture, the_items.values(), ids=the_items.keys(), indirect=True
        )
    elif isinstance(the_items, list) or isinstance(the_items, tuple):
        if type(the_items[0]) == str:
            params = [the_items]
        else:
            params = the_items
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
    `base_oks_config` variable in the global scope of the test module,
    and the arguments for the confgen are taken from the
    `confgen_arguments` variable in the same place. These variables
    are converted into parameters for this fixture by the
    pytest_generate_tests function, to allow multiple confgens to be
    produced by one pytest module

    """
    drunc_config = request.param

    disable_connectivity_service = request.config.getoption(
        "--disable-connectivity-service"
    )

    config_dir = tmp_path_factory.mktemp("config")
    boot_file = config_dir / "boot.json"
    configfile = config_dir / "config.json"
    dro_map_file = config_dir / "ReadoutMap.data.xml"
    readout_db = config_dir / "readout-segment.data.xml"
    dataflow_db = config_dir / "df-segment.data.xml"
    trigger_db = config_dir / "trg-segment.data.xml"
    hsi_db = config_dir / "hsi-segment.data.xml"
    config_db = config_dir / "integtest-session-resolved.data.xml"
    temp_config_db = config_dir / "integtest-session.data.xml"
    logfile = tmp_path_factory.getbasetemp() / f"stdouterr{request.param_index}.txt"

    integtest_conf = drunc_config.config_db

    object_databases = getattr(request.module, "object_databases", [])
    local_object_databases = copy_configuration(config_dir, object_databases)

    print()  # Blank line
    if file_exists(integtest_conf):
        print(f"Integtest preconfigured config file: {integtest_conf}")
        consolidate_files(str(temp_config_db), integtest_conf, *local_object_databases)
    else:
        if not drunc_config.use_fakedataprod:
            if not file_exists(dro_map_file):
                dro_map_config = drunc_config.dro_map_config
                if dro_map_config != None:
                    generate_hwmap(
                        str(dro_map_file),
                        dro_map_config.n_streams,
                        dro_map_config.n_apps,
                        dro_map_config.det_id,
                        dro_map_config.app_host,
                        dro_map_config.eth_protocol,
                        dro_map_config.flx_mode,
                    )

            if not file_exists(readout_db):
                generate_readout(
                    readoutmap=str(dro_map_file),
                    oksfile=str(readout_db),
                    include=local_object_databases,
                    generate_segment=True,
                    emulated_file_name=drunc_config.frame_file,
                    tpg_enabled=drunc_config.tpg_enabled,
                )
        elif not file_exists(readout_db):
            generate_fakedata(
                oksfile=str(readout_db),
                include=local_object_databases,
                generate_segment=True,
                n_streams=drunc_config.dro_map_config.n_streams,
                n_apps=drunc_config.dro_map_config.n_apps,
                det_id=drunc_config.dro_map_config.det_id,
            )

        generate_trigger(
            oksfile=str(trigger_db),
            include=local_object_databases,
            generate_segment=True,
            tpg_enabled=drunc_config.tpg_enabled,
            hsi_enabled=drunc_config.fake_hsi_enabled,
        )
        if drunc_config.fake_hsi_enabled:
            generate_hsi(
                oksfile=str(hsi_db),
                include=local_object_databases,
                generate_segment=True,
            )
        generate_dataflow(
            oksfile=str(dataflow_db),
            include=local_object_databases,
            n_dfapps=drunc_config.n_df_apps,
            tpwriting_enabled=drunc_config.tpg_enabled,
            generate_segment=True,
            n_data_writers=drunc_config.n_data_writers,
        )

        generate_session(
            oksfile=str(temp_config_db),
            include=local_object_databases
            + [str(readout_db), str(trigger_db), str(dataflow_db)]
            + ([str(hsi_db)] if drunc_config.fake_hsi_enabled else []),
            session_name=drunc_config.session,
            op_env=drunc_config.op_env,
            connectivity_service_is_infrastructure_app=drunc_config.drunc_connsvc,
            disable_connectivity_service=disable_connectivity_service,
        )

    drunc_config.connsvc_port = set_connectivity_service_port(
        oksfile=str(temp_config_db),
        session_name=drunc_config.session,
        connsvc_port=drunc_config.connsvc_port, # Default is 0, which causes random port to be selected
    )

    consolidate_db(str(temp_config_db), str(config_db))

    dal = conffwk.dal.module("generated", "schema/appmodel/fdmodules.schema.xml")
    db = conffwk.Configuration("oksconflibs:" + str(config_db))

    def apply_update(obj, substitution):
        for name, value in substitution.updates.items():
            setattr(obj, name, value)

        db.update_dal(obj)

    for substitution in drunc_config.config_substitutions:
        if substitution.obj_id != "*":
            obj = db.get_dal(class_name=substitution.obj_class, uid=substitution.obj_id)
            apply_update(obj, substitution)
        else:
            objs = db.get_dals(class_name=substitution.obj_class)
            for obj in objs:
                apply_update(obj, substitution)

    db.commit()

    # For preconfigured tests, disable starting the ConnSvc if the ConnectionService is an ifapp or unused
    sessionobj = db.get_dal(class_name="Session", uid=drunc_config.session)
    if sessionobj.connectivity_service is None:
        drunc_config.drunc_connsvc = True
    for if_app in sessionobj.infrastructure_applications:
        if if_app.className() == "ConnectionService":
            drunc_config.drunc_connsvc = True

    result = CreateConfigResult(
        config=drunc_config,
        config_dir=config_dir,
        config_file=config_db,
        log_file=logfile,
        data_dirs=[],
    )

    yield result


@pytest.fixture(scope="module")
def run_nanorc(request, create_config_files, tmp_path_factory):
    """Run nanorc with the OKS DB files created by `create_config_files`. The
    commands specified by the `nanorc_command_list` variable in the
    test module are executed. If `nanorc_command_list`'s items are
    themselves lists, then nanorc will be run multiple times, once for
    each set of arguments in the list

    """
    command_list = request.param

    disable_connectivity_service = request.config.getoption(
        "--disable-connectivity-service"
    )

    run_dir = tmp_path_factory.mktemp("run")

    connsvc_obj = None
    if (
        not disable_connectivity_service
        and not create_config_files.config.drunc_connsvc
    ):
        # start connsvc
        print(
            f"Starting Connectivity Service on port {create_config_files.config.connsvc_port}"
        )

        connsvc_env = os.environ.copy()
        connsvc_env["CONNECTION_FLASK_DEBUG"] = str(
            create_config_files.config.connsvc_debug_level
        )

        connsvc_log = open(
            run_dir
            / f"log_{getpass.getuser()}_{create_config_files.config.session}_connectivity-service.log",
            "w",
        )
        connsvc_obj = subprocess.Popen(
            f"gunicorn -b 0.0.0.0:{create_config_files.config.connsvc_port} --workers=1 --worker-class=gthread --threads=2 --timeout 5000000000 --log-level=info connection-service.connection-flask:app".split(),
            stdout=connsvc_log,
            stderr=connsvc_log,
            env=connsvc_env,
        )

    nanorc = request.config.getoption("--nanorc-path")
    if nanorc is None:
        nanorc = "drunc-unified-shell"
    nanorc_options = request.config.getoption("--nanorc-option")
    nanorc_option_strings = []
    if nanorc_options is not None:
        for opt in nanorc_options:
            if len(opt) > 2:
                print("Nanorc options take either 0 or 1 arguments!")
                pytest.fail()
            if len(opt[0]) == 1:
                nanorc_option_strings.append("-" + "".join(opt))
            else:
                nanorc_option_strings.append("--" + opt[0])
                if len(opt) == 2:
                    nanorc_option_strings.append(opt[1])

    class RunResult:
        pass

    # 28-Jun-2022, KAB: added the ability to handle a non-standard output directory
    rawdata_dirs = [run_dir]
    rawdata_paths = create_config_files.data_dirs
    tpset_dir = run_dir
    tpset_path = ""

    for path in rawdata_paths:
        rawdata_dir = pathlib.Path(path)
        if rawdata_dir not in rawdata_dirs:
            rawdata_dirs.append(rawdata_dir)
        # deal with any pre-existing data files
        temp_suffix = ".temp_saved"
        now = time.time()
        for file_obj in rawdata_dir.glob(
            f"{create_config_files.config.op_env}_raw*.hdf5"
        ):
            print(f"Renaming raw data file from earlier test: {str(file_obj)}")
            new_name = str(file_obj) + temp_suffix
            file_obj.rename(new_name)
        for file_obj in rawdata_dir.glob(
            f"{create_config_files.config.op_env}_raw*.hdf5{temp_suffix}"
        ):
            modified_time = file_obj.stat().st_mtime
            if (now - modified_time) > 3600:
                print(f"Deleting raw data file from earlier test: {str(file_obj)}")
                file_obj.unlink(True)  # missing is OK
    if tpset_path != "" and tpset_path != ".":
        tpset_dir = pathlib.Path(tpset_path)
        # deal with any pre-existing data files
        temp_suffix = ".temp_saved"
        now = time.time()
        for file_obj in tpset_dir.glob(
            f"{create_config_files.config.op_env}_tps*.hdf5"
        ):
            print(f"Renaming TP data file from earlier test: {str(file_obj)}")
            new_name = str(file_obj) + temp_suffix
            file_obj.rename(new_name)
        for file_obj in tpset_dir.glob(
            f"{create_config_files.config.op_env}_tps*.hdf5{temp_suffix}"
        ):
            modified_time = file_obj.stat().st_mtime
            if (now - modified_time) > 3600:
                print(f"Deleting TP data file from earlier test: {str(file_obj)}")
                file_obj.unlink(True)  # missing is OK

    print(
        "++++++++++ DRUNC Run BEGIN ++++++++++", flush=True
    )  # Apparently need to flush before subprocess.run
    result = RunResult()
    result.completed_process = subprocess.run(
        [nanorc]
        + nanorc_option_strings
        + [str("ssh-standalone")]
        + [str(create_config_files.config_file)]
        + [str(create_config_files.config.session)]
        + command_list,
        cwd=run_dir,
    )

    if connsvc_obj is not None:
        connsvc_obj.send_signal(2)
        connsvc_obj.kill()

    if create_config_files.config.attempt_cleanup:
        print(
            "Checking for remaining gunicorn and drunc-controller processes", flush=True
        )
        subprocess.run(["killall", "gunicorn", "drunc-controller"])

    result.confgen_config = create_config_files.config
    result.session = create_config_files.config.session
    result.nanorc_commands = command_list
    result.run_dir = run_dir
    result.config_dir = create_config_files.config_dir
    result.data_files = []
    for rawdata_dir in rawdata_dirs:
        result.data_files += list(
            rawdata_dir.glob(f"{create_config_files.config.op_env}_raw_*.hdf5")
        )
    result.tpset_files = list(
        tpset_dir.glob(f"{create_config_files.config.op_env}_tp_*.hdf5")
    )
    result.log_files = list(run_dir.glob("log_*.txt")) + list(run_dir.glob("log_*.log"))
    result.opmon_files = list(run_dir.glob("info_*.json"))
    print("---------- DRUNC Run END ----------", flush=True)
    yield result

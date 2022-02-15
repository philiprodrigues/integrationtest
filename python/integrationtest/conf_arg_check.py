import pytest
import shutil
import subprocess
import os.path
import filecmp
import os
import pathlib

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
        metafunc.parametrize(fixture, params, indirect=True, ids=[f[0] for f in the_items])
    
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
    # parametrize_fixture_with_items(metafunc, "create_json_files", "base_conf_args", "create_json_default_files")
    parametrize_fixture_with_items(metafunc, "create_json_files_log", "confgen_arguments")

@pytest.fixture(scope="module")
def create_json_files_log(request, tmp_path_factory):
    """Run the confgen to produce the configuration json files

    The name of the module to use is taken (indirectly) from the
    `confgen_name` variable in the global scope of the test module,
    and the arguments for the confgen are taken from the
    `confgen_arguments` variable in the same place. These variables
    are converted into parameters for this fixture by the
    pytest_generate_tests function, to allow multiple confgens to be
    produced by one pytest module

    """
    module_name=getattr(request.module, "confgen_name")
    module_arguments=request.param

    class CreateJsonResult:
        pass
    
    json_dir=tmp_path_factory.getbasetemp() /  f"json{request.param_index}"
    logfile = tmp_path_factory.getbasetemp()/"stdouterr.txt"
    if not os.path.isdir(json_dir):
        print("Creating json files")
        try:
            with open(logfile, "wb") as outerr:
                subprocess.run(["python", "-m"] + [module_name] + module_arguments + [str(json_dir)], check=True, stdout=outerr,stderr=outerr)
        except subprocess.CalledProcessError as err:
            print(f"Generating json files failed with exit code {err.returncode}")
            pytest.fail()

    result=CreateJsonResult()
    result.confgen_name=module_name
    result.confgen_arguments=module_arguments
    result.json_dir=json_dir
    result.log_file=logfile
    
    yield result

@pytest.fixture(scope="module")
def create_json_default_files(request, tmp_path_factory):
    """Run the confgen to produce the configuration json files

    The name of the module to use is taken (indirectly) from the
    `confgen_name` variable in the global scope of the test module,
    and the arguments for the confgen are taken from the
    `confgen_arguments` variable in the same place. These variables
    are converted into parameters for this fixture by the
    pytest_generate_tests function, to allow multiple confgens to be
    produced by one pytest module

    """
    module_name=getattr(request.module, "confgen_name")
    module_arguments=getattr(request.module, 'base_conf_args')

    class CreateJsonResult:
        pass
    
    json_dir=tmp_path_factory.getbasetemp() /  f"json{request.param_index}"
    if not os.path.isdir(json_dir):
        print("Creating json files")
        try:
            subprocess.run(["python", "-m"] + [module_name] + module_arguments + [str(json_dir)], check=True)
        except subprocess.CalledProcessError as err:
            print(f"Generating json files failed with exit code {err.returncode}")
            pytest.fail()

    result=CreateJsonResult()
    result.confgen_name=module_name
    result.confgen_arguments=module_arguments
    result.json_dir=json_dir
    
    yield result

@pytest.fixture(scope="module")
def diff_conf_files(create_json_default_files, create_json_files_log):
    class DiffResult:
        pass

    left=create_json_default_files.json_dir
    right=create_json_files_log.json_dir
    
    result=DiffResult()
    result.diff = filecmp.dircmp(left, right).diff_files
    yield result
    

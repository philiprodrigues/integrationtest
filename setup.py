from setuptools import setup

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="integrationtest",
    install_requires=[
        "pytest", "configparser",
    ],
    # the following makes a plugin available to pytest
    entry_points={"pytest11": ["name_of_plugin = integrationtest.integrationtest_commandline"],
                  },              
    include_package_data=True                  
)

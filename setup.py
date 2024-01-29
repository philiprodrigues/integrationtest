from setuptools import setup

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="integrationtest",
    install_requires=[
        "pytest", "configparser",
    ],
    # the following makes a plugin available to pytest
    entry_points={
        "pytest11":[
            "parallel_rc_plugin = integrationtest.integrationtest_nanotimingrc_nanorc",
            "name_of_plugin = integrationtest.integrationtest_nanorc"
        ]
    }
)

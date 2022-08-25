import configparser

"""
[daqconf]

[timing]

[readout]

[trigger]

[dataflow]

[dataflow.dataflow0]

[dqm]
"""

def get_default_config_dict():
    config_dict = {}

    config_dict["daqconf"] = {}
    config_dict["timing"] = {}
    config_dict["readout"] = {}
    config_dict["trigger"] = {}
    config_dict["dataflow"] = {}
    config_dict["dataflow.dataflow0"] = {}
    config_dict["dqm"] = {}

    return config_dict

def write_config(file_name, config_dict):
    parser = configparser.ConfigParser()
    parser.read_dict(config_dict)
    with open(file_name, 'w+') as fp:
        parser.write(fp)
        fp.flush()
        fp.close()
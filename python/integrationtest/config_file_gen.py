import json


def get_default_config_dict():
    config_dict = {}

    config_dict["boot"] = {}
    config_dict["timing"] = {}
    config_dict["readout"] = {}
    config_dict["trigger"] = {}
    config_dict["dataflow"] = {
        "apps": [{
            "app_name": "dataflow0"
        }]
    }
    config_dict["dqm"] = {}

    return config_dict

def get_timing_config_dict():
    config_dict = {}

    config_dict["boot"] = {}
    config_dict["timing_hardware_interface"] = {}
    config_dict["timing_master_controller"] = {}
    config_dict["timing_fanout_controller"] = {}

    return config_dict

def write_config(file_name, config_dict):
    with open(file_name, 'w+') as fp:
        json.dump(config_dict, fp)
        fp.flush()
        fp.close()
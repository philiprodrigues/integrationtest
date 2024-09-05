import json
from integrationtest.data_classes import drunc_config

def get_default_config_dict():
    config_dict = {}

    config_dict["detector"] = {}
    config_dict["daq_common"] = {}
    config_dict["boot"] = {}
    config_dict["hsi"] = {}
    config_dict["timing"] = {}
    config_dict["readout"] = {}
    config_dict["trigger"] = {}
    config_dict["dataflow"] = {
        "apps": [{
            "app_name": "dataflow0"
        }]
    }

    return config_dict

def get_default_oks_config_dict():
    return drunc_config()

def write_config(file_name, config_dict):
    with open(file_name, 'w+') as fp:
        json.dump(config_dict, fp, indent=4)
        fp.flush()
        fp.close()

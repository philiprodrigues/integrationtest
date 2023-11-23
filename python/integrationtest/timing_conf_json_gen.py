import json

dict = {
    "boot": {
        "use_connectivity_service": True,
        "start_connectivity_service": True,
        "connectivity_service_host": "localhost",
        "connectivity_service_port": 16032
    },
    "timing_hardware_interface": {
        "host_thi": "localhost",
        "firmware_type": "pdii"
        # "timing_hw_connections_file": "connections.xml"
    },
    "timing_master_controller": {
        "host_tmc": "localhost",
        "master_device_name": "MST"
    }
}


# this function creates the daq config json needed to run the fddaqconf_gen 
# command for creating the daq conf files 
def create_timing_conf_json(filename, connections_file):
    with open(filename, 'w+') as fp:
        dict["timing_hardware_interface"]["timing_hw_connections_file"] = connections_file
        json.dump(dict, fp, indent=4)
        fp.flush()
        fp.close()
    return filename
import json

dict = {
    "boot": {
      "use_connectivity_service": True,
      "start_connectivity_service": False,
      "connectivity_service_host": "localhost",
      "connectivity_service_port": 16032
    }, 
    "daq_common": {
      "data_rate_slowdown_factor": 1
    },
    "detector": {
      "clock_speed_hz": 62500000
    },
    "readout": {
      "use_fake_cards": True,
      "default_data_file": "asset://?label=WIBEth&subsystem=readout"
    },
    "trigger": {
      "trigger_window_before_ticks": 1000,
      "trigger_window_after_ticks": 1000
    },
    "hsi": {
      "random_trigger_rate_hz": 1.0
    }
}

# this function creates the daq config json needed to run the fddaqconf_gen 
# command for creating the daq conf files 
def create_daq_conf_json(filename):
    with open(filename, 'w+') as fp:
        json.dump(dict, fp, indent=4)
        fp.flush()
        fp.close()
    return filename
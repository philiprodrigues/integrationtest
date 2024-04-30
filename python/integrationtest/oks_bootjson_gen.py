import json
from random import randrange


def write_config(file_name, config_dict):
    with open(file_name, "w+") as fp:
        json.dump(config_dict, fp, indent=4)
        fp.flush()
        fp.close()


def generate_boot_json(app_names=[], connsvc_port=15000, config_db="test-session.data.xml"):

    responselistener_port = randrange(2048, 65500)
    config_dict = {
        "apps": {},
        "env": {
            "DUNEDAQ_ERS_DEBUG_LEVEL": "getenv_ifset",
            "DUNEDAQ_ERS_ERROR": "erstrace,throttle,lstdout",
            "DUNEDAQ_ERS_FATAL": "erstrace,lstdout",
            "DUNEDAQ_ERS_INFO": "erstrace,throttle,lstdout",
            "DUNEDAQ_ERS_VERBOSITY_LEVEL": "getenv:1",
            "DUNEDAQ_ERS_WARNING": "erstrace,throttle,lstdout",
        },
        "exec": {
            "consvc_ssh": {
                "args": [
                    "--bind=0.0.0.0:{APP_PORT}",
                    "--workers=1",
                    "--worker-class=gthread",
                    "--threads=2",
                    "--timeout=0",
                    "--pid={APP_NAME}_{APP_PORT}.pid",
                    "connection-service.connection-flask:app",
                ],
                "cmd": "gunicorn",
                "env": {
                    "CONNECTION_FLASK_DEBUG": "getenv:2",
                    "PATH": "getenv",
                    "PYTHONPATH": "getenv",
                },
            },
            "daq_application_ssh": {
                "args": [
                    "--name",
                    "{APP_NAME}",
                    "-c",
                    "{CMD_FAC}",
                    "-i",
                    "{INFO_SVC}",
                    "--configurationService",
                    "oksconfig:" + config_db,
                ],
                "cmd": "daq_application",
                "comment": "Application profile using PATH variables (lower start time)",
                "env": {
                    "CET_PLUGIN_PATH": "getenv",
                    "CMD_FAC": "rest://localhost:{APP_PORT}",
                    "CONNECTION_SERVER": "localhost",
                    "DETCHANNELMAPS_SHARE": "getenv",
                    "DUNEDAQ_DB_PATH": "getenv",
                    "DUNEDAQ_SHARE_PATH": "getenv",
                    "INFO_SVC": "file://info_{APP_NAME}_{APP_PORT}.json",
                    "LD_LIBRARY_PATH": "getenv",
                    "PATH": "getenv",
                    "TIMING_SHARE": "getenv",
                    "TRACE_FILE": "getenv:/tmp/trace_buffer_{APP_HOST}_{DUNEDAQ_PARTITION}",
                },
            },
        },
        "external_connections": [],
        "hosts-ctrl": {"connectionservice": "localhost", "local": "localhost"},
        "hosts-data": {"local": "localhost"},
        "response_listener": {"port": responselistener_port},
        "services": {
            "connectionservice": {
                "exec": "consvc_ssh",
                "host": "connectionservice",
                "port": connsvc_port,
                "update-env": {"CONNECTION_PORT": "{APP_PORT}"},
            }
        },
    }

    port = 3000 + 100 * randrange(0, 10)

    for app in app_names:
        config_dict["apps"][app] = {
            "exec": "daq_application_ssh",
            "host": "local",
            "port": port,
        }
        port = port + 1

    return config_dict


def generate_dromap_contents(n_streams, n_apps = 1, det_id = 3, app_type = "eth", app_host = "localhost",
                             eth_protocol = "udp", flx_mode = "fix_rate", flx_protocol = "full"):
    return [n_streams, n_apps, det_id, app_host, eth_protocol, flx_mode]
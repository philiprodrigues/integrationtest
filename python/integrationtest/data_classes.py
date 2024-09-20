from dataclasses import dataclass, field


@dataclass
class DROMap_config:
    n_streams: int
    n_apps: int = 1
    det_id: int = 3
    app_host: str = "localhost"
    eth_protocol: str = "udp"
    flx_mode: str = "fix_rate"


@dataclass
class config_substitution:
    obj_class: str
    obj_id: str = "*"
    updates: dict = field(default_factory=dict)


@dataclass
class drunc_config:
    op_env: str = "integtest"
    session: str = "integtest"
    dro_map_config: DROMap_config = DROMap_config(1)
    frame_file: str = "asset://?checksum=e96fd6efd3f98a9a3bfaba32975b476e"
    tpg_enabled: bool = False
    fake_hsi_enabled: bool = False
    config_db: str = ""
    n_df_apps: int = 1
    object_databases: list[str] = field(default_factory=list)
    config_substitutions: list[config_substitution] = field(default_factory=list)
    attempt_cleanup: bool = False


@dataclass
class CreateConfigResult:
    config: drunc_config
    config_dir: str
    config_file: str
    log_file: str
    data_dirs: list[str]
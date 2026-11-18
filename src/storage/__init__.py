from src.storage.detector import detect_installed_clouds
from src.storage.ftp_client import connect_ftp, ftp_test, ftp_upload_backups
from src.storage.local_sync import sync_to_directory
from src.storage.rclone_client import (
    download_rclone_binary,
    find_rclone,
    list_rclone_remotes,
    open_rclone_terminal_config,
    rclone_run,
)
from src.storage.webdav_client import (
    get_webdav_base_url,
    webdav_test,
    webdav_upload_backups,
)

__all__ = [
    "detect_installed_clouds",
    "connect_ftp",
    "ftp_test",
    "ftp_upload_backups",
    "sync_to_directory",
    "download_rclone_binary",
    "find_rclone",
    "list_rclone_remotes",
    "open_rclone_terminal_config",
    "rclone_run",
    "get_webdav_base_url",
    "webdav_test",
    "webdav_upload_backups",
]

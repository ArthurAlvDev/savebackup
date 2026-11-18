"""
Constantes globais e caminhos do sistema.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from typing import Any

APP_NAME = "SaveBackup"
APP_TITLE = "Save Backup"
APP_ID = "SaveBackup.GameSaveManager.2.0"
APP_VERSION = "2.2.1"
APP_AUTHOR = "OlacDev"
APP_URL = "https://olacdev.com/"
MUTEX_NAME = "Local\\SaveBackup.SingleInstance"

FROZEN = getattr(sys, "frozen", False)
IS_WIN = sys.platform == "win32"

# DiretÃ³rio base do executÃ¡vel ou do script raiz
APP_DIR = Path(sys.executable if FROZEN else __file__).resolve().parent
# Quando rodando via src/config/constants.py, a raiz do projeto Ã© dois nÃ­veis acima
if not FROZEN:
    # Se estamos dentro de src/config, a raiz da aplicaÃ§Ã£o Ã© SaveBackup_App/
    if (APP_DIR.parent.parent / "locales").exists():
        APP_ROOT = APP_DIR.parent.parent
    else:
        APP_ROOT = APP_DIR
else:
    APP_ROOT = APP_DIR

# Suporte ao PyInstaller --onefile via _MEIPASS
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_ROOT))

# Modo portÃ¡til: se existir 'portable.txt' ao lado do executÃ¡vel, grava na prÃ³pria pasta
IS_PORTABLE = (APP_ROOT / "portable.txt").exists() or (APP_DIR / "portable.txt").exists()
DATA_DIR = (APP_ROOT / "data") if IS_PORTABLE else (Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME)
CONFIG_FILE = DATA_DIR / "config.json"
RCLONE_LOCAL = DATA_DIR / "rclone.exe"
RCLONE_RELEASE_API = "https://api.github.com/repos/rclone/rclone/releases/latest"

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

DEFAULT_DEST = str(Path.home() / "Documents" / "SaveBackups")

DEFAULTS = {
    "lang": "pt",
    "folders": [],
    "backup_dirs": [DEFAULT_DEST],
    "local_enabled": True,
    "local_minutes": 30,
    "keep_local": 10,
    "cloud_enabled": False,
    "cloud_provider": "rclone",  # rclone | local_cloud | ftp | webdav | network
    "cloud_minutes": 120,
    "cloud_keep_days": 0,
    # Rclone
    "cloud_remote": "",
    "cloud_path": "SaveBackups",
    # Nativo: Pasta de nuvem local (OneDrive / Google Drive / Dropbox / Mega)
    "native_cloud_dir": "",
    # Nativo: FTP / FTPS
    "ftp_host": "",
    "ftp_port": 21,
    "ftp_user": "",
    "ftp_pass": "",
    "ftp_path": "/SaveBackups",
    "ftp_tls": False,
    # Nativo: WebDAV (Nextcloud, ownCloud, Koofr, pCloud, Box...)
    "webdav_url": "",
    "webdav_user": "",
    "webdav_pass": "",
    "webdav_path": "SaveBackups",
    # Nativo: Rede / SMB
    "net_path": "",
    # Sistema
    "autostart": False,
    "close_to_tray": True,
    "minimize_to_tray": True,
    "last_local": 0,
    "last_cloud": 0,
}


def get_icon_path() -> str | None:
    """Busca o arquivo de Ã­cone (.ico) no bundle do PyInstaller ou na pasta da aplicaÃ§Ã£o."""
    search_dirs = [BUNDLE_DIR, APP_ROOT, APP_DIR]
    for folder in search_dirs:
        for name in ("logo.ico", "icon.ico", "SaveBackup.ico", "assets/logo.ico"):
            cand = folder / name
            if cand.is_file():
                return str(cand)
    return None


def toint(value: Any, default: int, minimum: int = 0) -> int:
    """Converte valor para inteiro com limite mÃ­nimo e fallback seguro."""
    try:
        return max(minimum, int(str(value).strip()))
    except (ValueError, TypeError):
        return default

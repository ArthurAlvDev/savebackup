"""
Detecção automática de clientes de nuvem instalados no Windows (OneDrive, Google Drive, Dropbox, MEGA, etc.).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.config.constants import IS_WIN


def detect_installed_clouds() -> dict[str, str]:
    """Varre caminhos conhecidos do sistema e variáveis de ambiente em busca de pastas de nuvem."""
    found: dict[str, str] = {}
    home = Path.home()

    # 1. Microsoft OneDrive
    for env_var in ("OneDriveConsumer", "OneDriveCommercial", "OneDrive"):
        val = os.environ.get(env_var)
        if val and Path(val).is_dir():
            found["OneDrive"] = str(Path(val))
            break
    if "OneDrive" not in found and (home / "OneDrive").is_dir():
        found["OneDrive"] = str(home / "OneDrive")

    # 2. Dropbox (lê info.json oficial do Dropbox)
    for base in (os.environ.get("APPDATA"), os.environ.get("LOCALAPPDATA")):
        if base:
            info_file = Path(base) / "Dropbox" / "info.json"
            if info_file.is_file():
                try:
                    data = json.loads(info_file.read_text(encoding="utf-8"))
                    for section in ("personal", "business"):
                        if section in data and "path" in data[section]:
                            p = Path(data[section]["path"])
                            if p.is_dir():
                                found["Dropbox"] = str(p)
                                break
                except Exception:
                    pass
    if "Dropbox" not in found and (home / "Dropbox").is_dir():
        found["Dropbox"] = str(home / "Dropbox")

    # 3. Google Drive (pastas padrão ou unidades virtuais mapeadas G:, H:, etc.)
    for p in (home / "Google Drive", home / "My Drive", home / "Meu Drive"):
        if p.is_dir():
            found["Google Drive"] = str(p)
            break
    if "Google Drive" not in found and IS_WIN:
        for letter in "GHIJKLMNOPQRSTUVWXYZ":
            for sub in ("My Drive", "Meu Drive", "Mi unidad"):
                cand = Path(f"{letter}:\\{sub}")
                if cand.is_dir():
                    found[f"Google Drive ({letter}:)"] = str(cand)
                    break

    # 4. Outros serviços conhecidos
    for name, folder in (
        ("MEGA", "MEGA"),
        ("Nextcloud", "Nextcloud"),
        ("iCloud Drive", "iCloudDrive"),
        ("pCloud", "pCloud Drive"),
    ):
        cand = home / folder
        if cand.is_dir():
            found[name] = str(cand)

    return found

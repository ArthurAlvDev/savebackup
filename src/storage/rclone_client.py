"""
Integração com o utilitário Rclone (suporte a +70 serviços de armazenamento em nuvem).
"""
from __future__ import annotations

import io
from pathlib import Path
import shutil
import subprocess
from typing import Callable
import urllib.request
import zipfile

from src.config.constants import (
    APP_DIR,
    APP_ROOT,
    NEW_CONSOLE,
    NO_WINDOW,
    RCLONE_LOCAL,
    RCLONE_URL,
)


def find_rclone() -> str | None:
    """Busca o executável rclone.exe no diretório de dados, na pasta do app ou no PATH do sistema."""
    if RCLONE_LOCAL.exists():
        return str(RCLONE_LOCAL)
    if (APP_ROOT / "rclone.exe").exists():
        return str(APP_ROOT / "rclone.exe")
    if (APP_DIR / "rclone.exe").exists():
        return str(APP_DIR / "rclone.exe")
    return shutil.which("rclone")


def rclone_run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Executa um comando rclone ocultando janelas de console indesejadas."""
    exe = find_rclone()
    if not exe:
        raise RuntimeError("rclone não encontrado")
    return subprocess.run(
        [exe, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=NO_WINDOW,
    )


def download_rclone_binary(
    log_func: Callable[[str], None],
    t_func: Callable[..., str],
    on_success: Callable[[], None] | None = None,
) -> None:
    """Baixa e extrai rclone.exe oficial de forma autônoma para a pasta de dados."""
    try:
        log_func(t_func("log_dl_rclone"))
        data = urllib.request.urlopen(RCLONE_URL, timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in z.namelist():
                if n.endswith("/rclone.exe"):
                    RCLONE_LOCAL.parent.mkdir(parents=True, exist_ok=True)
                    RCLONE_LOCAL.write_bytes(z.read(n))
                    break
        log_func(t_func("log_rclone_installed"))
        if on_success:
            on_success()
    except Exception as e:
        log_func(t_func("log_upload_err", e))


def open_rclone_terminal_config() -> subprocess.Popen | None:
    """Abre uma nova janela de console para o assistente interativo `rclone config`."""
    exe = find_rclone()
    if not exe:
        return None
    return subprocess.Popen([exe, "config"], creationflags=NEW_CONSOLE)


def list_rclone_remotes() -> list[str]:
    """Obtém a lista de remotos configurados no Rclone."""
    if not find_rclone():
        return []
    res = rclone_run(["listremotes"])
    if res.returncode == 0:
        return [line.strip().rstrip(":") for line in res.stdout.splitlines() if line.strip()]
    return []

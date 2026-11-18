"""
Integração com o utilitário Rclone (suporte a +70 serviços de armazenamento em nuvem).
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
from typing import Callable
import urllib.request
import zipfile

from src.config.constants import (
    APP_DIR,
    APP_ROOT,
    APP_VERSION,
    NEW_CONSOLE,
    NO_WINDOW,
    RCLONE_LOCAL,
    RCLONE_RELEASE_API,
)


def validate_remote_value(value: str, label: str) -> str:
    """
    Valida nomes de remoto/pasta usados como argumento do rclone.

    Impede que um valor de configuração seja interpretado como opção de linha
    de comando (ex.: `--config`), o que permitiria redirecionar a execução.
    """
    text = str(value).strip()
    if not text:
        raise ValueError(f"{label} vazio.")
    if text.startswith("-"):
        raise ValueError(f"{label} inválido: não pode começar com '-'.")
    if any(ch in text for ch in "\r\n\0"):
        raise ValueError(f"{label} inválido: contém caractere de controle.")
    return text


def build_remote_target(remote: str, path: str) -> str:
    """Monta `remoto:caminho` após validar as duas partes."""
    safe_remote = validate_remote_value(remote, "Remoto")
    safe_path = validate_remote_value(path, "Pasta na nuvem")
    return f"{safe_remote}:{safe_path}"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fetch(url: str, timeout: int = 60) -> bytes:
    """GET com User-Agent identificado (downloads.rclone.org recusa o padrão do urllib)."""
    request = urllib.request.Request(
        url, headers={"User-Agent": f"SaveBackup/{APP_VERSION} (+https://olacdev.com/)"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return resp.read()


def _latest_release_assets() -> tuple[str, str]:
    """
    Descobre, na API de releases do rclone, a URL do .zip do Windows e a de SHA256SUMS.

    Retorna `(url_do_zip, url_do_sha256sums)`. Levanta erro se não encontrar.
    """
    data = json.loads(_fetch(RCLONE_RELEASE_API, timeout=60).decode("utf-8"))
    assets = {
        str(a.get("name", "")): str(a.get("browser_download_url", ""))
        for a in data.get("assets", [])
    }
    zip_url = next(
        (
            url
            for name, url in assets.items()
            if name.endswith("windows-amd64.zip")
        ),
        "",
    )
    sums_url = assets.get("SHA256SUMS", "")
    if not zip_url or not sums_url:
        raise RuntimeError("release do rclone sem windows-amd64.zip ou SHA256SUMS")
    return zip_url, sums_url


def _official_sha256_hashes(sums_url: str) -> set[str]:
    """Lê a lista oficial de hashes (SHA256SUMS) publicada no release do rclone."""
    raw = _fetch(sums_url, timeout=60).decode("utf-8", errors="replace")
    hashes: set[str] = set()
    for line in raw.splitlines():
        parts = line.split()
        if parts and len(parts[0]) == 64:
            hashes.add(parts[0].lower())
    return hashes


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
    """
    Baixa e extrai rclone.exe oficial para a pasta de dados.

    Antes de gravar, confere o SHA-256 do arquivo contra o SHA256SUMS oficial
    do release do rclone. Se a verificação falhar, nada é instalado: o app
    nunca executa um binário não conferido.
    """
    try:
        log_func(t_func("log_dl_rclone"))
        zip_url, sums_url = _latest_release_assets()
        data = _fetch(zip_url, timeout=180)

        expected = _official_sha256_hashes(sums_url)
        actual = _sha256(data)
        if actual not in expected:
            log_func(t_func("log_rclone_checksum_fail"))
            return

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

"""
Cliente nativo FTP e FTPS (TLS).
"""
from __future__ import annotations

from datetime import datetime, timedelta
import ftplib
from pathlib import Path
from typing import Any

from src.config.constants import toint


def connect_ftp(cfg: dict[str, Any]) -> ftplib.FTP:
    """Abre conexão com o servidor FTP ou FTPS com suporte a UTF-8."""
    host = str(cfg.get("ftp_host", "")).strip()
    port = toint(cfg.get("ftp_port", 21), 21, 1)
    user = str(cfg.get("ftp_user", "")).strip() or "anonymous"
    passwd = str(cfg.get("ftp_pass", ""))
    use_tls = bool(cfg.get("ftp_tls", False))

    if not host:
        raise ValueError("Host FTP vazio.")

    ftp = ftplib.FTP_TLS(timeout=30) if use_tls else ftplib.FTP(timeout=30)
    ftp.connect(host, port)
    ftp.login(user, passwd)
    if use_tls and isinstance(ftp, ftplib.FTP_TLS):
        ftp.prot_p()
    ftp.encoding = "utf-8"
    return ftp


def ftp_mkdirs(ftp: ftplib.FTP, remote_path: str) -> None:
    """Garante que a hierarquia de pastas remota exista, criando pastas ausentes."""
    parts = [p for p in remote_path.replace("\\", "/").split("/") if p]
    if remote_path.startswith("/"):
        ftp.cwd("/")
    for part in parts:
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            try:
                ftp.mkd(part)
            except ftplib.error_perm:
                pass
            ftp.cwd(part)


def ftp_test(cfg: dict[str, Any]) -> None:
    """Testa a conexão e a criação da pasta remota no FTP."""
    ftp = connect_ftp(cfg)
    try:
        ftp_mkdirs(ftp, str(cfg.get("ftp_path", "")).strip() or "/SaveBackups")
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def ftp_upload_backups(src_dir: Path, cfg: dict[str, Any]) -> int:
    """Envia backups .zip para o servidor FTP e aplica política de retenção por dias."""
    ftp = connect_ftp(cfg)
    uploaded = 0
    try:
        remote_path = str(cfg.get("ftp_path", "")).strip() or "/SaveBackups"
        ftp_mkdirs(ftp, remote_path)

        try:
            existing = set(ftp.nlst())
        except ftplib.error_perm:
            existing = set()

        for zf in sorted(src_dir.glob("saves_*.zip")):
            if zf.name not in existing:
                with open(zf, "rb") as fp:
                    ftp.storbinary(f"STOR {zf.name}", fp, blocksize=65536)
                uploaded += 1

        keep_days = toint(cfg.get("cloud_keep_days", 0), 0, 0)
        if keep_days > 0:
            cutoff = datetime.now() - timedelta(days=keep_days)
            for name in list(existing):
                base = name.rsplit("/", 1)[-1]
                if base.startswith("saves_") and base.endswith(".zip"):
                    try:
                        dt = datetime.strptime(base[6:25], "%Y-%m-%d_%H-%M-%S")
                        if dt < cutoff:
                            ftp.delete(base)
                    except Exception:
                        pass
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()

    return uploaded

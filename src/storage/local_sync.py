"""
Sincronização com pastas locais de nuvem (OneDrive, GDrive, Dropbox) ou pastas de rede (SMB/NAS).
"""
from __future__ import annotations

from pathlib import Path
import shutil
import time


def sync_to_directory(src_dir: Path, target_dir: Path, keep_days: int) -> int:
    """
    Copia novos arquivos .zip para o diretório de destino e aplica retenção por idade em dias.
    Retorna o número de novos arquivos copiados.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    uploaded = 0

    for zf in sorted(src_dir.glob("saves_*.zip")):
        dest_file = target_dir / zf.name
        if not dest_file.exists() or dest_file.stat().st_size != zf.stat().st_size:
            shutil.copy2(zf, dest_file)
            uploaded += 1

    if keep_days > 0:
        cutoff = time.time() - (keep_days * 86400)
        for old in target_dir.glob("saves_*.zip"):
            try:
                if old.stat().st_mtime < cutoff:
                    old.unlink(missing_ok=True)
            except OSError:
                pass

    return uploaded

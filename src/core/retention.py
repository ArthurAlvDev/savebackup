"""
Módulo de controle de retenção e rotação de backups locais.
"""
from __future__ import annotations

from pathlib import Path


def rotate_local_backups(dest_dir: Path, keep: int) -> int:
    """
    Mantém apenas os últimos `keep` backups no diretório informado.
    Se keep <= 0, nenhum arquivo é apagado (mantém todos).
    Retorna a quantidade de arquivos removidos.
    """
    if keep <= 0 or not dest_dir.exists():
        return 0

    removed = 0
    zips = sorted(dest_dir.glob("saves_*.zip"))
    if len(zips) > keep:
        for old in zips[:-keep]:
            try:
                old.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass

    return removed

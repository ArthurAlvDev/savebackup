"""
Módulo responsável pela compactação atômica dos saves em arquivos .zip.
"""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import time
from typing import Callable
import zipfile

# Arquivos .part mais antigos que isso são restos de uma execução interrompida.
STALE_PART_SECONDS = 3600


def cleanup_stale_parts(dest_dir: Path, max_age_seconds: int = STALE_PART_SECONDS) -> int:
    """
    Remove arquivos `.zip.part` órfãos deixados por backups interrompidos.

    A compactação grava primeiro em `.part` e só renomeia ao final; se o
    processo for encerrado no meio, o arquivo parcial ficaria ocupando espaço
    para sempre. Só remove restos com mais de `max_age_seconds` para nunca
    apagar uma gravação em andamento em outro processo.
    """
    removed = 0
    try:
        candidates = list(dest_dir.glob("saves_*.zip.part"))
    except OSError:
        return 0

    now = time.time()
    for part in candidates:
        try:
            if now - part.stat().st_mtime > max_age_seconds:
                part.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def make_zip(
    folders: list[str],
    primary_dest: Path,
    all_dests: list[Path],
    log_func: Callable[[str], None],
    t_func: Callable[..., str],
) -> Path | None:
    """
    Cria um arquivo ZIP com o conteúdo de todas as pastas de saves selecionadas.

    - Evita auto-inclusão de diretórios de destino que estejam dentro das fontes.
    - Grava primeiro em um arquivo temporário `.part` e renomeia apenas após o término,
      evitando corrupção em caso de encerramento abrupto.
    - Ignora com segurança arquivos travados/em uso pelo jogo sem travar o backup.
    """
    primary_dest.mkdir(parents=True, exist_ok=True)
    stale = cleanup_stale_parts(primary_dest)
    if stale:
        log_func(t_func("log_stale_parts_removed", stale))

    # Conjunto de caminhos canônicos dos destinos para evitar recursão infinita
    excluded_resolved: set[Path] = set()
    for d in all_dests:
        try:
            excluded_resolved.add(d.resolve())
        except Exception:
            pass

    name = f"saves_{datetime.now():%Y-%m-%d_%H-%M-%S}.zip"
    final_path = primary_dest / name
    temp_path = primary_dest / (name + ".part")

    count = 0
    skipped = 0
    used_roots: set[str] = set()

    with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for folder in folders:
            src = Path(folder)
            if not src.is_dir():
                log_func(t_func("log_folder_missing", folder))
                continue

            base = src.name or src.drive.replace(":", "") or "pasta"
            root_name, i = base, 2
            while root_name in used_roots:
                root_name, i = f"{base}_{i}", i + 1
            used_roots.add(root_name)

            for dirpath, dirs, files in os.walk(src):
                # Filtra diretórios excluídos in-place para que walk não desça neles
                dirs[:] = [
                    d
                    for d in dirs
                    if Path(dirpath, d).resolve() not in excluded_resolved
                ]
                for f in files:
                    full = Path(dirpath) / f
                    try:
                        arcname = Path(root_name) / full.relative_to(src)
                        z.write(full, arcname)
                        count += 1
                    except OSError:
                        skipped += 1

    if skipped:
        log_func(t_func("log_skipped_files", skipped))

    if count == 0:
        temp_path.unlink(missing_ok=True)
        log_func(t_func("log_no_files"))
        return None

    temp_path.replace(final_path)
    return final_path

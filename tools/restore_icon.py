"""
Restaura o ícone binário (logo.ico) a partir de assets/logo.ico.b64.

O repositório mantém o ícone em base64 para que o build funcione em qualquer
clone sem depender de anexos binários. Execute antes de compilar:

    python tools/restore_icon.py
"""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "logo.ico.b64"
TARGET = ROOT / "logo.ico"


def main() -> int:
    if TARGET.is_file():
        print(f"logo.ico já existe ({TARGET.stat().st_size} bytes).")
        return 0

    if not SOURCE.is_file():
        print(f"ERRO: {SOURCE} não encontrado.")
        return 1

    data = base64.b64decode(SOURCE.read_text(encoding="ascii").strip())
    TARGET.write_bytes(data)
    print(f"logo.ico restaurado ({len(data)} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

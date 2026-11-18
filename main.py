"""
SaveBackup - ponto de entrada da aplicação.

Uso:
    python main.py               # abre a janela
    python main.py --minimized   # inicia direto na bandeja
    python main.py --version     # mostra a versão e sai
"""
from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk

# Garante que a raiz do projeto esteja no sys.path para imports absolutos
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.constants import APP_TITLE, APP_VERSION, IS_WIN, MUTEX_NAME
from src.platform.single_instance import (
    acquire_single_instance,
    focus_existing_window,
    release_single_instance,
)
from src.ui.app_window import MainWindow


def main() -> None:
    if "--version" in sys.argv or "-V" in sys.argv:
        print(f"SaveBackup {APP_VERSION}")
        return

    mutex = True
    if IS_WIN:
        mutex = acquire_single_instance(MUTEX_NAME)
        if mutex is None:
            # Já existe uma instância aberta: apenas traz a janela para frente.
            focus_existing_window(f"{APP_TITLE} {APP_VERSION}")
            return

    try:
        root = tk.Tk()
        MainWindow(root)
        root.mainloop()
    finally:
        if IS_WIN:
            release_single_instance(mutex)


if __name__ == "__main__":
    main()

"""
Gerenciamento de inicialização automática no Windows.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from src.config.constants import APP_NAME, FROZEN, IS_WIN


def get_startup_bat_path() -> Path | None:
    """Caminho do arquivo de lote no menu Iniciar (Pasta Inicializar)."""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return None
    return Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup" / f"{APP_NAME}.bat"


def build_autostart_command() -> str:
    """Monta a linha de comando para iniciar a aplicação minimizada."""
    if FROZEN:
        return f'"{Path(sys.executable).resolve()}" --minimized'

    exe_path = Path(sys.executable).resolve()
    pyw = exe_path.with_name("pythonw.exe")
    if not pyw.exists():
        pyw = exe_path

    # Localiza o script principal na raiz do projeto
    entry_point = Path(__file__).resolve().parent.parent.parent / "main.py"
    return f'"{pyw}" "{entry_point}" --minimized'


def is_autostart_enabled() -> bool:
    """Verifica se a inicialização automática está habilitada no Registro ou Pasta de Inicialização."""
    if not IS_WIN:
        return False

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            if val:
                return True
    except Exception:
        pass

    bat = get_startup_bat_path()
    return bool(bat and bat.exists())


def set_autostart(enabled: bool) -> bool:
    """Habilita ou desabilita a inicialização automática com o Windows."""
    if not IS_WIN:
        return False

    cmd = build_autostart_command()
    bat = get_startup_bat_path()
    ok = False

    try:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        ok = True
    except Exception:
        pass

    try:
        if bat:
            if enabled and not ok:
                bat.parent.mkdir(parents=True, exist_ok=True)
                bat.write_text(f'@echo off\r\nstart "" {cmd}\r\n', encoding="utf-8")
                ok = True
            elif not enabled and bat.exists():
                bat.unlink(missing_ok=True)
    except Exception:
        pass

    return ok

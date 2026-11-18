"""
Controle de instância única da aplicação (Windows).

Impede que duas cópias do SaveBackup rodem ao mesmo tempo — duas instâncias
agendariam backups concorrentes e poderiam gravar o mesmo arquivo .zip.

Quando uma segunda instância é iniciada, a janela da instância já aberta
(inclusive se estiver minimizada na bandeja) é restaurada e trazida para frente.
"""
from __future__ import annotations

import ctypes
from typing import Any

ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9


def acquire_single_instance(name: str) -> Any | None:
    """
    Cria (ou abre) o mutex nomeado da aplicação.

    Retorna o handle do mutex quando esta é a primeira instância.
    Retorna None quando outra instância já está em execução.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p

    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        # Sem mutex o aplicativo ainda deve abrir; não bloqueia o usuário.
        return True

    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_single_instance(handle: Any | None) -> None:
    """Libera o mutex ao encerrar a aplicação."""
    if not handle or handle is True:
        return
    try:
        ctypes.WinDLL("kernel32").CloseHandle(handle)
    except Exception:
        pass


def focus_existing_window(title: str) -> bool:
    """Restaura e traz para frente a janela existente com o título informado."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False

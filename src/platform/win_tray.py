"""
Ícone nativo da Área de Notificação (System Tray) para Windows 10/11 (64-bit safe).
Utiliza a API pura Win32 via ctypes, garantindo compatibilidade total com Python x64.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
import threading
from typing import Callable

from src.config.constants import FROZEN, IS_WIN, get_icon_path

if IS_WIN:
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(
        LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uTimeoutOrVersion", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
            ("guidItem", GUID),
            ("hBalloonIcon", wintypes.HICON),
        ]

    _user32 = ctypes.windll.user32
    _shell32 = ctypes.windll.shell32
    _kernel32 = ctypes.windll.kernel32

    _shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
    _shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    _shell32.ExtractIconExW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(wintypes.HICON),
        ctypes.POINTER(wintypes.HICON),
        wintypes.UINT,
    ]
    _shell32.ExtractIconExW.restype = wintypes.UINT

    _user32.DefWindowProcW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    _user32.DefWindowProcW.restype = LRESULT
    _user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    _user32.RegisterClassW.restype = wintypes.ATOM
    _user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        wintypes.LPVOID,
    ]
    _user32.CreateWindowExW.restype = wintypes.HWND
    _user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    _user32.LoadImageW.restype = wintypes.HANDLE
    _user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
    _user32.LoadIconW.restype = wintypes.HICON
    _user32.CreatePopupMenu.argtypes = []
    _user32.CreatePopupMenu.restype = wintypes.HMENU
    _user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
    _user32.AppendMenuW.restype = wintypes.BOOL
    _user32.SetMenuDefaultItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    _user32.SetMenuDefaultItem.restype = wintypes.BOOL
    _user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    _user32.GetCursorPos.restype = wintypes.BOOL
    _user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    _user32.SetForegroundWindow.restype = wintypes.BOOL
    _user32.TrackPopupMenu.argtypes = [
        wintypes.HMENU,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.LPVOID,
    ]
    _user32.TrackPopupMenu.restype = wintypes.BOOL
    _user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.PostMessageW.restype = wintypes.BOOL
    _user32.DestroyMenu.argtypes = [wintypes.HMENU]
    _user32.DestroyMenu.restype = wintypes.BOOL
    _user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    ]
    _user32.GetMessageW.restype = wintypes.BOOL
    _user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    _user32.TranslateMessage.restype = wintypes.BOOL
    _user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    _user32.DispatchMessageW.restype = LRESULT
    _user32.PostQuitMessage.argtypes = [ctypes.c_int]
    _user32.PostQuitMessage.restype = None

    _kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    _kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE


class WinTrayIcon:
    """Ícone na bandeja do sistema com menu de contexto e balão de notificação."""

    WM_DESTROY = 0x0002
    WM_USER = 0x0400
    WM_TRAY = WM_USER + 20
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    WM_CONTEXTMENU = 0x007B

    NIM_ADD = 0x00000000
    NIM_MODIFY = 0x00000001
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    NIF_INFO = 0x00000010
    NIIF_INFO = 0x00000001

    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040

    MF_STRING = 0x00000000
    MF_SEPARATOR = 0x00000800
    TPM_RIGHTBUTTON = 0x0002
    TPM_RETURNCMD = 0x0100

    ID_OPEN = 1001
    ID_BACKUP = 1002
    ID_UPLOAD = 1003
    ID_EXIT = 1004

    def __init__(
        self,
        on_open: Callable[[], None],
        on_backup: Callable[[], None],
        on_upload: Callable[[], None],
        on_exit: Callable[[], None],
        t_func: Callable[[str], str],
    ) -> None:
        self.on_open = on_open
        self.on_backup = on_backup
        self.on_upload = on_upload
        self.on_exit = on_exit
        self.t = t_func

        self.hwnd = None
        self._ready = threading.Event()
        self._balloon_shown = False
        self._wnd_proc_ref = None

        if IS_WIN:
            threading.Thread(target=self._loop, daemon=True).start()
            self._ready.wait(timeout=2.0)

    def _load_icon(self):
        # 1. Tenta carregar o logo.ico
        ico_path = get_icon_path()
        if ico_path:
            hicon = _user32.LoadImageW(
                None,
                ico_path,
                self.IMAGE_ICON,
                0,
                0,
                self.LR_LOADFROMFILE | self.LR_DEFAULTSIZE,
            )
            if hicon:
                return hicon

        # 2. Se for executável compilado, extrai dele próprio
        if FROZEN:
            hicon_exe = wintypes.HICON()
            if (
                _shell32.ExtractIconExW(
                    sys.executable, 0, None, ctypes.byref(hicon_exe), 1
                )
                > 0
                and hicon_exe.value
            ):
                return hicon_exe.value

        # 3. Fallback: ícone padrão do Windows
        hicon_def = wintypes.HICON()
        if (
            _shell32.ExtractIconExW("shell32.dll", 43, None, ctypes.byref(hicon_def), 1)
            > 0
            and hicon_def.value
        ):
            return hicon_def.value

        return _user32.LoadIconW(None, ctypes.cast(32512, wintypes.LPCWSTR))

    def _loop(self) -> None:
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == self.WM_TRAY:
                ev = lparam & 0xFFFF
                if ev in (self.WM_LBUTTONDBLCLK, self.WM_LBUTTONUP):
                    self.on_open()
                elif ev in (self.WM_RBUTTONUP, self.WM_CONTEXTMENU):
                    self._show_context_menu(hwnd)
                return 0
            elif msg == self.WM_DESTROY:
                _user32.PostQuitMessage(0)
                return 0
            return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wnd_proc_ref = WNDPROC(wnd_proc)
        hinst = _kernel32.GetModuleHandleW(None)
        class_name = f"SaveBackupTray_{os.getpid()}"

        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wnd_proc_ref
        wc.hInstance = hinst
        wc.lpszClassName = class_name
        _user32.RegisterClassW(ctypes.byref(wc))

        self.hwnd = _user32.CreateWindowExW(
            0,
            class_name,
            "SaveBackupTrayWindow",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            hinst,
            None,
        )

        self.hicon = self._load_icon()
        self.nid = NOTIFYICONDATAW()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        self.nid.uCallbackMessage = self.WM_TRAY
        self.nid.hIcon = self.hicon
        self.nid.szTip = "SaveBackup"
        _shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(self.nid))
        self._ready.set()

        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

    def _show_context_menu(self, hwnd) -> None:
        menu = _user32.CreatePopupMenu()

        _user32.AppendMenuW(menu, self.MF_STRING, self.ID_OPEN, self.t("tray_open"))
        _user32.AppendMenuW(menu, self.MF_SEPARATOR, 0, None)
        _user32.AppendMenuW(menu, self.MF_STRING, self.ID_BACKUP, self.t("tray_backup"))
        _user32.AppendMenuW(menu, self.MF_STRING, self.ID_UPLOAD, self.t("tray_upload"))
        _user32.AppendMenuW(menu, self.MF_SEPARATOR, 0, None)
        _user32.AppendMenuW(menu, self.MF_STRING, self.ID_EXIT, self.t("tray_exit"))

        _user32.SetMenuDefaultItem(menu, self.ID_OPEN, 0)

        pt = wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        _user32.SetForegroundWindow(hwnd)
        cmd = _user32.TrackPopupMenu(
            menu,
            self.TPM_RIGHTBUTTON | self.TPM_RETURNCMD,
            pt.x,
            pt.y,
            0,
            hwnd,
            None,
        )
        _user32.PostMessageW(hwnd, 0, 0, 0)
        _user32.DestroyMenu(menu)

        if cmd == self.ID_OPEN:
            self.on_open()
        elif cmd == self.ID_BACKUP:
            self.on_backup()
        elif cmd == self.ID_UPLOAD:
            self.on_upload()
        elif cmd == self.ID_EXIT:
            self.on_exit()

    def show_balloon(self, title: str, message: str) -> None:
        """Exibe balão de notificação (apenas uma vez para evitar incomodar o usuário)."""
        if not IS_WIN or not self.hwnd or self._balloon_shown:
            return
        self._balloon_shown = True
        try:
            self.nid.uFlags = (
                self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP | self.NIF_INFO
            )
            self.nid.szInfoTitle = title[:63]
            self.nid.szInfo = message[:255]
            self.nid.dwInfoFlags = self.NIIF_INFO
            _shell32.Shell_NotifyIconW(self.NIM_MODIFY, ctypes.byref(self.nid))
        except Exception:
            pass

    def stop(self) -> None:
        """Remove o ícone da bandeja e finaliza o loop de mensagens."""
        if not IS_WIN or not self.hwnd:
            return
        try:
            _shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(self.nid))
            _user32.PostMessageW(self.hwnd, self.WM_DESTROY, 0, 0)
            self.hwnd = None
        except Exception:
            pass

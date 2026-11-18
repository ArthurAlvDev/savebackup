"""
Componente Seção 4: Ações manuais e inicialização com o Windows.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from src.i18n.manager import I18nManager


class ActionsComponent(ttk.Frame):
    """Botoes de acionamento imediato e chave de inicializacao com o sistema."""

    def __init__(
        self,
        parent: tk.Misc,
        i18n: I18nManager,
        autostart_enabled: bool,
        on_backup_now: Callable[[], None],
        on_upload_now: Callable[[], None],
        on_open_all: Callable[[], None],
        on_autostart_toggle: Callable[[bool], None],
    ) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.on_backup_now = on_backup_now
        self.on_upload_now = on_upload_now
        self.on_open_all = on_open_all
        self.on_autostart_toggle = on_autostart_toggle

        self.btn_backup_now = ttk.Button(
            self, text=self.i18n.t("btn_backup_now"), command=self.on_backup_now
        )
        self.btn_backup_now.pack(side="left")

        self.btn_upload_now = ttk.Button(
            self, text=self.i18n.t("btn_upload_now"), command=self.on_upload_now
        )
        self.btn_upload_now.pack(side="left", padx=8)

        self.btn_open_all = ttk.Button(
            self, text=self.i18n.t("btn_open_backups"), command=self.on_open_all
        )
        self.btn_open_all.pack(side="left")

        self.v_auto = tk.BooleanVar(value=autostart_enabled)
        self.chk_autostart = ttk.Checkbutton(
            self,
            text=self.i18n.t("chk_autostart"),
            variable=self.v_auto,
            command=self._on_check_toggle,
        )
        self.chk_autostart.pack(side="right")

    def _on_check_toggle(self) -> None:
        self.on_autostart_toggle(self.v_auto.get())

    def set_autostart_state(self, enabled: bool) -> None:
        self.v_auto.set(enabled)

    def update_texts(self) -> None:
        t = self.i18n.t
        self.btn_backup_now.configure(text=t("btn_backup_now"))
        self.btn_upload_now.configure(text=t("btn_upload_now"))
        self.btn_open_all.configure(text=t("btn_open_backups"))
        self.chk_autostart.configure(text=t("chk_autostart"))

"""
Componente do cabeçalho superior: seletor de idiomas e opção de bandeja.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from src.i18n.manager import I18nManager


class HeaderComponent(ttk.Frame):
    """Barra superior com controle de idioma e opção de minimizar para a bandeja."""

    def __init__(
        self,
        parent: tk.Misc,
        i18n: I18nManager,
        close_to_tray: bool,
        on_lang_changed: Callable[[str], None],
        on_tray_toggle: Callable[[bool], None],
    ) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.on_lang_changed = on_lang_changed
        self.on_tray_toggle = on_tray_toggle

        self.lbl_lang = ttk.Label(self, text=self.i18n.t("lang_label"))
        self.lbl_lang.pack(side="left")

        # Configuração da lista de idiomas com exibição amigável
        self.lang_map = self.i18n.get_languages()
        self.lang_codes = list(self.lang_map.keys())
        display_values = [
            f"{code.upper()} - {name}" for code, name in self.lang_map.items()
        ]

        current_idx = (
            self.lang_codes.index(self.i18n.current_language)
            if self.i18n.current_language in self.lang_codes
            else 0
        )

        self.cb_lang = ttk.Combobox(
            self, values=display_values, state="readonly", width=18
        )
        self.cb_lang.current(current_idx)
        self.cb_lang.pack(side="left", padx=6)
        self.cb_lang.bind("<<ComboboxSelected>>", self._on_combobox_selected)

        self.v_close_tray = tk.BooleanVar(value=close_to_tray)
        self.chk_close_tray = ttk.Checkbutton(
            self,
            text=self.i18n.t("close_to_tray"),
            variable=self.v_close_tray,
            command=self._on_tray_check_clicked,
        )
        self.chk_close_tray.pack(side="right")

    def _on_combobox_selected(self, _event=None) -> None:
        idx = self.cb_lang.current()
        if 0 <= idx < len(self.lang_codes):
            selected_code = self.lang_codes[idx]
            self.on_lang_changed(selected_code)

    def _on_tray_check_clicked(self) -> None:
        self.on_tray_toggle(self.v_close_tray.get())

    def update_texts(self) -> None:
        """Atualiza rótulos ao trocar de idioma."""
        self.lbl_lang.configure(text=self.i18n.t("lang_label"))
        self.chk_close_tray.configure(text=self.i18n.t("close_to_tray"))

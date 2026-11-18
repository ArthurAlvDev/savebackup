"""
Componente Seção 1: Pastas de Origem dos saves de jogos.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable

from src.i18n.manager import I18nManager


class SourcesComponent(ttk.LabelFrame):
    """Gerencia a lista de pastas de jogos que serão incluídas no backup."""

    def __init__(
        self,
        parent: tk.Misc,
        i18n: I18nManager,
        folders: list[str],
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(parent, text=i18n.t("sec_sources"))
        self.i18n = i18n
        self.on_change = on_change

        self.columnconfigure(0, weight=1)

        self.lb = tk.Listbox(self, height=5, selectmode="extended")
        self.lb.grid(row=0, column=0, rowspan=2, sticky="ew", padx=(8, 0), pady=6)
        for folder in folders:
            self.lb.insert("end", folder)

        sb = ttk.Scrollbar(self, command=self.lb.yview)
        sb.grid(row=0, column=1, rowspan=2, sticky="ns", pady=6)
        self.lb.config(yscrollcommand=sb.set)

        self.btn_add = ttk.Button(
            self, text=self.i18n.t("btn_add_folder"), command=self.add_folder
        )
        self.btn_add.grid(row=0, column=2, padx=8, pady=(6, 2), sticky="new")

        self.btn_remove = ttk.Button(
            self, text=self.i18n.t("btn_remove"), command=self.remove_folder
        )
        self.btn_remove.grid(row=1, column=2, padx=8, pady=(2, 6), sticky="new")

    def get_folders(self) -> list[str]:
        return list(self.lb.get(0, "end"))

    def add_folder(self) -> None:
        path = filedialog.askdirectory(
            mustexist=True, title=self.i18n.t("dlg_pick_source")
        )
        if path:
            norm = os.path.normpath(path)
            if norm not in self.get_folders():
                self.lb.insert("end", norm)
                self.on_change()

    def remove_folder(self) -> None:
        for idx in reversed(self.lb.curselection()):
            self.lb.delete(idx)
        self.on_change()

    def update_texts(self) -> None:
        self.configure(text=self.i18n.t("sec_sources"))
        self.btn_add.configure(text=self.i18n.t("btn_add_folder"))
        self.btn_remove.configure(text=self.i18n.t("btn_remove"))

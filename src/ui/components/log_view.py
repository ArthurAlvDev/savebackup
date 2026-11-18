"""
Componente Seção 5: Registro de Atividades (Log).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.i18n.manager import I18nManager


class LogComponent(ttk.LabelFrame):
    """Painel de visualização de logs em tempo real com barra de rolagem."""

    def __init__(self, parent: tk.Misc, i18n: I18nManager) -> None:
        super().__init__(parent, text=i18n.t("sec_log"))
        self.i18n = i18n

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.txt = tk.Text(self, height=7, state="disabled", wrap="word")
        self.txt.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=6)

        sb = ttk.Scrollbar(self, command=self.txt.yview)
        sb.grid(row=0, column=1, sticky="ns", pady=6)
        self.txt.config(yscrollcommand=sb.set)

    def append_message(self, message: str) -> None:
        """Adiciona uma nova linha ao log mantendo o campo somente leitura."""
        self.txt.config(state="normal")
        self.txt.insert("end", message + "\n")
        self.txt.see("end")
        self.txt.config(state="disabled")

    def update_texts(self) -> None:
        self.configure(text=self.i18n.t("sec_log"))

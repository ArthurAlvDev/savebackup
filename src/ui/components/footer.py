"""
Rodapé da janela principal: assinatura da OlacDev, versão e licença.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import webbrowser

from src.config.constants import APP_AUTHOR, APP_URL, APP_VERSION

LINK_COLOR = "#0B5CAD"


class FooterComponent(ttk.Frame):
    """Faixa inferior com crédito clicável, versão e licença."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)

        credit = ttk.Label(
            self,
            text=f"Made by {APP_AUTHOR}",
            foreground=LINK_COLOR,
            cursor="hand2",
        )
        credit.pack(side="left")
        credit.bind("<Button-1>", lambda _e: self._open_site())

        site = ttk.Label(
            self,
            text=APP_URL,
            foreground=LINK_COLOR,
            cursor="hand2",
        )
        site.pack(side="left", padx=(6, 0))
        site.bind("<Button-1>", lambda _e: self._open_site())

        ttk.Label(self, text=f"·  v{APP_VERSION}").pack(side="left", padx=(8, 0))
        ttk.Label(self, text="MIT License  ·  github.com/ArthurAlvDev/savebackup").pack(
            side="right"
        )

    def _open_site(self) -> None:
        try:
            webbrowser.open(APP_URL)
        except Exception:
            pass

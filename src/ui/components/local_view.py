"""
Componente Seção 2: Destinos de Backup Local (.zip em múltiplos discos/pastas).
"""
from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable

from src.config.constants import DEFAULT_DEST, toint
from src.i18n.manager import I18nManager


class LocalBackupComponent(ttk.LabelFrame):
    """Gerencia múltiplos destinos locais, temporizador e limites de retenção."""

    def __init__(
        self,
        parent: tk.Misc,
        i18n: I18nManager,
        destinations: list[str],
        enabled: bool,
        interval_minutes: int,
        keep_count: int,
        on_change: Callable[[], None],
        log_func: Callable[[str], None],
    ) -> None:
        super().__init__(parent, text=i18n.t("sec_local"))
        self.i18n = i18n
        self.on_change = on_change
        self.log_func = log_func

        self.columnconfigure(0, weight=1)

        self.lb_dest = tk.Listbox(self, height=3, selectmode="extended")
        self.lb_dest.grid(row=0, column=0, rowspan=3, sticky="ew", padx=(8, 0), pady=6)
        for d in destinations:
            self.lb_dest.insert("end", d)

        sb = ttk.Scrollbar(self, command=self.lb_dest.yview)
        sb.grid(row=0, column=1, rowspan=3, sticky="ns", pady=6)
        self.lb_dest.config(yscrollcommand=sb.set)

        self.btn_add = ttk.Button(
            self, text=self.i18n.t("btn_add_dest"), command=self.add_dest
        )
        self.btn_add.grid(row=0, column=2, padx=8, pady=(6, 2), sticky="new")

        self.btn_remove = ttk.Button(
            self, text=self.i18n.t("btn_remove_dest"), command=self.remove_dest
        )
        self.btn_remove.grid(row=1, column=2, padx=8, pady=2, sticky="new")

        self.btn_open = ttk.Button(
            self, text=self.i18n.t("btn_open_dest"), command=self.open_dest
        )
        self.btn_open.grid(row=2, column=2, padx=8, pady=(2, 6), sticky="new")

        # Linha inferior de agendamento e retenção
        row_cfg = ttk.Frame(self)
        row_cfg.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

        self.v_enabled = tk.BooleanVar(value=enabled)
        self.chk_auto = ttk.Checkbutton(
            row_cfg,
            text=self.i18n.t("auto_every"),
            variable=self.v_enabled,
            command=self.on_change,
        )
        self.chk_auto.pack(side="left")

        self.v_minutes = tk.StringVar(value=str(interval_minutes))
        self.sp_min = ttk.Spinbox(
            row_cfg,
            from_=1,
            to=100000,
            width=6,
            textvariable=self.v_minutes,
            command=self.on_change,
        )
        self.sp_min.pack(side="left", padx=4)
        self.sp_min.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_keep1 = ttk.Label(row_cfg, text=self.i18n.t("min_keep_last"))
        self.lbl_keep1.pack(side="left")

        self.v_keep = tk.StringVar(value=str(keep_count))
        self.sp_keep = ttk.Spinbox(
            row_cfg,
            from_=0,
            to=1000,
            width=5,
            textvariable=self.v_keep,
            command=self.on_change,
        )
        self.sp_keep.pack(side="left", padx=4)
        self.sp_keep.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_keep2 = ttk.Label(row_cfg, text=self.i18n.t("backups_zero_all"))
        self.lbl_keep2.pack(side="left")

    def get_destinations(self) -> list[str]:
        items = list(self.lb_dest.get(0, "end"))
        return items if items else [DEFAULT_DEST]

    def is_enabled(self) -> bool:
        return self.v_enabled.get()

    def get_minutes(self) -> int:
        return toint(self.v_minutes.get(), 30, 1)

    def get_keep(self) -> int:
        return toint(self.v_keep.get(), 10, 0)

    def add_dest(self) -> None:
        path = filedialog.askdirectory(title=self.i18n.t("dlg_pick_dest"))
        if path:
            norm = os.path.normpath(path)
            if norm not in self.lb_dest.get(0, "end"):
                self.lb_dest.insert("end", norm)
                self.on_change()

    def remove_dest(self) -> None:
        for idx in reversed(self.lb_dest.curselection()):
            if self.lb_dest.size() > 1:
                self.lb_dest.delete(idx)
        self.on_change()

    def open_dest(self) -> None:
        self.on_change()
        sel = self.lb_dest.curselection()
        targets = (
            [self.lb_dest.get(i) for i in sel]
            if sel
            else self.get_destinations()
        )
        for d_str in targets:
            try:
                d = Path(d_str)
                d.mkdir(parents=True, exist_ok=True)
                os.startfile(d)
            except Exception as e:
                self.log_func(f"ERRO: {e}")

    def update_texts(self) -> None:
        self.configure(text=self.i18n.t("sec_local"))
        self.btn_add.configure(text=self.i18n.t("btn_add_dest"))
        self.btn_remove.configure(text=self.i18n.t("btn_remove_dest"))
        self.btn_open.configure(text=self.i18n.t("btn_open_dest"))
        self.chk_auto.configure(text=self.i18n.t("auto_every"))
        self.lbl_keep1.configure(text=self.i18n.t("min_keep_last"))
        self.lbl_keep2.configure(text=self.i18n.t("backups_zero_all"))

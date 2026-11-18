"""
Componente Seção 3: Nuvem e Backup Externo (Rclone, Cloud Local, FTP/FTPS, WebDAV, SMB).
"""
from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from src.config.constants import toint
from src.i18n.manager import I18nManager
from src.storage.detector import detect_installed_clouds
from src.storage.rclone_client import (
    download_rclone_binary,
    find_rclone,
    list_rclone_remotes,
    open_rclone_terminal_config,
)


class CloudBackupComponent(ttk.LabelFrame):
    """Gerencia configuração, painéis específicos de provedores e rotina de upload remoto."""

    PROVIDER_KEYS = ["rclone", "local_cloud", "ftp", "webdav", "network"]

    def __init__(
        self,
        parent: tk.Misc,
        i18n: I18nManager,
        cfg: dict[str, Any],
        on_change: Callable[[], None],
        on_test: Callable[[], None],
        log_func: Callable[[str], None],
        run_async: Callable[[Callable[[], None]], None],
    ) -> None:
        super().__init__(parent, text=i18n.t("sec_cloud"))
        self.i18n = i18n
        self.cfg = cfg
        self.on_change = on_change
        self.on_test = on_test
        self.log_func = log_func
        self.run_async = run_async

        self.detected_clouds = detect_installed_clouds()
        self.frames_prov: dict[str, ttk.Frame] = {}

        self.columnconfigure(1, weight=1)

        # Barra do Provedor (Combobox + Botão Testar)
        prov_row = ttk.Frame(self)
        prov_row.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 4))
        prov_row.columnconfigure(1, weight=1)

        self.lbl_provider = ttk.Label(prov_row, text=self.i18n.t("provider_label"))
        self.lbl_provider.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.cb_provider = ttk.Combobox(prov_row, state="readonly")
        self.cb_provider.grid(row=0, column=1, sticky="ew")
        self.cb_provider.bind("<<ComboboxSelected>>", self._on_provider_combobox_changed)

        self.btn_test_cloud = ttk.Button(
            prov_row, text=self.i18n.t("btn_test_cloud"), command=self.on_test
        )
        self.btn_test_cloud.grid(row=0, column=2, padx=(8, 0))

        # Container dos painéis dinâmicos de cada provedor
        self.prov_container = ttk.Frame(self)
        self.prov_container.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=2)
        self.prov_container.columnconfigure(0, weight=1)

        self._build_provider_subframes()

        # Linha inferior de agendamento e retenção
        row_cld = ttk.Frame(self)
        row_cld.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 8))

        self.v_cloud_en = tk.BooleanVar(value=cfg.get("cloud_enabled", False))
        self.chk_cloud_en = ttk.Checkbutton(
            row_cld,
            text=self.i18n.t("cloud_auto_every"),
            variable=self.v_cloud_en,
            command=self.on_change,
        )
        self.chk_cloud_en.pack(side="left")

        self.v_cloud_min = tk.StringVar(value=str(cfg.get("cloud_minutes", 120)))
        self.sp_cmin = ttk.Spinbox(
            row_cld,
            from_=1,
            to=100000,
            width=6,
            textvariable=self.v_cloud_min,
            command=self.on_change,
        )
        self.sp_cmin.pack(side="left", padx=4)
        self.sp_cmin.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_cdays1 = ttk.Label(row_cld, text=self.i18n.t("min_del_after"))
        self.lbl_cdays1.pack(side="left")

        self.v_cdays = tk.StringVar(value=str(cfg.get("cloud_keep_days", 0)))
        self.sp_cdays = ttk.Spinbox(
            row_cld,
            from_=0,
            to=3650,
            width=5,
            textvariable=self.v_cdays,
            command=self.on_change,
        )
        self.sp_cdays.pack(side="left", padx=4)
        self.sp_cdays.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_cdays2 = ttk.Label(row_cld, text=self.i18n.t("days_zero_never"))
        self.lbl_cdays2.pack(side="left")

        self.update_provider_combobox_list()
        self.show_active_provider_frame()

    def _build_provider_subframes(self) -> None:
        c = self.cfg

        # 1. Rclone
        fr_rc = ttk.Frame(self.prov_container)
        fr_rc.columnconfigure(1, weight=1)
        self.lbl_rc_rem = ttk.Label(fr_rc, text=self.i18n.t("remote_label"))
        self.lbl_rc_rem.grid(row=0, column=0, sticky="w", pady=3, padx=(0, 6))
        self.v_remote = tk.StringVar(value=c.get("cloud_remote", ""))
        self.cb_remote = ttk.Combobox(fr_rc, textvariable=self.v_remote, values=[])
        self.cb_remote.grid(row=0, column=1, sticky="ew", pady=3)
        self.cb_remote.bind("<<ComboboxSelected>>", lambda _: self.on_change())
        self.cb_remote.bind("<FocusOut>", lambda _: self.on_change())

        self.btn_rc_ref = ttk.Button(
            fr_rc, text=self.i18n.t("btn_refresh"), command=lambda: self.refresh_remotes(False)
        )
        self.btn_rc_ref.grid(row=0, column=2, padx=(6, 0))

        self.lbl_rc_path = ttk.Label(fr_rc, text=self.i18n.t("cloud_folder"))
        self.lbl_rc_path.grid(row=1, column=0, sticky="w", pady=3, padx=(0, 6))
        self.v_cpath = tk.StringVar(value=c.get("cloud_path", "SaveBackups"))
        en_cpath = ttk.Entry(fr_rc, textvariable=self.v_cpath)
        en_cpath.grid(row=1, column=1, sticky="ew", pady=3)
        en_cpath.bind("<FocusOut>", lambda _: self.on_change())

        btns_rc = ttk.Frame(fr_rc)
        btns_rc.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 2))
        self.btn_dl_rc = ttk.Button(
            btns_rc, text=self.i18n.t("btn_dl_rclone"), command=self.download_rclone
        )
        self.btn_dl_rc.pack(side="left", padx=(0, 6))
        self.btn_cfg_rc = ttk.Button(
            btns_rc, text=self.i18n.t("btn_cfg_rclone"), command=self.config_rclone
        )
        self.btn_cfg_rc.pack(side="left", padx=6)
        self.frames_prov["rclone"] = fr_rc

        # 2. Nuvem Local Nativa
        fr_lc = ttk.Frame(self.prov_container)
        fr_lc.columnconfigure(1, weight=1)
        self.lbl_lc_det = ttk.Label(fr_lc, text=self.i18n.t("local_cloud_detected"))
        self.lbl_lc_det.grid(row=0, column=0, sticky="w", pady=3, padx=(0, 6))
        cloud_items = [f"{k} -> {v}" for k, v in self.detected_clouds.items()]
        self.cb_detected_clouds = ttk.Combobox(fr_lc, values=cloud_items, state="readonly")
        self.cb_detected_clouds.grid(row=0, column=1, columnspan=2, sticky="ew", pady=3)
        self.cb_detected_clouds.bind("<<ComboboxSelected>>", self._on_select_detected_cloud)

        self.lbl_lc_target = ttk.Label(fr_lc, text=self.i18n.t("local_cloud_target"))
        self.lbl_lc_target.grid(row=1, column=0, sticky="w", pady=3, padx=(0, 6))
        default_lc = c.get("native_cloud_dir", "")
        if not default_lc and self.detected_clouds:
            first_base = next(iter(self.detected_clouds.values()))
            default_lc = str(Path(first_base) / "SaveBackups")
        self.v_native_cloud_dir = tk.StringVar(value=default_lc)
        en_lc = ttk.Entry(fr_lc, textvariable=self.v_native_cloud_dir)
        en_lc.grid(row=1, column=1, sticky="ew", pady=3)
        en_lc.bind("<FocusOut>", lambda _: self.on_change())

        self.btn_lc_browse = ttk.Button(
            fr_lc, text=self.i18n.t("btn_browse"), command=self.pick_native_cloud_dir
        )
        self.btn_lc_browse.grid(row=1, column=2, padx=(6, 0))
        self.frames_prov["local_cloud"] = fr_lc

        # 3. FTP / FTPS Nativo
        fr_ftp = ttk.Frame(self.prov_container)
        fr_ftp.columnconfigure(1, weight=1)
        fr_ftp.columnconfigure(3, weight=1)
        self.lbl_ftp_host = ttk.Label(fr_ftp, text=self.i18n.t("ftp_host"))
        self.lbl_ftp_host.grid(row=0, column=0, sticky="w", pady=2, padx=(0, 6))
        self.v_ftp_host = tk.StringVar(value=c.get("ftp_host", ""))
        en_fhost = ttk.Entry(fr_ftp, textvariable=self.v_ftp_host)
        en_fhost.grid(row=0, column=1, sticky="ew", pady=2)
        en_fhost.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_ftp_port = ttk.Label(fr_ftp, text=self.i18n.t("ftp_port"))
        self.lbl_ftp_port.grid(row=0, column=2, sticky="w", pady=2, padx=(10, 6))
        self.v_ftp_port = tk.StringVar(value=str(c.get("ftp_port", 21)))
        sp_fport = ttk.Spinbox(fr_ftp, from_=1, to=65535, width=7, textvariable=self.v_ftp_port)
        sp_fport.grid(row=0, column=3, sticky="w", pady=2)
        sp_fport.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_ftp_user = ttk.Label(fr_ftp, text=self.i18n.t("ftp_user"))
        self.lbl_ftp_user.grid(row=1, column=0, sticky="w", pady=2, padx=(0, 6))
        self.v_ftp_user = tk.StringVar(value=c.get("ftp_user", ""))
        en_fuser = ttk.Entry(fr_ftp, textvariable=self.v_ftp_user)
        en_fuser.grid(row=1, column=1, sticky="ew", pady=2)
        en_fuser.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_ftp_pass = ttk.Label(fr_ftp, text=self.i18n.t("ftp_pass"))
        self.lbl_ftp_pass.grid(row=1, column=2, sticky="w", pady=2, padx=(10, 6))
        self.v_ftp_pass = tk.StringVar(value=c.get("ftp_pass", ""))
        en_fpass = ttk.Entry(fr_ftp, textvariable=self.v_ftp_pass, show="*")
        en_fpass.grid(row=1, column=3, sticky="ew", pady=2)
        en_fpass.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_ftp_path = ttk.Label(fr_ftp, text=self.i18n.t("ftp_path"))
        self.lbl_ftp_path.grid(row=2, column=0, sticky="w", pady=2, padx=(0, 6))
        self.v_ftp_path = tk.StringVar(value=c.get("ftp_path", "/SaveBackups"))
        en_fpath = ttk.Entry(fr_ftp, textvariable=self.v_ftp_path)
        en_fpath.grid(row=2, column=1, sticky="ew", pady=2)
        en_fpath.bind("<FocusOut>", lambda _: self.on_change())

        self.v_ftp_tls = tk.BooleanVar(value=c.get("ftp_tls", False))
        self.chk_ftp_tls = ttk.Checkbutton(
            fr_ftp, text=self.i18n.t("ftp_tls"), variable=self.v_ftp_tls, command=self.on_change
        )
        self.chk_ftp_tls.grid(row=2, column=2, columnspan=2, sticky="w", padx=(10, 0), pady=2)
        self.frames_prov["ftp"] = fr_ftp

        # 4. WebDAV Nativo
        fr_dav = ttk.Frame(self.prov_container)
        fr_dav.columnconfigure(1, weight=1)
        fr_dav.columnconfigure(3, weight=1)
        self.lbl_dav_url = ttk.Label(fr_dav, text=self.i18n.t("webdav_url"))
        self.lbl_dav_url.grid(row=0, column=0, sticky="w", pady=2, padx=(0, 6))
        self.v_dav_url = tk.StringVar(value=c.get("webdav_url", ""))
        en_durl = ttk.Entry(fr_dav, textvariable=self.v_dav_url)
        en_durl.grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)
        en_durl.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_dav_user = ttk.Label(fr_dav, text=self.i18n.t("ftp_user"))
        self.lbl_dav_user.grid(row=1, column=0, sticky="w", pady=2, padx=(0, 6))
        self.v_dav_user = tk.StringVar(value=c.get("webdav_user", ""))
        en_duser = ttk.Entry(fr_dav, textvariable=self.v_dav_user)
        en_duser.grid(row=1, column=1, sticky="ew", pady=2)
        en_duser.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_dav_pass = ttk.Label(fr_dav, text=self.i18n.t("ftp_pass"))
        self.lbl_dav_pass.grid(row=1, column=2, sticky="w", pady=2, padx=(10, 6))
        self.v_dav_pass = tk.StringVar(value=c.get("webdav_pass", ""))
        en_dpass = ttk.Entry(fr_dav, textvariable=self.v_dav_pass, show="*")
        en_dpass.grid(row=1, column=3, sticky="ew", pady=2)
        en_dpass.bind("<FocusOut>", lambda _: self.on_change())

        self.lbl_dav_path = ttk.Label(fr_dav, text=self.i18n.t("webdav_path"))
        self.lbl_dav_path.grid(row=2, column=0, sticky="w", pady=2, padx=(0, 6))
        self.v_dav_path = tk.StringVar(value=c.get("webdav_path", "SaveBackups"))
        en_dpath = ttk.Entry(fr_dav, textvariable=self.v_dav_path)
        en_dpath.grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)
        en_dpath.bind("<FocusOut>", lambda _: self.on_change())
        self.frames_prov["webdav"] = fr_dav

        # 5. Rede / SMB Nativo
        fr_net = ttk.Frame(self.prov_container)
        fr_net.columnconfigure(1, weight=1)
        self.lbl_net_path = ttk.Label(fr_net, text=self.i18n.t("net_path_label"))
        self.lbl_net_path.grid(row=0, column=0, sticky="w", pady=6, padx=(0, 6))
        self.v_net_path = tk.StringVar(value=c.get("net_path", ""))
        en_npath = ttk.Entry(fr_net, textvariable=self.v_net_path)
        en_npath.grid(row=0, column=1, sticky="ew", pady=6)
        en_npath.bind("<FocusOut>", lambda _: self.on_change())

        self.btn_net_browse = ttk.Button(
            fr_net, text=self.i18n.t("btn_browse"), command=self.pick_net_dir
        )
        self.btn_net_browse.grid(row=0, column=2, padx=(6, 0))
        self.frames_prov["network"] = fr_net

    def update_provider_combobox_list(self) -> None:
        labels = [
            self.i18n.t("prov_rclone"),
            self.i18n.t("prov_local_cloud"),
            self.i18n.t("prov_ftp"),
            self.i18n.t("prov_webdav"),
            self.i18n.t("prov_network"),
        ]
        cur_prov = self.cfg.get("cloud_provider", "rclone")
        idx = (
            self.PROVIDER_KEYS.index(cur_prov)
            if cur_prov in self.PROVIDER_KEYS
            else 0
        )
        self.cb_provider.configure(values=labels)
        self.cb_provider.current(idx)

    def show_active_provider_frame(self) -> None:
        cur_prov = self.cfg.get("cloud_provider", "rclone")
        for key, frame in self.frames_prov.items():
            if key == cur_prov:
                frame.grid(row=0, column=0, sticky="ew")
            else:
                frame.grid_remove()

    def _on_provider_combobox_changed(self, _event=None) -> None:
        idx = self.cb_provider.current()
        if 0 <= idx < len(self.PROVIDER_KEYS):
            self.cfg["cloud_provider"] = self.PROVIDER_KEYS[idx]
            self.show_active_provider_frame()
            self.on_change()

    def _on_select_detected_cloud(self, _event=None) -> None:
        val = self.cb_detected_clouds.get()
        if " -> " in val:
            base = val.split(" -> ", 1)[1].strip()
            self.v_native_cloud_dir.set(str(Path(base) / "SaveBackups"))
            self.on_change()

    def pick_native_cloud_dir(self) -> None:
        p = filedialog.askdirectory(title=self.i18n.t("dlg_pick_dest"))
        if p:
            self.v_native_cloud_dir.set(os.path.normpath(p))
            self.on_change()

    def pick_net_dir(self) -> None:
        p = filedialog.askdirectory(title=self.i18n.t("dlg_pick_dest"))
        if p:
            self.v_net_path.set(os.path.normpath(p))
            self.on_change()

    def download_rclone(self) -> None:
        self.run_async(
            lambda: download_rclone_binary(
                self.log_func, self.i18n.t, on_success=lambda: self.refresh_remotes(True)
            )
        )

    def config_rclone(self) -> None:
        exe = find_rclone()
        if not exe:
            messagebox.showinfo("rclone", self.i18n.t("log_rclone_missing"))
            return
        messagebox.showinfo("rclone", self.i18n.t("dlg_rclone_info"))
        open_rclone_terminal_config()

    def refresh_remotes(self, silent: bool = False) -> None:
        def work():
            if not find_rclone():
                if not silent:
                    self.log_func(self.i18n.t("log_rclone_missing"))
                return
            try:
                names = list_rclone_remotes()
                self.cb_remote.configure(values=names)
                if not silent:
                    found_str = ", ".join(names) if names else self.i18n.t("log_none")
                    self.log_func(self.i18n.t("log_remotes_found", found_str))
            except Exception as e:
                self.log_func(f"ERRO: {e}")

        self.run_async(work)

    def collect_to_dict(self, target: dict[str, Any]) -> None:
        """Coleta todos os dados preenchidos no formulário para o dicionário de configurações."""
        target["cloud_enabled"] = self.v_cloud_en.get()
        target["cloud_minutes"] = toint(self.v_cloud_min.get(), 120, 1)
        target["cloud_keep_days"] = toint(self.v_cdays.get(), 0, 0)
        target["cloud_remote"] = self.v_remote.get().strip().rstrip(":")
        target["cloud_path"] = self.v_cpath.get().strip().strip("/")
        target["native_cloud_dir"] = self.v_native_cloud_dir.get().strip()
        target["ftp_host"] = self.v_ftp_host.get().strip()
        target["ftp_port"] = toint(self.v_ftp_port.get(), 21, 1)
        target["ftp_user"] = self.v_ftp_user.get().strip()
        target["ftp_pass"] = self.v_ftp_pass.get()
        target["ftp_path"] = self.v_ftp_path.get().strip() or "/SaveBackups"
        target["ftp_tls"] = self.v_ftp_tls.get()
        target["webdav_url"] = self.v_dav_url.get().strip()
        target["webdav_user"] = self.v_dav_user.get().strip()
        target["webdav_pass"] = self.v_dav_pass.get()
        target["webdav_path"] = self.v_dav_path.get().strip().strip("/")
        target["net_path"] = self.v_net_path.get().strip()

    def update_texts(self) -> None:
        t = self.i18n.t
        self.configure(text=t("sec_cloud"))
        self.lbl_provider.configure(text=t("provider_label"))
        self.update_provider_combobox_list()
        self.btn_test_cloud.configure(text=t("btn_test_cloud"))

        self.lbl_rc_rem.configure(text=t("remote_label"))
        self.btn_rc_ref.configure(text=t("btn_refresh"))
        self.lbl_rc_path.configure(text=t("cloud_folder"))
        self.btn_dl_rc.configure(text=t("btn_dl_rclone"))
        self.btn_cfg_rc.configure(text=t("btn_cfg_rclone"))

        self.lbl_lc_det.configure(text=t("local_cloud_detected"))
        self.lbl_lc_target.configure(text=t("local_cloud_target"))
        self.btn_lc_browse.configure(text=t("btn_browse"))

        self.lbl_ftp_host.configure(text=t("ftp_host"))
        self.lbl_ftp_port.configure(text=t("ftp_port"))
        self.lbl_ftp_user.configure(text=t("ftp_user"))
        self.lbl_ftp_pass.configure(text=t("ftp_pass"))
        self.lbl_ftp_path.configure(text=t("ftp_path"))
        self.chk_ftp_tls.configure(text=t("ftp_tls"))

        self.lbl_dav_url.configure(text=t("webdav_url"))
        self.lbl_dav_user.configure(text=t("ftp_user"))
        self.lbl_dav_pass.configure(text=t("ftp_pass"))
        self.lbl_dav_path.configure(text=t("webdav_path"))

        self.lbl_net_path.configure(text=t("net_path_label"))
        self.btn_net_browse.configure(text=t("btn_browse"))

        self.chk_cloud_en.configure(text=t("cloud_auto_every"))
        self.lbl_cdays1.configure(text=t("min_del_after"))
        self.lbl_cdays2.configure(text=t("days_zero_never"))

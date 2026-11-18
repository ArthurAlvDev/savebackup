"""
Janela Principal da Aplicação SaveBackup.
Coordena a interface do usuário, eventos de janela, fila assíncrona e agendamentos periódicos.
"""
from __future__ import annotations

import ctypes
from datetime import datetime
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from src.config.constants import (
    APP_ID,
    APP_TITLE,
    APP_VERSION,
    DATA_DIR,
    DEFAULT_DEST,
    IS_WIN,
    get_icon_path,
)
from src.config.settings import ConfigManager
from src.core.archiver import make_zip
from src.core.retention import rotate_local_backups
from src.i18n.manager import I18nManager
from src.platform.autostart import is_autostart_enabled, set_autostart
from src.platform.win_tray import WinTrayIcon
from src.storage.ftp_client import ftp_test, ftp_upload_backups
from src.storage.local_sync import sync_to_directory
from src.storage.rclone_client import find_rclone, rclone_run
from src.storage.webdav_client import get_webdav_base_url, webdav_test, webdav_upload_backups
from src.ui.components.actions_view import ActionsComponent
from src.ui.components.cloud_view import CloudBackupComponent
from src.ui.components.footer import FooterComponent
from src.ui.components.header import HeaderComponent
from src.ui.components.local_view import LocalBackupComponent
from src.ui.components.log_view import LogComponent
from src.ui.components.sources_view import SourcesComponent


class MainWindow:
    """Controlador central da interface Tkinter e do ciclo de vida da aplicação."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        self.cfg_mgr = ConfigManager()
        self.cfg = self.cfg_mgr.data

        # Inicializa gerenciador de internacionalização com o idioma salvo
        self.i18n = I18nManager(current_lang=self.cfg.get("lang", "pt"))

        # Sincroniza estado de autostart com o registro do sistema operacional
        if IS_WIN:
            system_autostart = is_autostart_enabled()
            if system_autostart != self.cfg.get("autostart", False):
                if self.cfg.get("autostart"):
                    set_autostart(True)
                else:
                    self.cfg["autostart"] = system_autostart

        self.q: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.lock_local = threading.Lock()
        self.lock_cloud = threading.Lock()

        # Define ID do processo no Windows para que o ícone na barra de tarefas seja único
        if IS_WIN:
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
            except Exception:
                pass

        root.title(f"{APP_TITLE} {APP_VERSION}")
        root.geometry("780x820")
        root.minsize(740, 740)

        # Aplica ícone se disponível
        ico = get_icon_path()
        if ico:
            try:
                root.iconbitmap(default=ico)
            except Exception:
                pass

        try:
            ttk.Style().theme_use("vista")
        except tk.TclError:
            pass

        self._build_layout()

        # Criação do System Tray Nativo
        self.tray = WinTrayIcon(
            on_open=lambda: self.ui(self.restore_from_tray),
            on_backup=lambda: self.ui(self.manual_backup),
            on_upload=lambda: self.ui(self.manual_upload),
            on_exit=lambda: self.ui(self.quit_app),
            t_func=self.i18n.t,
        )

        # Intercepta Fechar (X) e Minimizar (_) para ocultar na bandeja
        root.protocol("WM_DELETE_WINDOW", self.on_close_button)
        root.bind("<Unmap>", self.on_window_unmap)

        if "--minimized" in sys.argv:
            root.withdraw()

        self.pump()
        self.cloud_view.refresh_remotes(silent=True)
        self.log(self.i18n.t("log_started"))
        root.after(3000, self.tick)

    def _build_layout(self) -> None:
        r = self.root
        r.columnconfigure(0, weight=1)
        r.rowconfigure(5, weight=1)
        pad = {"padx": 10, "pady": 4}

        # 0. Cabeçalho (Idioma + Opção de bandeja)
        self.header = HeaderComponent(
            r,
            self.i18n,
            close_to_tray=self.cfg.get("close_to_tray", True),
            on_lang_changed=self.on_language_changed,
            on_tray_toggle=self.on_tray_toggle,
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))

        # 1. Pastas de Origem (Saves)
        self.sources_view = SourcesComponent(
            r,
            self.i18n,
            folders=self.cfg.get("folders", []),
            on_change=self.collect_and_save,
        )
        self.sources_view.grid(row=1, column=0, sticky="ew", **pad)

        # 2. Destinos Locais
        self.local_view = LocalBackupComponent(
            r,
            self.i18n,
            destinations=self.cfg.get("backup_dirs", [DEFAULT_DEST]),
            enabled=self.cfg.get("local_enabled", True),
            interval_minutes=self.cfg.get("local_minutes", 30),
            keep_count=self.cfg.get("keep_local", 10),
            on_change=self.collect_and_save,
            log_func=self.log,
        )
        self.local_view.grid(row=2, column=0, sticky="ew", **pad)

        # 3. Nuvem e Backup Externo
        self.cloud_view = CloudBackupComponent(
            r,
            self.i18n,
            cfg=self.cfg,
            on_change=self.collect_and_save,
            on_test=self.test_cloud,
            log_func=self.log,
            run_async=self.run_async,
        )
        self.cloud_view.grid(row=3, column=0, sticky="ew", **pad)

        # 4. Ações e Autostart
        self.actions_view = ActionsComponent(
            r,
            self.i18n,
            autostart_enabled=self.cfg.get("autostart", False),
            on_backup_now=self.manual_backup,
            on_upload_now=self.manual_upload,
            on_open_all=self.local_view.open_dest,
            on_autostart_toggle=self.toggle_autostart,
        )
        self.actions_view.grid(row=4, column=0, sticky="ew", **pad)

        # 5. Log de Atividades
        self.log_view = LogComponent(r, self.i18n)
        self.log_view.grid(row=5, column=0, sticky="nsew", **pad)

        # 6. Rodapé: crédito OlacDev, versão e licença
        self.footer = FooterComponent(r)
        self.footer.grid(row=6, column=0, sticky="ew", padx=12, pady=(2, 8))

    # ---- Troca de Idioma em Tempo Real
    def on_language_changed(self, lang_code: str) -> None:
        self.i18n.set_language(lang_code)
        self.cfg["lang"] = lang_code
        self.apply_language()
        self.collect_and_save()

    def on_tray_toggle(self, enabled: bool) -> None:
        self.cfg["close_to_tray"] = enabled
        self.collect_and_save()

    def apply_language(self) -> None:
        """Propaga atualização de idioma para todos os componentes."""
        self.header.update_texts()
        self.sources_view.update_texts()
        self.local_view.update_texts()
        self.cloud_view.update_texts()
        self.actions_view.update_texts()
        self.log_view.update_texts()

    # ---- Persistência de Dados
    def collect_and_save(self) -> None:
        """Coleta o estado atual de todos os componentes da interface e persiste."""
        c = self.cfg
        c["folders"] = self.sources_view.get_folders()
        c["backup_dirs"] = self.local_view.get_destinations()
        c["local_enabled"] = self.local_view.is_enabled()
        c["local_minutes"] = self.local_view.get_minutes()
        c["keep_local"] = self.local_view.get_keep()
        c["close_to_tray"] = self.header.v_close_tray.get()
        self.cloud_view.collect_to_dict(c)
        self.cfg_mgr.save()

    # ---- Log e Fila de UI Thread-Safe
    def log(self, msg: str) -> None:
        formatted = f"[{datetime.now():%d/%m %H:%M:%S}] {msg}"
        self.q.put(("log", formatted))

    def ui(self, fn: Callable[[], None]) -> None:
        self.q.put(("call", fn))

    def pump(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.log_view.append_message(payload)
                elif kind == "call":
                    payload()
        except queue.Empty:
            pass
        self.root.after(200, self.pump)

    def run_async(self, fn: Callable[[], None]) -> None:
        threading.Thread(target=fn, daemon=True).start()

    # ---- System Tray e Eventos de Janela
    def hide_to_tray(self) -> None:
        self.collect_and_save()
        self.root.withdraw()
        self.log(self.i18n.t("log_minimized_tray"))
        self.tray.show_balloon(
            self.i18n.t("tray_balloon_title"), self.i18n.t("tray_balloon_msg")
        )

    def on_window_unmap(self, event) -> None:
        if event.widget is self.root and self.root.state() == "iconic":
            if IS_WIN and self.header.v_close_tray.get():
                self.root.after(10, self.hide_to_tray)

    def on_close_button(self) -> None:
        self.collect_and_save()
        if IS_WIN and self.cfg.get("close_to_tray", True):
            self.hide_to_tray()
        else:
            self.quit_app()

    def restore_from_tray(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def quit_app(self) -> None:
        self.collect_and_save()
        self.tray.stop()
        self.root.destroy()

    def toggle_autostart(self, enabled: bool) -> None:
        set_autostart(enabled)
        self.cfg["autostart"] = enabled
        self.collect_and_save()
        self.log(
            self.i18n.t("log_autostart_on" if enabled else "log_autostart_off")
        )

    # ---- Agendamento Periódico
    def _is_cloud_configured(self) -> bool:
        c = self.cfg
        p = c.get("cloud_provider", "rclone")
        if p == "rclone":
            return bool(c.get("cloud_remote"))
        if p == "local_cloud":
            return bool(c.get("native_cloud_dir"))
        if p == "ftp":
            return bool(c.get("ftp_host"))
        if p == "webdav":
            return bool(c.get("webdav_url"))
        if p == "network":
            return bool(c.get("net_path"))
        return False

    def tick(self) -> None:
        try:
            self.collect_and_save()
            c = self.cfg
            now = time.time()
            if (
                c["local_enabled"]
                and c["folders"]
                and now - c.get("last_local", 0) >= c["local_minutes"] * 60
                and not self.lock_local.locked()
            ):
                self.run_async(self.do_backup)

            if (
                c["cloud_enabled"]
                and self._is_cloud_configured()
                and now - c.get("last_cloud", 0) >= c["cloud_minutes"] * 60
                and not self.lock_cloud.locked()
            ):
                self.run_async(self.do_upload)
        finally:
            self.root.after(5000, self.tick)

    def manual_backup(self) -> None:
        self.collect_and_save()
        self.run_async(self.do_backup)

    def manual_upload(self) -> None:
        self.collect_and_save()
        self.run_async(self.do_upload)

    # ---- Execução do Backup Local
    def do_backup(self) -> None:
        if not self.lock_local.acquire(blocking=False):
            return
        try:
            folders = self.cfg.get("folders", [])
            if not folders:
                self.log(self.i18n.t("log_no_sources"))
                return

            dest_paths = [
                Path(p) for p in self.cfg.get("backup_dirs", []) if str(p).strip()
            ]
            if not dest_paths:
                self.log(self.i18n.t("log_no_dests"))
                return

            self.log(self.i18n.t("log_starting_backup"))
            created_zip = None
            primary_idx = 0

            for idx, d in enumerate(dest_paths):
                try:
                    created_zip = make_zip(
                        folders, d, dest_paths, self.log, self.i18n.t
                    )
                    primary_idx = idx
                    if created_zip:
                        size_mb = created_zip.stat().st_size / 1048576
                        self.log(
                            self.i18n.t(
                                "log_backup_created",
                                str(d),
                                created_zip.name,
                                size_mb,
                            )
                        )
                        rotate_local_backups(d, self.cfg.get("keep_local", 10))
                    break
                except Exception as e:
                    self.log(self.i18n.t("log_backup_copy_err", str(d), e))

            # Réplica redundante nos destinos secundários
            if created_zip and created_zip.exists():
                for idx, d in enumerate(dest_paths):
                    if idx == primary_idx:
                        continue
                    try:
                        d.mkdir(parents=True, exist_ok=True)
                        target_copy = d / created_zip.name
                        shutil.copy2(created_zip, target_copy)
                        rotate_local_backups(d, self.cfg.get("keep_local", 10))
                        self.log(self.i18n.t("log_backup_copied", str(d)))
                    except Exception as e:
                        self.log(self.i18n.t("log_backup_copy_err", str(d), e))

        except Exception as e:
            self.log(self.i18n.t("log_backup_err", e))
        finally:
            self.cfg["last_local"] = time.time()
            self.lock_local.release()

    def _find_source_backup_dir(self) -> Path | None:
        for p in self.cfg.get("backup_dirs", []):
            d = Path(p)
            if d.exists() and any(d.glob("saves_*.zip")):
                return d
        return None

    # ---- Execução do Upload para Nuvem
    def do_upload(self) -> None:
        if not self.lock_cloud.acquire(blocking=False):
            return
        try:
            c = self.cfg
            src = self._find_source_backup_dir()
            if not src:
                self.log(self.i18n.t("log_no_backups_yet"))
                return

            prov = c.get("cloud_provider", "rclone")

            if prov == "rclone":
                if not c.get("cloud_remote"):
                    self.log(self.i18n.t("log_choose_remote"))
                    return
                if not find_rclone():
                    self.log(self.i18n.t("log_rclone_missing"))
                    return
                target = f"{c['cloud_remote']}:{c['cloud_path']}"
                self.log(self.i18n.t("log_uploading_to", target))
                r = rclone_run(
                    [
                        "copy",
                        str(src),
                        target,
                        "--include",
                        "saves_*.zip",
                        "--transfers",
                        "2",
                        "--retries",
                        "3",
                    ]
                )
                if r.returncode != 0:
                    self.log(
                        self.i18n.t(
                            "log_upload_err",
                            r.stderr.strip()[-400:] or "rclone error",
                        )
                    )
                    return
                if c.get("cloud_keep_days", 0) > 0:
                    rclone_run(
                        [
                            "delete",
                            target,
                            "--include",
                            "saves_*.zip",
                            "--min-age",
                            f"{c['cloud_keep_days']}d",
                        ]
                    )
                self.log(self.i18n.t("log_upload_done", "rclone"))

            elif prov == "local_cloud":
                target_dir = Path(c.get("native_cloud_dir", "").strip())
                if not str(target_dir).strip():
                    raise ValueError("Pasta de nuvem local não definida.")
                self.log(self.i18n.t("log_uploading_to", str(target_dir)))
                n = sync_to_directory(src, target_dir, c.get("cloud_keep_days", 0))
                self.log(self.i18n.t("log_upload_done", n))

            elif prov == "ftp":
                self.log(
                    self.i18n.t(
                        "log_uploading_to",
                        f"FTP://{c.get('ftp_host')}{c.get('ftp_path')}",
                    )
                )
                n = ftp_upload_backups(src, c)
                self.log(self.i18n.t("log_upload_done", n))

            elif prov == "webdav":
                self.log(
                    self.i18n.t("log_uploading_to", get_webdav_base_url(c))
                )
                n = webdav_upload_backups(src, c)
                self.log(self.i18n.t("log_upload_done", n))

            elif prov == "network":
                target_dir = Path(c.get("net_path", "").strip())
                if not str(target_dir).strip():
                    raise ValueError("Caminho de rede vazio.")
                self.log(self.i18n.t("log_uploading_to", str(target_dir)))
                n = sync_to_directory(src, target_dir, c.get("cloud_keep_days", 0))
                self.log(self.i18n.t("log_upload_done", n))

        except Exception as e:
            self.log(self.i18n.t("log_upload_err", e))
        finally:
            self.cfg["last_cloud"] = time.time()
            self.lock_cloud.release()

    # ---- Teste de Conectividade
    def test_cloud(self) -> None:
        self.collect_and_save()

        def work():
            c = self.cfg
            prov = c.get("cloud_provider", "rclone")
            try:
                if prov == "rclone":
                    if not c.get("cloud_remote"):
                        self.log(self.i18n.t("log_choose_remote"))
                        return
                    if not find_rclone():
                        self.log(self.i18n.t("log_rclone_missing"))
                        return
                    r = rclone_run(
                        ["mkdir", f"{c['cloud_remote']}:{c['cloud_path']}"]
                    )
                    if r.returncode == 0:
                        self.log(self.i18n.t("log_test_ok"))
                    else:
                        self.log(
                            self.i18n.t("log_test_fail", r.stderr.strip()[-400:])
                        )
                elif prov == "local_cloud":
                    p = Path(c.get("native_cloud_dir", "").strip())
                    if not str(p).strip():
                        raise ValueError("Escolha uma pasta primeiro.")
                    p.mkdir(parents=True, exist_ok=True)
                    test_f = p / ".savebackup_test"
                    test_f.write_text("ok", encoding="utf-8")
                    test_f.unlink(missing_ok=True)
                    self.log(self.i18n.t("log_test_ok"))
                elif prov == "ftp":
                    ftp_test(c)
                    self.log(self.i18n.t("log_test_ok"))
                elif prov == "webdav":
                    webdav_test(c)
                    self.log(self.i18n.t("log_test_ok"))
                elif prov == "network":
                    p = Path(c.get("net_path", "").strip())
                    if not str(p).strip():
                        raise ValueError("Informe o caminho de rede.")
                    p.mkdir(parents=True, exist_ok=True)
                    test_f = p / ".savebackup_test"
                    test_f.write_text("ok", encoding="utf-8")
                    test_f.unlink(missing_ok=True)
                    self.log(self.i18n.t("log_test_ok"))
            except Exception as e:
                self.log(self.i18n.t("log_test_fail", e))

        self.run_async(work)

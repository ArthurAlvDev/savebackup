"""
Testes automatizados do núcleo do SaveBackup.

Execução:
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import ConfigManager
from src.core.archiver import cleanup_stale_parts, make_zip
from src.core.retention import rotate_local_backups
from src.i18n.manager import I18nManager
from src.storage.rclone_client import build_remote_target
from src.storage.webdav_client import get_webdav_base_url


def _t(key: str, *args) -> str:
    return key.format(*args) if args else key


class ArchiverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="sb_test_"))
        self.source = self.tmp / "Save"
        (self.source / "sub").mkdir(parents=True)
        (self.source / "slot1.sav").write_bytes(b"a" * 2048)
        (self.source / "sub" / "slot2.sav").write_text("save data", encoding="utf-8")
        self.dest = self.tmp / "backups"
        self.logs: list[str] = []

    def test_creates_valid_zip_with_all_files(self) -> None:
        path = make_zip([str(self.source)], self.dest, [self.dest], self.logs.append, _t)

        self.assertIsNotNone(path)
        assert path is not None
        self.assertTrue(path.name.startswith("saves_"))
        with zipfile.ZipFile(path) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(
                sorted(z.namelist()), ["Save/slot1.sav", "Save/sub/slot2.sav"]
            )

    def test_no_files_produces_no_archive(self) -> None:
        empty = self.tmp / "Empty"
        empty.mkdir()

        path = make_zip([str(empty)], self.dest, [self.dest], self.logs.append, _t)

        self.assertIsNone(path)
        self.assertIn("log_no_files", self.logs)
        self.assertEqual(list(self.dest.glob("*.zip")), [])

    def test_destination_inside_source_is_not_archived(self) -> None:
        inner_dest = self.source / "backups"
        inner_dest.mkdir()
        (inner_dest / "old.zip").write_bytes(b"x")

        path = make_zip(
            [str(self.source)], inner_dest, [inner_dest], self.logs.append, _t
        )

        self.assertIsNotNone(path)
        assert path is not None
        with zipfile.ZipFile(path) as z:
            self.assertFalse(any("old.zip" in n for n in z.namelist()))

    def test_missing_source_is_logged_and_skipped(self) -> None:
        path = make_zip(
            [str(self.tmp / "nao_existe")],
            self.dest,
            [self.dest],
            self.logs.append,
            _t,
        )

        self.assertIsNone(path)
        self.assertTrue(any("log_folder_missing" in line for line in self.logs))


class StalePartsTests(unittest.TestCase):
    def test_old_partial_files_are_removed_and_recent_ones_kept(self) -> None:
        dest = Path(tempfile.mkdtemp(prefix="sb_part_"))
        old = dest / "saves_2026-01-01_00-00-00.zip.part"
        new = dest / "saves_2026-01-02_00-00-00.zip.part"
        old.write_bytes(b"x")
        new.write_bytes(b"x")
        ancient = 1_600_000_000
        os.utime(old, (ancient, ancient))

        removed = cleanup_stale_parts(dest)

        self.assertEqual(removed, 1)
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())


class RetentionTests(unittest.TestCase):
    def test_keeps_only_most_recent_archives(self) -> None:
        dest = Path(tempfile.mkdtemp(prefix="sb_ret_"))
        for day in range(1, 6):
            (dest / f"saves_2026-01-0{day}_00-00-00.zip").write_bytes(b"x")

        removed = rotate_local_backups(dest, keep=2)

        self.assertEqual(removed, 3)
        self.assertEqual(
            sorted(p.name for p in dest.glob("saves_*.zip")),
            [
                "saves_2026-01-04_00-00-00.zip",
                "saves_2026-01-05_00-00-00.zip",
            ],
        )

    def test_zero_keep_deletes_nothing(self) -> None:
        dest = Path(tempfile.mkdtemp(prefix="sb_ret_"))
        (dest / "saves_2026-01-01_00-00-00.zip").write_bytes(b"x")

        self.assertEqual(rotate_local_backups(dest, keep=0), 0)
        self.assertEqual(len(list(dest.glob("*.zip"))), 1)


class I18nTests(unittest.TestCase):
    def setUp(self) -> None:
        self.i18n = I18nManager(current_lang="pt")

    def test_brazilian_portuguese_is_default(self) -> None:
        self.assertEqual(self.i18n.t("btn_backup_now"), "Fazer backup agora")

    def test_falls_back_to_english_for_unknown_language(self) -> None:
        self.i18n.set_language("xx")
        self.assertEqual(self.i18n.current_language, self.i18n.DEFAULT_LANG)

    def test_missing_key_returns_the_key(self) -> None:
        self.assertEqual(self.i18n.t("chave_inexistente_123"), "chave_inexistente_123")

    def test_all_locales_have_the_same_keys(self) -> None:
        locales = Path(PROJECT_ROOT) / "locales"
        catalogs = {
            p.stem: set(json.loads(p.read_text(encoding="utf-8")))
            for p in locales.glob("*.json")
            if not p.stem.startswith("_")
        }
        reference = catalogs["pt"]
        for lang, keys in catalogs.items():
            self.assertEqual(
                reference - keys, set(), f"faltam chaves em {lang}.json"
            )


class SecurityValidationTests(unittest.TestCase):
    def test_webdav_rejects_plain_http_for_public_host(self) -> None:
        with self.assertRaises(ValueError):
            get_webdav_base_url({"webdav_url": "http://cloud.example.com/dav"})

    def test_webdav_accepts_https(self) -> None:
        url = get_webdav_base_url(
            {"webdav_url": "https://cloud.example.com/dav/", "webdav_path": "SaveBackups"}
        )
        self.assertEqual(url, "https://cloud.example.com/dav/SaveBackups")

    def test_webdav_allows_http_on_private_network(self) -> None:
        self.assertTrue(
            get_webdav_base_url({"webdav_url": "http://192.168.0.10/dav"}).startswith(
                "http://192.168.0.10"
            )
        )

    def test_rclone_rejects_option_like_remote(self) -> None:
        with self.assertRaises(ValueError):
            build_remote_target("--config=/tmp/x", "SaveBackups")

    def test_rclone_rejects_control_characters(self) -> None:
        with self.assertRaises(ValueError):
            build_remote_target("gdrive", "Save\nBackups")

    def test_rclone_builds_target_from_valid_parts(self) -> None:
        self.assertEqual(build_remote_target("gdrive", "SaveBackups"), "gdrive:SaveBackups")


class ConfigTests(unittest.TestCase):
    def test_defaults_are_applied_to_new_config(self) -> None:
        path = Path(tempfile.mkdtemp(prefix="sb_cfg_")) / "config.json"
        cfg = ConfigManager(config_path=path)

        self.assertEqual(cfg.get("lang"), "pt")
        self.assertTrue(cfg.get("backup_dirs"))

    def test_legacy_backup_dir_is_migrated(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="sb_cfg_"))
        path = base / "config.json"
        path.write_text(
            json.dumps({"backup_dir": r"D:\Backups"}), encoding="utf-8"
        )

        cfg = ConfigManager(config_path=path)

        self.assertEqual(cfg.get("backup_dirs"), [r"D:\Backups"])

    def test_corrupted_config_falls_back_to_defaults(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="sb_cfg_"))
        path = base / "config.json"
        path.write_text("{ nao e json", encoding="utf-8")

        cfg = ConfigManager(config_path=path)

        self.assertEqual(cfg.get("lang"), "pt")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Gerenciador de configurações persistentes da aplicação.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config.constants import CONFIG_FILE, DATA_DIR, DEFAULT_DEST, DEFAULTS


class ConfigManager:
    """Gerencia leitura, gravação e integridade das configurações (config.json)."""

    def __init__(self, config_path: Path = CONFIG_FILE) -> None:
        self.config_path = config_path
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._last_saved_json: str = ""
        self.load()

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, mapping: dict[str, Any]) -> None:
        self._data.update(mapping)

    def load(self) -> dict[str, Any]:
        """Carrega do disco aplicando defaults e migrações necessárias."""
        self._data = dict(DEFAULTS)
        if self.config_path.is_file():
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    # Migração de versão legada (backup_dir -> backup_dirs)
                    if "backup_dir" in raw and "backup_dirs" not in raw:
                        old_dir = str(raw.get("backup_dir", "")).strip()
                        if old_dir:
                            raw["backup_dirs"] = [old_dir]
                    self._data.update(raw)
            except Exception:
                pass

        # Garante integridade mínima
        if not self._data.get("backup_dirs"):
            self._data["backup_dirs"] = [DEFAULT_DEST]

        return self._data

    def save(self) -> bool:
        """Salva as configurações se houver alteração nos dados."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data_str = json.dumps(self._data, indent=2, sort_keys=True)
            if data_str != self._last_saved_json:
                self.config_path.write_text(data_str, encoding="utf-8")
                self._last_saved_json = data_str
            return True
        except Exception:
            return False

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

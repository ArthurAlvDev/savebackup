"""
Sistema profissional de internacionalização (i18n).

Carrega traduções de arquivos JSON externos na pasta `locales/`.
Permite adicionar ou alterar idiomas sem tocar no código Python.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.config.constants import APP_ROOT, BUNDLE_DIR


class I18nManager:
    """Gerencia catálogo de traduções, detecção de idiomas e formatação de textos."""

    DEFAULT_LANG = "pt"

    # Nomes padrão caso _metadata.json não esteja acessível
    FALLBACK_LANG_NAMES = {
        "pt": "Português (BR)",
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "it": "Italiano",
    }

    def __init__(self, current_lang: str = "pt") -> None:
        self.locales_dir = self._find_locales_dir()
        self._languages: dict[str, str] = dict(self.FALLBACK_LANG_NAMES)
        self._catalogs: dict[str, dict[str, str]] = {}
        self._listeners: list[Callable[[str], None]] = []
        self._current_lang = current_lang

        self._load_metadata()
        self._preload_catalog(self.DEFAULT_LANG)
        if self._current_lang != self.DEFAULT_LANG:
            self._preload_catalog(self._current_lang)

    def _find_locales_dir(self) -> Path:
        """Localiza a pasta locales em desenvolvimento ou compilado (PyInstaller)."""
        candidates = [
            BUNDLE_DIR / "locales",
            APP_ROOT / "locales",
            Path(__file__).resolve().parent.parent.parent / "locales",
        ]
        for c in candidates:
            if c.is_dir():
                return c
        return candidates[0]

    def _load_metadata(self) -> None:
        """Carrega metadados de idiomas suportados a partir de _metadata.json."""
        meta_file = self.locales_dir / "_metadata.json"
        if meta_file.is_file():
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                if "languages" in data and isinstance(data["languages"], dict):
                    self._languages = data["languages"]
                if "default" in data:
                    self.DEFAULT_LANG = data["default"]
            except Exception:
                pass

        # Descoberta dinâmica: se existirem outros arquivos .json no diretório
        if self.locales_dir.is_dir():
            for json_path in self.locales_dir.glob("*.json"):
                stem = json_path.stem
                if stem.startswith("_"):
                    continue
                if stem not in self._languages:
                    self._languages[stem] = stem.upper()

    def _preload_catalog(self, lang: str) -> None:
        """Carrega o catálogo de um idioma do disco se ainda não estiver na memória."""
        if lang in self._catalogs:
            return

        lang_file = self.locales_dir / f"{lang}.json"
        if lang_file.is_file():
            try:
                data = json.loads(lang_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._catalogs[lang] = data
                    return
            except Exception:
                pass

        self._catalogs[lang] = {}

    @property
    def current_language(self) -> str:
        return self._current_lang

    def get_languages(self) -> dict[str, str]:
        """Retorna dicionário de código -> nome de exibição."""
        return dict(self._languages)

    def set_language(self, lang_code: str) -> None:
        """Define o idioma ativo e notifica observadores."""
        if lang_code not in self._languages:
            lang_code = self.DEFAULT_LANG

        self._preload_catalog(lang_code)
        self._current_lang = lang_code

        # Notifica todos os observadores cadastrados
        for listener in self._listeners:
            try:
                listener(lang_code)
            except Exception:
                pass

    def subscribe(self, callback: Callable[[str], None]) -> None:
        """Cadastra uma função para ser chamada sempre que o idioma mudar."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        """Remove o cadastro da função observadora."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def t(self, key: str, *args: Any) -> str:
        """
        Retorna a tradução para a chave informada.

        Ordem de resolução:
        1. Catálogo do idioma atual
        2. Catálogo do idioma padrão (pt)
        3. Catálogo inglês (en)
        4. A própria chave textual
        """
        self._preload_catalog(self._current_lang)
        current_cat = self._catalogs.get(self._current_lang, {})

        text = current_cat.get(key)
        if text is None and self._current_lang != self.DEFAULT_LANG:
            self._preload_catalog(self.DEFAULT_LANG)
            text = self._catalogs.get(self.DEFAULT_LANG, {}).get(key)

        if text is None and self._current_lang != "en":
            self._preload_catalog("en")
            text = self._catalogs.get("en", {}).get(key)

        if text is None:
            text = key

        if args:
            try:
                return text.format(*args)
            except Exception:
                return text
        return text

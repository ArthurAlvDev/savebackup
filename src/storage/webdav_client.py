"""
Cliente nativo WebDAV (Nextcloud, ownCloud, Koofr, pCloud, Box, etc.).
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import ipaddress
from pathlib import Path
import ssl
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from src.config.constants import APP_NAME, APP_VERSION, toint


def _is_local_host(hostname: str) -> bool:
    """Servidores locais podem usar http:// sem risco de tráfego na internet."""
    host = (hostname or "").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback


def get_webdav_base_url(cfg: dict[str, Any]) -> str:
    """Monta a URL completa do endpoint WebDAV, exigindo HTTPS fora da rede local."""
    base = str(cfg.get("webdav_url", "")).strip().rstrip("/")
    if not base:
        raise ValueError("URL WebDAV vazia.")

    parsed = urllib.parse.urlparse(base)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("A URL WebDAV deve começar com https:// (ou http:// em rede local).")
    if parsed.scheme == "http" and not _is_local_host(parsed.hostname or ""):
        raise ValueError(
            "Use https:// para servidores fora da rede local: credenciais e backups "
            "passariam sem criptografia."
        )

    sub = str(cfg.get("webdav_path", "")).strip().strip("/")
    return f"{base}/{urllib.parse.quote(sub)}" if sub else base


def _webdav_headers(cfg: dict[str, Any], extra: dict[str, str] | None = None) -> dict[str, str]:
    user = str(cfg.get("webdav_user", "")).strip()
    passwd = str(cfg.get("webdav_pass", ""))
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
    if user or passwd:
        token = base64.b64encode(f"{user}:{passwd}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    if extra:
        headers.update(extra)
    return headers


def _webdav_request(url: str, method: str, headers: dict[str, str], data: bytes | None = None):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    return urllib.request.urlopen(req, timeout=60, context=ctx)


def _webdav_ensure_dir(cfg: dict[str, Any]) -> None:
    base = str(cfg.get("webdav_url", "")).strip().rstrip("/")
    if not base:
        raise ValueError("URL WebDAV vazia.")
    sub = str(cfg.get("webdav_path", "")).strip().strip("/")
    cur = base
    for part in [p for p in sub.split("/") if p]:
        cur = f"{cur}/{urllib.parse.quote(part)}"
        try:
            _webdav_request(cur + "/", "MKCOL", _webdav_headers(cfg)).close()
        except urllib.error.HTTPError as e:
            if e.code not in (200, 201, 204, 301, 302, 405):
                raise


def _webdav_list(cfg: dict[str, Any]) -> dict[str, datetime | None]:
    url = get_webdav_base_url(cfg) + "/"
    body = (
        b'<?xml version="1.0" encoding="utf-8"?>'
        b'<d:propfind xmlns:d="DAV:"><d:prop><d:getlastmodified/></d:prop></d:propfind>'
    )
    headers = _webdav_headers(cfg, {"Depth": "1", "Content-Type": "application/xml"})
    items: dict[str, datetime | None] = {}

    with _webdav_request(url, "PROPFIND", headers, data=body) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    for response in root.findall(".//{DAV:}response"):
        href_el = response.find("{DAV:}href")
        if href_el is None or not href_el.text:
            continue
        name = urllib.parse.unquote(href_el.text.rstrip("/").rsplit("/", 1)[-1])
        lastmod_el = response.find(".//{DAV:}getlastmodified")
        mtime = None
        if lastmod_el is not None and lastmod_el.text:
            try:
                mtime = parsedate_to_datetime(lastmod_el.text)
            except Exception:
                pass
        items[name] = mtime

    return items


def webdav_test(cfg: dict[str, Any]) -> None:
    """Testa a conectividade e permissões no servidor WebDAV."""
    _webdav_ensure_dir(cfg)
    _webdav_list(cfg)


def webdav_upload_backups(src_dir: Path, cfg: dict[str, Any]) -> int:
    """Envia novos arquivos .zip via WebDAV e exclui arquivos antigos conforme retenção."""
    _webdav_ensure_dir(cfg)
    existing = _webdav_list(cfg)
    base_url = get_webdav_base_url(cfg)
    uploaded = 0

    for zf in sorted(src_dir.glob("saves_*.zip")):
        if zf.name not in existing:
            file_url = f"{base_url}/{urllib.parse.quote(zf.name)}"
            data = zf.read_bytes()
            headers = _webdav_headers(cfg, {"Content-Type": "application/zip"})
            with _webdav_request(file_url, "PUT", headers, data=data):
                pass
            uploaded += 1

    keep_days = toint(cfg.get("cloud_keep_days", 0), 0, 0)
    if keep_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
        for name, mtime in existing.items():
            if name.startswith("saves_") and name.endswith(".zip"):
                should_del = False
                if mtime is not None:
                    if mtime.tzinfo is None:
                        mtime = mtime.replace(tzinfo=timezone.utc)
                    should_del = mtime < cutoff
                else:
                    try:
                        dt = datetime.strptime(
                            name[6:25], "%Y-%m-%d_%H-%M-%S"
                        ).replace(tzinfo=timezone.utc)
                        should_del = dt < cutoff
                    except Exception:
                        pass
                if should_del:
                    try:
                        file_url = f"{base_url}/{urllib.parse.quote(name)}"
                        _webdav_request(file_url, "DELETE", _webdav_headers(cfg)).close()
                    except Exception:
                        pass

    return uploaded

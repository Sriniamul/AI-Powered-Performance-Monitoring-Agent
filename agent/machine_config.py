"""Validation and persistence for dashboard-managed monitoring targets."""

import ipaddress
import os
import tempfile
import uuid
from threading import RLock
from pathlib import Path

import yaml


PUBLIC_FIELDS = ("id", "name", "ip_address", "port", "username", "service_name", "environment", "enabled")
_CONFIG_LOCK = RLock()


def list_machines(config_path: str | Path) -> list[dict]:
    data = _read(config_path)
    return [{**{key: item.get(key) for key in PUBLIC_FIELDS}, "password_configured": bool(item.get("password"))}
            for item in data.get("machines", [])]


def save_machine(config_path: str | Path, payload: dict, machine_id: str | None = None) -> dict:
    clean = _validate(payload)
    with _CONFIG_LOCK:
        data = _read(config_path)
        machines = data.setdefault("machines", [])
        existing = next((item for item in machines if item.get("id") == machine_id), None)
        if machine_id and existing is None:
            raise KeyError("machine not found")
        if existing:
            if not clean.get("password"):
                clean["password"] = existing.get("password", "")
            existing.clear()
            existing.update(clean, id=machine_id)
            saved = existing
        else:
            saved = {**clean, "id": uuid.uuid4().hex}
            machines.append(saved)
        _write(config_path, data)
    return {**{key: saved.get(key) for key in PUBLIC_FIELDS}, "password_configured": bool(saved.get("password"))}


def delete_machine(config_path: str | Path, machine_id: str) -> bool:
    with _CONFIG_LOCK:
        data = _read(config_path)
        machines = data.get("machines", [])
        kept = [item for item in machines if item.get("id") != machine_id]
        if len(kept) == len(machines):
            return False
        data["machines"] = kept
        _write(config_path, data)
    return True


def _validate(payload: dict) -> dict:
    address = str(payload.get("ip_address", "")).strip()
    try:
        ipaddress.ip_address(address)
    except ValueError as exc:
        raise ValueError("A valid IPv4 or IPv6 address is required") from exc
    username = str(payload.get("username", "")).strip()
    if not username:
        raise ValueError("Username is required")
    port = int(payload.get("port", 22))
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    return {
        "name": str(payload.get("name", "")).strip() or address,
        "ip_address": address,
        "port": port,
        "username": username,
        "password": str(payload.get("password", "")),
        "service_name": str(payload.get("service_name", "")).strip(),
        "environment": str(payload.get("environment", "")).strip(),
        "enabled": bool(payload.get("enabled", True)),
    }


def _read(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _write(path: str | Path, data: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=target.parent, prefix=target.name, suffix=".tmp", text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, sort_keys=False)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

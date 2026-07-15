"""Durable cooldown-based suppression for repeated incidents."""

from datetime import datetime, timezone
import json
from pathlib import Path

from agent.utils.logger import get_logger


logger = get_logger(__name__)


class IncidentDeduplicator:
    def __init__(self, config: dict):
        cfg = config.get("incidents", {})
        self.enabled = bool(cfg.get("deduplication_enabled", True))
        self.cooldown_seconds = max(0, int(cfg.get("cooldown_seconds", 3600)))
        artifact_dir = Path(config.get("agent", {}).get("artifact_dir", "artifacts"))
        self.state_path = Path(cfg.get("state_path", artifact_dir / "incident_registry.json"))
        self.entries = self._load()

    @staticmethod
    def incident_key(service: str, anomaly_types: list[str]) -> str:
        normalized_types = sorted(set(anomaly_types or ["behavioral_anomaly"]))
        return f"{service or 'unknown-service'}|{','.join(normalized_types)}"

    def find_duplicate(self, service: str, anomaly_types: list[str], now: float | None = None) -> dict | None:
        if not self.enabled:
            return None
        timestamp = datetime.now(timezone.utc).timestamp() if now is None else now
        entry = self.entries.get(self.incident_key(service, anomaly_types))
        if entry and timestamp - float(entry.get("created_at_epoch", 0)) < self.cooldown_seconds:
            return entry
        return None

    def record(self, service: str, anomaly_types: list[str], issue_key: str, now: float | None = None):
        if not self.enabled:
            return
        timestamp = datetime.now(timezone.utc).timestamp() if now is None else now
        key = self.incident_key(service, anomaly_types)
        self.entries[key] = {
            "issue_key": issue_key,
            "service": service or "unknown-service",
            "anomaly_types": sorted(set(anomaly_types or ["behavioral_anomaly"])),
            "created_at_epoch": timestamp,
            "created_at": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
        }
        self._save()

    def _load(self) -> dict:
        if not self.enabled or not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            if payload.get("version") == 1 and isinstance(payload.get("entries"), dict):
                return payload["entries"]
        except (OSError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Could not restore incident registry from %s: %s", self.state_path, exc)
        return {}

    def _save(self):
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            temporary.write_text(json.dumps({"version": 1, "entries": self.entries}, indent=2), encoding="utf-8")
            temporary.replace(self.state_path)
        except OSError as exc:
            logger.warning("Could not persist incident registry to %s: %s", self.state_path, exc)

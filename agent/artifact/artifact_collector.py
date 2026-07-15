from datetime import datetime, timezone
from pathlib import Path
import json
import time

from agent.artifact.compressor import zip_files
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class ArtifactCollector:
    def __init__(self, config: dict):
        self.artifact_dir = Path(config.get("agent", {}).get("artifact_dir", "artifacts"))
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        retention = config.get("artifact_retention", {})
        self.retention_enabled = bool(retention.get("enabled", True))
        self.max_age_days = max(0.0, float(retention.get("max_age_days", 14)))
        self.max_files = max(1, int(retention.get("max_files", 500)))
        self.enforce_retention()

    def build_bundle(self, metrics: dict, decision: dict, files: list[str]):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snapshot = self.artifact_dir / f"metrics_snapshot_{stamp}.json"
        snapshot.write_text(json.dumps({"metrics": metrics, "decision": decision}, indent=2), encoding="utf-8")
        all_files = [str(snapshot)] + [f for f in files if f]
        bundle = self.artifact_dir / f"ai_perf_agent_artifacts_{stamp}.zip"
        zip_files(all_files, str(bundle))
        return {
            "bundle": str(bundle),
            "files": all_files,
            "metrics_snapshot": str(snapshot),
        }

    def record_issue_key(self, snapshot_path: str, issue_key: str):
        snapshot = Path(snapshot_path)
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
        payload["issue_key"] = issue_key
        snapshot.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.enforce_retention()

    def enforce_retention(self, now: float | None = None) -> list[Path]:
        if not self.retention_enabled:
            return []
        current_time = time.time() if now is None else now
        cutoff = current_time - self.max_age_days * 86400 if self.max_age_days else None
        protected = {"anomaly_state.json", "incident_registry.json"}
        candidates = []
        for path in self.artifact_dir.rglob("*"):
            if not path.is_file() or path.name in protected:
                continue
            try:
                candidates.append((path.stat().st_mtime, path))
            except OSError:
                continue

        removed = []
        retained = []
        for modified, path in candidates:
            if cutoff is not None and modified < cutoff:
                if self._remove(path):
                    removed.append(path)
            else:
                retained.append((modified, path))

        retained.sort(key=lambda item: item[0], reverse=True)
        for _, path in retained[self.max_files:]:
            if self._remove(path):
                removed.append(path)
        if removed:
            logger.info("Artifact retention removed %s file(s)", len(removed))
        return removed

    @staticmethod
    def _remove(path: Path) -> bool:
        try:
            path.unlink()
            return True
        except OSError as exc:
            logger.warning("Could not remove expired artifact %s: %s", path, exc)
            return False

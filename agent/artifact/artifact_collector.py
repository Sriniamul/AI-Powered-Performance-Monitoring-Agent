from datetime import datetime, timezone
from pathlib import Path
import json

from agent.artifact.compressor import zip_files


class ArtifactCollector:
    def __init__(self, config: dict):
        self.artifact_dir = Path(config.get("agent", {}).get("artifact_dir", "artifacts"))
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

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

import logging
import os

from agent.artifact.artifact_collector import ArtifactCollector
from agent.utils.logger import configure_logging


def test_artifact_retention_enforces_age_count_and_protects_state(tmp_path):
    collector = ArtifactCollector({
        "agent": {"artifact_dir": str(tmp_path)},
        "artifact_retention": {"enabled": True, "max_age_days": 1, "max_files": 2},
    })
    old = tmp_path / "old.zip"
    oldest_retained = tmp_path / "first.json"
    newer = tmp_path / "second.json"
    newest = tmp_path / "third.json"
    protected = tmp_path / "anomaly_state.json"
    for path in (old, oldest_retained, newer, newest, protected):
        path.write_text("data", encoding="utf-8")
    os.utime(old, (0, 0))
    os.utime(protected, (0, 0))
    os.utime(oldest_retained, (99997, 99997))
    os.utime(newer, (99998, 99998))
    os.utime(newest, (99999, 99999))

    removed = collector.enforce_retention(now=100000)

    assert old in removed
    assert oldest_retained in removed
    assert newer.exists() and newest.exists()
    assert protected.exists()


def test_log_file_rotates_at_configured_size(tmp_path):
    configure_logging({
        "logging": {
            "directory": str(tmp_path), "max_bytes": 1024,
            "backup_count": 2, "level": "INFO",
        }
    }, "rotation-test")
    try:
        logger = logging.getLogger("rotation-test")
        for _ in range(20):
            logger.info("x" * 200)
        for handler in logging.getLogger().handlers:
            handler.flush()

        assert (tmp_path / "rotation-test.log").exists()
        assert (tmp_path / "rotation-test.log.1").exists()
    finally:
        root = logging.getLogger()
        for handler in list(root.handlers):
            if getattr(handler, "_ai_perf_rotating_file", False):
                root.removeHandler(handler)
                handler.close()

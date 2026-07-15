from agent.incident_deduplicator import IncidentDeduplicator


def config(tmp_path, cooldown=3600):
    return {
        "agent": {"artifact_dir": str(tmp_path)},
        "incidents": {
            "deduplication_enabled": True,
            "cooldown_seconds": cooldown,
            "state_path": str(tmp_path / "incident_registry.json"),
        },
    }


def test_duplicate_is_suppressed_after_restart(tmp_path):
    first_process = IncidentDeduplicator(config(tmp_path))
    first_process.record("payment-api", ["memory_pressure", "resource_contention"], "PERF-42", now=1000)

    restarted_process = IncidentDeduplicator(config(tmp_path))
    duplicate = restarted_process.find_duplicate(
        "payment-api", ["resource_contention", "memory_pressure"], now=1200
    )

    assert duplicate["issue_key"] == "PERF-42"


def test_incident_is_allowed_after_cooldown(tmp_path):
    subject = IncidentDeduplicator(config(tmp_path, cooldown=60))
    subject.record("payment-api", ["cpu_behavior_anomaly"], "PERF-7", now=1000)

    assert subject.find_duplicate("payment-api", ["cpu_behavior_anomaly"], now=1059)
    assert subject.find_duplicate("payment-api", ["cpu_behavior_anomaly"], now=1060) is None


def test_different_service_or_anomaly_type_is_not_suppressed(tmp_path):
    subject = IncidentDeduplicator(config(tmp_path))
    subject.record("payment-api", ["memory_pressure"], "PERF-9", now=1000)

    assert subject.find_duplicate("orders-api", ["memory_pressure"], now=1100) is None
    assert subject.find_duplicate("payment-api", ["database_bottleneck"], now=1100) is None

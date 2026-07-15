import json

from agent.dashboard import describe_cause, describe_process_attribution, load_issues


def test_load_issues_returns_newest_incidents(tmp_path):
    for stamp, severity in [("20260101T010101Z", "high"), ("20260102T010101Z", "critical")]:
        payload = {
            "issue_key": f"PERF-{stamp[-2:]}",
            "metrics": {"timestamp": stamp, "service_name": "api", "environment": "test", "machine_name": "host-1", "cpu_percent": 91},
            "decision": {"should_act": True, "severity": severity, "reason": "cpu_percent_above_80"},
        }
        (tmp_path / f"metrics_snapshot_{stamp}.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "metrics_snapshot_bad.json").write_text("not json", encoding="utf-8")

    issues = load_issues(tmp_path)

    assert [issue["severity"] for issue in issues] == ["critical", "high"]
    assert issues[0]["environment"] == "test"
    assert issues[0]["machine_name"] == "host-1"
    assert issues[0]["incident_id"] == "PERF-1Z"
    assert "CPU utilization reached 91.0%" in issues[0]["cause"]


def test_load_issues_honors_limit(tmp_path):
    for number in range(3):
        payload = {"metrics": {"timestamp": str(number)}, "decision": {"should_act": True}}
        (tmp_path / f"metrics_snapshot_{number}.json").write_text(json.dumps(payload), encoding="utf-8")

    assert len(load_issues(tmp_path, limit=2)) == 2


def test_load_issues_excludes_legacy_demo_environment(tmp_path):
    payload = {
        "metrics": {"timestamp": "now", "environment": "demo"},
        "decision": {"should_act": True, "severity": "high"},
    }
    (tmp_path / "metrics_snapshot_demo.json").write_text(json.dumps(payload), encoding="utf-8")

    assert load_issues(tmp_path) == []


def test_describe_combined_resource_cause():
    cause = describe_cause(
        {"cpu_percent": 92, "memory_percent": 88},
        {"reason": "cpu_percent_above_80,memory_percent_above_80"},
    )

    assert "simultaneous compute saturation and memory pressure" in cause


def test_process_attribution_is_cautious_and_specific():
    note = describe_process_attribution(
        {"top_memory_process": {"name": "java.exe", "pid": 42, "memory_percent": 31.5}},
        cpu_high=False,
        memory_high=True,
    )

    assert note == "Likely contributing process at sampling time: java.exe (PID 42), using 31.5% memory."

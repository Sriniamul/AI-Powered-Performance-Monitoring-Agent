from agent.jira.jira_payload_builder import build_issue_payload


def test_payload_contains_project_and_summary(monkeypatch):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "PERF")
    payload = build_issue_payload(
        {"jira": {"project_key_env": "JIRA_PROJECT_KEY", "default_issue_type": "Bug"}},
        {"service_name": "svc", "environment": "demo", "timestamp": "now", "cpu_percent": 90, "memory_percent": 10},
        {"severity": "high", "reason": "cpu", "capture_heap_dump": False, "capture_thread_dump": True},
        {"summary": "High CPU", "recommendation": "Check thread dump"},
    )
    assert payload["fields"]["project"]["key"] == "PERF"
    assert "AI Alert" in payload["fields"]["summary"]


def test_payload_includes_suggested_fix_and_approval_guardrail():
    payload = build_issue_payload(
        {"jira": {"default_project_key": "PERF", "default_issue_type": "Bug"}},
        {"service_name": "svc", "environment": "prod", "timestamp": "now"},
        {"severity": "high", "reason": "database_bottleneck"},
        {"summary": "Pool saturation", "recommendation": "Validate capacity.",
         "proposed_fixes": [{"action": "Increase connection pool", "risk": "medium",
                             "when": "Database has spare capacity."}]},
    )
    text = payload["fields"]["description"]["content"][0]["content"][0]["text"]
    assert "Increase connection pool" in text
    assert "operator approval required" in text

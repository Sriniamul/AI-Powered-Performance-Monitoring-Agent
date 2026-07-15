from agent.rca.rca_engine import RcaEngine


def test_database_and_traffic_incident_proposes_contextual_fixes():
    insights = RcaEngine().generate({}, {
        "anomaly_types": ["database_bottleneck", "sudden_traffic_spike"],
        "evidence": {"db_pool_wait_ms": {"value": 80, "baseline": 10}},
    }, {})
    fixes = {fix["action"]: fix for fix in insights["proposed_fixes"]}
    assert "Increase connection pool" in fixes
    assert "Scale Kubernetes replicas" in fixes
    assert all(fix["automatic"] is False for fix in fixes.values())


def test_memory_leak_preserves_dump_before_restart():
    insights = RcaEngine().generate({}, {"anomaly_types": ["memory_leak"]}, {})
    restart = next(fix for fix in insights["proposed_fixes"] if fix["action"] == "Restart unhealthy pod")
    assert "heap dump" in restart["when"]

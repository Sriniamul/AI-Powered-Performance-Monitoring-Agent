from agent.anomaly.anomaly_detector import HybridAnomalyDetector


def detector(**overrides):
    config = {"mode": "adaptive", "min_samples": 5, "persistence": 1,
              "z_threshold": 3, "min_relative_change": .2}
    config.update(overrides)
    return HybridAnomalyDetector({"anomaly": config})


def test_learns_service_baseline_then_detects_latency_degradation():
    subject = detector()
    for value in (100, 101, 99, 100, 102):
        assert not subject.detect({"response_time_p95_ms": value}).is_anomaly
    result = subject.detect({"response_time_p95_ms": 180})
    assert result.is_anomaly
    assert "response_time_degradation" in result.anomaly_types
    assert result.evidence["response_time_p95_ms"]["baseline"] == 100


def test_classifies_database_and_traffic_signals():
    subject = detector()
    for _ in range(5):
        subject.detect({"db_pool_wait_ms": 10, "requests_per_second": 100})
    result = subject.detect({"db_pool_wait_ms": 60, "requests_per_second": 500})
    assert set(result.anomaly_types) == {"database_bottleneck", "sudden_traffic_spike"}


def test_static_limits_are_disabled_in_adaptive_mode():
    subject = HybridAnomalyDetector({"thresholds": {"cpu_percent": 10},
                                     "anomaly": {"mode": "adaptive", "min_samples": 30}})
    assert not subject.detect({"cpu_percent": 50}).is_anomaly


def test_deadlock_is_immediately_actionable():
    result = detector().detect({"jvm_deadlock_detected": True})
    assert result.is_anomaly
    assert result.anomaly_types == ("thread_starvation",)


def test_persisted_baseline_is_restored_after_restart(tmp_path):
    state_path = tmp_path / "anomaly_state.json"
    config = {
        "anomaly": {
            "mode": "adaptive", "min_samples": 5, "persistence": 1,
            "z_threshold": 3, "min_relative_change": .2,
            "persist_state": True, "state_path": str(state_path),
        }
    }
    first_process = HybridAnomalyDetector(config)
    for value in (100, 101, 99, 100, 102):
        first_process.detect({"response_time_p95_ms": value})

    restarted_process = HybridAnomalyDetector(config)
    result = restarted_process.detect({"response_time_p95_ms": 180})

    assert result.is_anomaly
    assert result.evidence["response_time_p95_ms"]["baseline"] == 100

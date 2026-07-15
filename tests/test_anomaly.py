from agent.anomaly.anomaly_detector import HybridAnomalyDetector


def test_rule_based_cpu_anomaly():
    cfg = {"thresholds": {"cpu_percent": 10, "memory_percent": 90}, "anomaly": {"min_samples": 10}}
    detector = HybridAnomalyDetector(cfg)
    result = detector.detect({"cpu_percent": 50, "memory_percent": 20})
    assert result.is_anomaly is True
    assert "cpu_percent" in result.reason

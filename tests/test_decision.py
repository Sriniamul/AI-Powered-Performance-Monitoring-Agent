from agent.decision.decision_engine import DecisionEngine
from agent.anomaly.anomaly_detector import AnomalyResult


def test_decision_for_memory_anomaly():
    cfg = {"thresholds": {"cpu_percent": 80, "memory_percent": 80}}
    engine = DecisionEngine(cfg)
    anomaly = AnomalyResult(True, 1.0, "memory_percent_above_80", {"memory_percent": 85})
    decision = engine.evaluate({"cpu_percent": 10, "memory_percent": 85}, anomaly)
    assert decision.should_act is True
    assert decision.capture_heap_dump is True
    assert decision.capture_thread_dump is False

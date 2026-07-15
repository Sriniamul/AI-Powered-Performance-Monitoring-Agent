from dataclasses import dataclass


@dataclass
class Decision:
    should_act: bool
    severity: str
    reason: str
    capture_heap_dump: bool
    capture_thread_dump: bool

    def to_dict(self):
        return {
            "should_act": self.should_act,
            "severity": self.severity,
            "reason": self.reason,
            "capture_heap_dump": self.capture_heap_dump,
            "capture_thread_dump": self.capture_thread_dump,
        }


class DecisionEngine:
    def __init__(self, config: dict):
        self.config = config

    def evaluate(self, metrics: dict, anomaly_result):
        if not anomaly_result.is_anomaly:
            return Decision(False, "none", anomaly_result.reason, False, False)

        mem = float(metrics.get("memory_percent") or 0)
        cpu = float(metrics.get("cpu_percent") or 0)

        capture_heap = mem >= float(self.config.get("thresholds", {}).get("memory_percent", 80))
        capture_thread = cpu >= float(self.config.get("thresholds", {}).get("cpu_percent", 80))
        if not capture_heap and not capture_thread:
            capture_heap = True
            capture_thread = True

        severity = "critical" if cpu >= 90 or mem >= 90 else "high"
        return Decision(True, severity, anomaly_result.reason, capture_heap, capture_thread)

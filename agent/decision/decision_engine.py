from dataclasses import dataclass, field


@dataclass
class Decision:
    should_act: bool
    severity: str
    reason: str
    capture_heap_dump: bool
    capture_thread_dump: bool
    anomaly_types: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "should_act": self.should_act,
            "severity": self.severity,
            "reason": self.reason,
            "capture_heap_dump": self.capture_heap_dump,
            "capture_thread_dump": self.capture_thread_dump,
            "anomaly_types": self.anomaly_types,
            "evidence": self.evidence,
        }


class DecisionEngine:
    def __init__(self, config: dict):
        self.config = config

    def evaluate(self, metrics: dict, anomaly_result):
        if not anomaly_result.is_anomaly:
            return Decision(False, "none", anomaly_result.reason, False, False)

        types = set(getattr(anomaly_result, "anomaly_types", ()))
        # Accept incidents produced by older detector/model payloads during upgrades.
        if not types:
            reason = anomaly_result.reason
            if "memory" in reason or "heap" in reason:
                types.add("memory_pressure")
            if "cpu" in reason:
                types.add("resource_contention")
        capture_heap = bool(types & {"memory_leak", "memory_pressure", "jvm_gc_issue"})
        capture_thread = bool(types & {"thread_starvation", "resource_contention", "response_time_degradation", "database_bottleneck"})
        # Unknown model anomalies capture both so RCA is not deprived of evidence.
        if not types or types == {"behavioral_anomaly"}:
            capture_heap = capture_thread = True
        severity = "critical" if len(types) >= 2 or anomaly_result.score >= 8 else "high"
        return Decision(True, severity, anomaly_result.reason, capture_heap, capture_thread,
                        sorted(types), getattr(anomaly_result, "evidence", None) or {})

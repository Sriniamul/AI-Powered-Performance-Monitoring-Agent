from collections import deque
from dataclasses import dataclass
from typing import Dict, List

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover
    IsolationForest = None


@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    reason: str
    features: Dict

    def to_dict(self):
        return {
            "is_anomaly": self.is_anomaly,
            "score": self.score,
            "reason": self.reason,
            "features": self.features,
        }


class HybridAnomalyDetector:
    """Combines threshold checks with an optional Isolation Forest model."""

    def __init__(self, config: dict):
        self.config = config
        anomaly_cfg = config.get("anomaly", {})
        self.min_samples = int(anomaly_cfg.get("min_samples", 10))
        self.contamination = float(anomaly_cfg.get("contamination", 0.15))
        self.history: deque[List[float]] = deque(maxlen=200)
        self.model = IsolationForest(contamination=self.contamination, random_state=42) if np is not None and IsolationForest else None

    def detect(self, metrics: Dict) -> AnomalyResult:
        cpu = float(metrics.get("cpu_percent") or 0)
        mem = float(metrics.get("memory_percent") or 0)
        vector = [cpu, mem]
        self.history.append(vector)

        rule_result = self._rule_check(cpu, mem)
        if rule_result.is_anomaly:
            return rule_result

        if self.model is None or len(self.history) < self.min_samples:
            return AnomalyResult(False, 0.0, "insufficient_samples_or_model_unavailable", {"cpu_percent": cpu, "memory_percent": mem})

        X = np.array(self.history)
        self.model.fit(X)
        pred = int(self.model.predict([vector])[0])
        score = float(self.model.decision_function([vector])[0])
        is_anomaly = pred == -1
        reason = "isolation_forest_anomaly" if is_anomaly else "normal"
        return AnomalyResult(is_anomaly, score, reason, {"cpu_percent": cpu, "memory_percent": mem})

    def _rule_check(self, cpu: float, mem: float) -> AnomalyResult:
        thresholds = self.config.get("thresholds", {})
        cpu_threshold = float(thresholds.get("cpu_percent", 80))
        mem_threshold = float(thresholds.get("memory_percent", 80))
        reasons = []
        if cpu >= cpu_threshold:
            reasons.append(f"cpu_percent_above_{cpu_threshold}")
        if mem >= mem_threshold:
            reasons.append(f"memory_percent_above_{mem_threshold}")
        return AnomalyResult(bool(reasons), 1.0 if reasons else 0.0, ",".join(reasons) if reasons else "normal", {"cpu_percent": cpu, "memory_percent": mem})

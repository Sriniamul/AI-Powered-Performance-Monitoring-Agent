"""Online, service-specific performance baselining and anomaly classification."""

from collections import defaultdict, deque
from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Dict


@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    reason: str
    features: Dict
    anomaly_types: tuple[str, ...] = ()
    evidence: Dict | None = None

    def to_dict(self):
        return {
            "is_anomaly": self.is_anomaly, "score": self.score, "reason": self.reason,
            "features": self.features, "anomaly_types": list(self.anomaly_types),
            "evidence": self.evidence or {},
        }


# Direction is deliberately explicit: a drop in free memory is bad, while a drop in
# latency is not. Additional application/OpenTelemetry metrics can be passed directly.
SIGNALS = {
    "cpu_percent": "high", "memory_percent": "high", "disk_percent": "high",
    "network_connections": "high", "network_received_mb_s": "high",
    "request_rate": "high", "requests_per_second": "high",
    "response_time_ms": "high", "response_time_p95_ms": "high", "response_time_p99_ms": "high",
    "error_rate": "high", "db_latency_ms": "high", "db_pool_wait_ms": "high",
    "db_active_connections": "high", "db_pool_pending": "high",
    "jvm_heap_percent": "high", "jvm_thread_count": "high",
    "jvm_gc_time_rate": "high", "jvm_full_gc_rate": "high",
    "process_count": "high", "context_switches_per_second": "high",
}

COUNTERS = {
    "jvm_gc_time_seconds": "jvm_gc_time_rate",
    "jvm_full_gc_count": "jvm_full_gc_rate",
}


class HybridAnomalyDetector:
    """Learns rolling normal behavior and explains multi-signal deviations.

    The old class name remains as a compatibility alias for callers. Static limits
    are only evaluated when ``anomaly.static_safety_limits`` is explicitly enabled.
    """

    def __init__(self, config: dict):
        self.config = config
        cfg = config.get("anomaly", {})
        self.min_samples = int(cfg.get("min_samples", 30))
        self.window_size = int(cfg.get("window_size", 288))
        self.z_threshold = float(cfg.get("z_threshold", 4.0))
        self.min_relative_change = float(cfg.get("min_relative_change", 0.20))
        self.persistence = max(1, int(cfg.get("persistence", 2)))
        self.static_safety_limits = bool(cfg.get("static_safety_limits", cfg.get("mode") != "adaptive"))
        self.history = defaultdict(lambda: deque(maxlen=self.window_size))
        self.previous_counters = {}
        self.consecutive = defaultdict(int)

    def detect(self, metrics: Dict) -> AnomalyResult:
        values = self._features(metrics)
        deviations = {}
        for name, value in values.items():
            history = self.history[name]
            if len(history) >= self.min_samples:
                center = median(history)
                mad = median(abs(point - center) for point in history)
                # MAD is robust to incidents; a small relative floor handles flat baselines.
                scale = max(1.4826 * mad, abs(center) * 0.02, 0.01)
                z_score = (value - center) / scale
                relative = (value - center) / max(abs(center), 1.0)
                anomalous = z_score >= self.z_threshold and relative >= self.min_relative_change
                self.consecutive[name] = self.consecutive[name] + 1 if anomalous else 0
                if self.consecutive[name] >= self.persistence:
                    deviations[name] = {
                        "value": round(value, 4), "baseline": round(center, 4),
                        "robust_z_score": round(z_score, 2), "relative_change": round(relative, 3),
                    }
            history.append(value)

        # Leaks are gradual and may never create a single large z-score. Detect a
        # sustained rise across the recent learned window as a distinct pattern.
        for name in ("memory_percent", "jvm_heap_percent"):
            history = self.history[name]
            trend_points = min(10, len(history))
            if trend_points >= max(6, self.min_samples // 3):
                recent = list(history)[-trend_points:]
                rises = sum(b > a for a, b in zip(recent, recent[1:]))
                growth = recent[-1] - recent[0]
                if rises >= len(recent) - 2 and growth >= max(3.0, abs(recent[0]) * self.min_relative_change):
                    deviations[name] = {"value": recent[-1], "baseline": recent[0],
                                        "relative_change": round(growth / max(abs(recent[0]), 1), 3),
                                        "pattern": "sustained_growth"}

        if metrics.get("jvm_deadlock_detected"):
            deviations["jvm_deadlock_detected"] = {"value": True, "pattern": "deadlock"}

        if self.static_safety_limits:
            deviations.update(self._static_limit_evidence(metrics))

        types = self._classify(deviations, metrics)
        if not deviations:
            learned = min((len(v) for v in self.history.values()), default=0)
            reason = "learning_baseline" if learned < self.min_samples else "normal_for_learned_baseline"
            return AnomalyResult(False, 0.0, reason, values, (), {})

        score = max(float(item.get("robust_z_score", self.z_threshold)) for item in deviations.values())
        reason = ",".join(types) if types else "behavioral_anomaly"
        if any(item.get("source") == "safety_limit" for item in deviations.values()):
            reason += ":" + ",".join(sorted(deviations))
        return AnomalyResult(True, score, reason, values, tuple(types or ["behavioral_anomaly"]), deviations)

    def _features(self, metrics):
        result = {}
        for name in SIGNALS:
            value = metrics.get(name)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value)):
                result[name] = float(value)
        for counter, rate_name in COUNTERS.items():
            value = metrics.get(counter)
            if isinstance(value, (int, float)):
                previous = self.previous_counters.get(counter)
                if previous is not None:
                    result[rate_name] = max(0.0, float(value) - previous)
                self.previous_counters[counter] = float(value)
        return result

    def _static_limit_evidence(self, metrics):
        evidence = {}
        for name, limit in self.config.get("thresholds", {}).items():
            value = metrics.get(name)
            if isinstance(value, (int, float)) and float(value) >= float(limit):
                evidence[name] = {"value": value, "safety_limit": limit, "source": "safety_limit"}
        return evidence

    @staticmethod
    def _classify(d, metrics):
        keys = set(d)
        types = []
        if "memory_percent" in keys or "jvm_heap_percent" in keys:
            types.append("memory_leak" if "jvm_heap_percent" in keys or "jvm_full_gc_rate" in keys else "memory_pressure")
        if keys & {"response_time_ms", "response_time_p95_ms", "response_time_p99_ms"}:
            types.append("response_time_degradation")
        if "jvm_thread_count" in keys or "jvm_deadlock_detected" in keys:
            types.append("thread_starvation")
        if keys & {"db_latency_ms", "db_pool_wait_ms", "db_active_connections", "db_pool_pending"}:
            types.append("database_bottleneck")
        if keys & {"jvm_gc_time_rate", "jvm_full_gc_rate"}:
            types.append("jvm_gc_issue")
        if keys & {"request_rate", "requests_per_second", "network_received_mb_s"}:
            types.append("sudden_traffic_spike")
        if ("cpu_percent" in keys and (keys & {"jvm_thread_count", "context_switches_per_second", "process_count"})):
            types.append("resource_contention")
        if not types and "cpu_percent" in keys:
            types.append("cpu_behavior_anomaly")
        return types


AdaptiveAnomalyDetector = HybridAnomalyDetector

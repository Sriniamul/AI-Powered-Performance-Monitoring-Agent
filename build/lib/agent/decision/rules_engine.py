def is_memory_pressure(metrics: dict, threshold: float = 80) -> bool:
    return float(metrics.get("memory_percent") or 0) >= threshold


def is_cpu_pressure(metrics: dict, threshold: float = 80) -> bool:
    return float(metrics.get("cpu_percent") or 0) >= threshold

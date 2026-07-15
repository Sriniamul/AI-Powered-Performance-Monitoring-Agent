def build_feature_vector(metrics: dict):
    return [float(metrics.get("cpu_percent") or 0), float(metrics.get("memory_percent") or 0)]

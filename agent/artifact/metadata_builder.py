def build_metadata(metrics: dict, decision: dict):
    return {
        "service_name": metrics.get("service_name"),
        "environment": metrics.get("environment"),
        "timestamp": metrics.get("timestamp"),
        "severity": decision.get("severity"),
        "reason": decision.get("reason"),
    }

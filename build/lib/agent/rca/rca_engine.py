class RcaEngine:
    def generate(self, metrics: dict, decision: dict, artifacts: dict):
        cpu = float(metrics.get("cpu_percent") or 0)
        mem = float(metrics.get("memory_percent") or 0)
        reason = decision.get("reason", "unknown")

        if mem >= 80 and cpu >= 80:
            summary = "High memory and CPU signals were observed together. Possible GC pressure, memory leak, or hot-loop behavior."
            recommendation = "Review heap dump dominator tree, inspect thread dump for hot threads, and check recent deployment changes."
        elif mem >= 80:
            summary = "High memory signal detected. Possible memory leak or retention growth."
            recommendation = "Open heap dump in Eclipse MAT or VisualVM and inspect retained objects and suspect leak reports."
        elif cpu >= 80:
            summary = "High CPU signal detected. Possible hot thread, thread contention, or compute-heavy loop."
            recommendation = "Inspect thread dump and correlate hot stacks with request traces or recent code changes."
        else:
            summary = f"Anomaly detected by model or rule engine. Reason: {reason}."
            recommendation = "Review attached metrics snapshot and logs for correlation."

        return {"summary": summary, "recommendation": recommendation, "artifact_bundle": artifacts.get("bundle")}

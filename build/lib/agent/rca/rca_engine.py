class RcaEngine:
    """Creates a deterministic, evidence-backed RCA before optional LLM enrichment."""

    GUIDANCE = {
        "memory_leak": ("Sustained heap or memory growth indicates retained objects or a leak.",
                        "Inspect the heap dominator tree and compare retained-object growth."),
        "memory_pressure": ("Memory usage departed materially from its learned baseline.",
                            "Inspect allocation pressure, paging, and the largest resident process."),
        "response_time_degradation": ("Request latency degraded relative to normal service behavior.",
                                      "Correlate slow trace spans with downstream and resource evidence."),
        "thread_starvation": ("Thread growth or a deadlock signal suggests starvation or blocked workers.",
                              "Inspect thread states, lock owners, pool queues, and blocked stack traces."),
        "database_bottleneck": ("Database latency, pool waits, or connection demand departed from baseline.",
                                "Inspect slow queries, pool saturation, lock waits, and database trace spans."),
        "jvm_gc_issue": ("GC time or full-GC frequency increased abnormally.",
                         "Correlate GC pauses with heap growth and request-latency intervals."),
        "sudden_traffic_spike": ("Traffic volume rose abruptly above its learned baseline.",
                                 "Validate demand, rate limiting, autoscaling, and downstream capacity."),
        "resource_contention": ("CPU and concurrency signals indicate possible resource contention.",
                                "Inspect hot threads, context switches, locks, and CPU throttling."),
        "cpu_behavior_anomaly": ("CPU behavior departed materially from its learned baseline.",
                                 "Inspect the top process and hot thread stacks during the event."),
    }

    FIXES = {
        "database_bottleneck": [
            ("Increase connection pool", "Pool wait or pending demand is elevated; confirm the database has spare connection capacity.", "medium"),
        ],
        "sudden_traffic_spike": [
            ("Scale Kubernetes replicas", "Request load exceeds the learned baseline and pods have available cluster capacity.", "low"),
        ],
        "jvm_gc_issue": [
            ("Tune JVM heap", "Heap/GC evidence confirms allocation pressure; validate container memory limits before increasing -Xmx.", "medium"),
        ],
        "memory_leak": [
            ("Restart unhealthy pod", "Use only as temporary containment after preserving the heap dump; restart one pod at a time.", "medium"),
            ("Tune JVM heap", "Only when the dump shows legitimate live-set growth rather than a leak.", "medium"),
        ],
        "memory_pressure": [
            ("Restart unhealthy pod", "Use as temporary containment when one pod is unhealthy and healthy replicas can carry traffic.", "medium"),
            ("Clear cache", "Use only when cache growth is confirmed and eviction is safe; expect a temporary cold-cache latency increase.", "medium"),
        ],
        "response_time_degradation": [
            ("Rollback deployment", "Latency degradation correlates with a recent deployment and rollback health checks are defined.", "high"),
            ("Clear cache", "Trace/log evidence identifies stale, corrupt, or unbounded cache behavior.", "medium"),
        ],
        "thread_starvation": [
            ("Restart unhealthy pod", "A deadlocked or unrecoverable pod is isolated; preserve the thread dump first.", "medium"),
            ("Scale Kubernetes replicas", "Worker saturation is load-driven rather than a deadlock or downstream outage.", "low"),
        ],
        "resource_contention": [
            ("Scale Kubernetes replicas", "Contention is caused by sustained load and requests are horizontally scalable.", "low"),
        ],
        "cpu_behavior_anomaly": [
            ("Rollback deployment", "Hot-stack evidence points to a recently deployed code path.", "high"),
        ],
    }

    def generate(self, metrics: dict, decision: dict, artifacts: dict):
        types = decision.get("anomaly_types") or ["behavioral_anomaly"]
        findings, actions = [], []
        for anomaly_type in types:
            finding, action = self.GUIDANCE.get(
                anomaly_type,
                (f"A learned behavioral anomaly was detected ({anomaly_type}).",
                 "Review the metrics, logs, dumps, and traces from the same event window."),
            )
            findings.append(finding)
            actions.append(action)
        evidence = decision.get("evidence", {})
        correlation = "; ".join(
            f"{name}={value.get('value')} (normal={value.get('baseline', 'n/a')})"
            for name, value in evidence.items()
        )
        proposed_fixes = []
        seen = set()
        for anomaly_type in types:
            for title, condition, risk in self.FIXES.get(anomaly_type, []):
                if title not in seen:
                    proposed_fixes.append({"action": title, "when": condition, "risk": risk,
                                           "automatic": False})
                    seen.add(title)
        return {
            "summary": " ".join(findings),
            "recommendation": " ".join(dict.fromkeys(actions)),
            "correlation": correlation or "See the incident metrics snapshot for correlated evidence.",
            "likely_root_causes": types,
            "proposed_fixes": proposed_fixes,
            "artifact_bundle": artifacts.get("bundle"),
        }

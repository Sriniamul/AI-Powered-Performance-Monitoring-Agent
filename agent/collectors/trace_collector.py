"""Best-effort analysis of newline-delimited OpenTelemetry/trace JSON exports."""

import json
from pathlib import Path


class TraceCollector:
    def __init__(self, config: dict):
        self.paths = [Path(path) for path in config.get("paths", [])]
        self.max_spans = int(config.get("max_spans", 1000))
        self.collected_files = []

    def collect(self):
        durations, db_durations, errors = [], [], 0
        self.collected_files = []
        for path in self.paths:
            if not path.is_file():
                continue
            self.collected_files.append(str(path))
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-self.max_spans:]:
                try:
                    span = json.loads(line)
                except (ValueError, TypeError):
                    continue
                duration = span.get("duration_ms")
                if isinstance(duration, (int, float)):
                    durations.append(float(duration))
                    attrs = span.get("attributes") or {}
                    if span.get("span_kind") == "CLIENT" and (attrs.get("db.system") or attrs.get("db.operation")):
                        db_durations.append(float(duration))
                status = str(span.get("status", span.get("status_code", ""))).upper()
                errors += status in {"ERROR", "STATUS_CODE_ERROR"}
        result = {"trace_span_count": len(durations), "trace_error_count": errors}
        if durations:
            ordered = sorted(durations)
            result["response_time_p95_ms"] = _percentile(ordered, .95)
            result["trace_error_rate"] = round(errors / len(durations), 4)
        if db_durations:
            result["db_latency_ms"] = _percentile(sorted(db_durations), .95)
        return result


def _percentile(values, percentile):
    return round(values[min(int(len(values) * percentile), len(values) - 1)], 2)

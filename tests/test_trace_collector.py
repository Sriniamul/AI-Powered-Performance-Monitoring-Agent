import json

from agent.collectors.trace_collector import TraceCollector


def test_trace_collector_derives_latency_and_database_signals(tmp_path):
    path = tmp_path / "spans.jsonl"
    spans = [
        {"duration_ms": 20, "status": "OK"},
        {"duration_ms": 200, "status": "ERROR", "span_kind": "CLIENT",
         "attributes": {"db.system": "postgresql"}},
    ]
    path.write_text("\n".join(json.dumps(span) for span in spans), encoding="utf-8")
    collector = TraceCollector({"paths": [str(path)]})
    result = collector.collect()
    assert result["response_time_p95_ms"] == 200
    assert result["db_latency_ms"] == 200
    assert result["trace_error_rate"] == .5
    assert collector.collected_files == [str(path)]

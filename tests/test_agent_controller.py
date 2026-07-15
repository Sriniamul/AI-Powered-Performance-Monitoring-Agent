from unittest.mock import MagicMock

from agent.agent_controller import AgentController
from agent.anomaly.anomaly_detector import AnomalyResult
from agent.decision.decision_engine import Decision


def test_duplicate_returns_before_diagnostics_and_jira():
    controller = AgentController.__new__(AgentController)
    controller.collect_metrics = MagicMock(return_value={"service_name": "payment-api", "cpu_percent": 95})
    controller.detector = MagicMock(return_value=None)
    controller.detector.detect.return_value = AnomalyResult(
        True, 9, "cpu_behavior_anomaly", {}, ("cpu_behavior_anomaly",), {}
    )
    controller.decision_engine = MagicMock()
    controller.decision_engine.evaluate.return_value = Decision(
        True, "critical", "cpu_behavior_anomaly", False, False, ["cpu_behavior_anomaly"], {}
    )
    controller.incident_deduplicator = MagicMock()
    controller.incident_deduplicator.find_duplicate.return_value = {"issue_key": "PERF-42"}
    controller.heap_dump = MagicMock()
    controller.thread_dump = MagicMock()
    controller.log_collector = MagicMock()
    controller.artifacts = MagicMock()
    controller.issue_creator = MagicMock()

    result = controller.run_cycle()

    assert result["status"] == "duplicate_suppressed"
    assert result["issue_key"] == "PERF-42"
    controller.heap_dump.capture.assert_not_called()
    controller.thread_dump.capture.assert_not_called()
    controller.log_collector.collect.assert_not_called()
    controller.artifacts.build_bundle.assert_not_called()
    controller.issue_creator.create_incident.assert_not_called()


def test_discovered_jvm_pid_is_forwarded_to_diagnostics():
    controller = AgentController.__new__(AgentController)
    metrics = {"service_name": "payment-api", "jvm_pid": 4242, "jvm_heap_percent": 95}
    controller.collect_metrics = MagicMock(return_value=metrics)
    controller.detector = MagicMock()
    controller.detector.detect.return_value = AnomalyResult(
        True, 9, "memory_leak,thread_starvation", {},
        ("memory_leak", "thread_starvation"), {},
    )
    controller.decision_engine = MagicMock()
    controller.decision_engine.evaluate.return_value = Decision(
        True, "critical", "memory_leak,thread_starvation", True, True,
        ["memory_leak", "thread_starvation"], {},
    )
    controller.incident_deduplicator = MagicMock()
    controller.incident_deduplicator.find_duplicate.return_value = None
    controller.heap_dump = MagicMock()
    controller.heap_dump.capture.return_value = []
    controller.thread_dump = MagicMock()
    controller.thread_dump.capture.return_value = []
    controller.log_collector = MagicMock()
    controller.log_collector.collect.return_value = []
    controller.trace_collector = MagicMock()
    controller.trace_collector.collected_files = []
    controller.llm_analyzer = MagicMock()
    controller.llm_analyzer.analyze.return_value = {}
    controller.artifacts = MagicMock()
    controller.artifacts.build_bundle.return_value = {
        "bundle": "bundle.zip", "files": [], "metrics_snapshot": "snapshot.json"
    }
    controller.rca = MagicMock()
    controller.rca.generate.return_value = {}
    controller.issue_creator = MagicMock()
    controller.issue_creator.create_incident.return_value = "PERF-42"
    controller.notifier = MagicMock()

    result = controller.run_cycle()

    assert result["status"] == "incident_created"
    controller.heap_dump.capture.assert_called_once_with(4242)
    controller.thread_dump.capture.assert_called_once_with(4242)

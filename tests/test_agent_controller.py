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

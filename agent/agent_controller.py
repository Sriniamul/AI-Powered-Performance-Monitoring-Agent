from datetime import datetime, timezone

from agent.collectors.cpu_collector import CpuCollector
from agent.collectors.memory_collector import MemoryCollector
from agent.collectors.machine_collector import MachineCollector
from agent.collectors.process_collector import ProcessCollector
from agent.collectors.disk_collector import DiskCollector
from agent.collectors.network_collector import NetworkCollector
from agent.collectors.jvm_collector import JvmCollector
from agent.collectors.log_collector import LogCollector
from agent.collectors.trace_collector import TraceCollector
from agent.anomaly.anomaly_detector import HybridAnomalyDetector
from agent.decision.decision_engine import DecisionEngine
from agent.diagnostics.heap_dump import HeapDumpService
from agent.diagnostics.thread_dump import ThreadDumpService
from agent.artifact.artifact_collector import ArtifactCollector
from agent.rca.rca_engine import RcaEngine
from agent.rca.llm_analyzer import LlmIncidentAnalyzer
from agent.jira.jira_client import JiraClient
from agent.jira.issue_creator import JiraIssueCreator
from agent.notification.console_notifier import ConsoleNotifier
from agent.utils.logger import get_logger

logger = get_logger(__name__)


class AgentController:
    """Coordinates metric collection, anomaly detection, diagnostics, artifacts, and JIRA workflow."""

    def __init__(self, config: dict):
        self.config = config
        self.cpu_collector = CpuCollector()
        self.memory_collector = MemoryCollector()
        self.machine_collector = MachineCollector()
        self.process_collector = ProcessCollector()
        self.disk_collector = DiskCollector(config.get("disk", {}).get("path", "."))
        self.network_collector = NetworkCollector()
        self.jvm_collector = JvmCollector(config.get("jvm", {}))
        self.log_collector = LogCollector(config.get("logs", {}))
        self.trace_collector = TraceCollector(config.get("traces", {}))
        self.detector = HybridAnomalyDetector(config)
        self.decision_engine = DecisionEngine(config)
        self.heap_dump = HeapDumpService(config.get("jvm", {}))
        self.thread_dump = ThreadDumpService(config.get("jvm", {}))
        self.artifacts = ArtifactCollector(config)
        self.rca = RcaEngine()
        self.llm_analyzer = LlmIncidentAnalyzer(config)
        self.jira_client = JiraClient(config)
        self.issue_creator = JiraIssueCreator(config, self.jira_client)
        self.notifier = ConsoleNotifier()

    def run_cycle(self):
        timestamp = datetime.now(timezone.utc).isoformat()
        metrics = self.collect_metrics(timestamp)
        logger.info("Metrics collected: %s", metrics)

        anomaly_result = self.detector.detect(metrics)
        decision = self.decision_engine.evaluate(metrics, anomaly_result)

        if not decision.should_act:
            logger.info("No incident action required. reason=%s", decision.reason)
            return {"status": "no_action", "metrics": metrics, "decision": decision.to_dict()}

        logger.warning("Anomaly action triggered: %s", decision.to_dict())
        generated_files = []

        if decision.capture_heap_dump:
            generated_files.extend(self.heap_dump.capture())
        if decision.capture_thread_dump:
            generated_files.extend(self.thread_dump.capture())

        generated_files.extend(self.log_collector.collect())
        generated_files.extend(self.trace_collector.collected_files)
        metrics["llm"] = self.llm_analyzer.analyze(metrics, decision.to_dict())
        artifacts = self.artifacts.build_bundle(metrics=metrics, decision=decision.to_dict(), files=generated_files)
        insights = self.rca.generate(metrics, decision.to_dict(), artifacts)
        issue_key = self.issue_creator.create_incident(metrics, decision.to_dict(), insights, artifacts)
        self.artifacts.record_issue_key(artifacts["metrics_snapshot"], issue_key)
        self.notifier.notify(issue_key, decision.to_dict(), insights)

        return {
            "status": "incident_created",
            "issue_key": issue_key,
            "metrics": metrics,
            "decision": decision.to_dict(),
            "artifacts": artifacts,
        }

    def collect_metrics(self, timestamp: str):
        machine = self.machine_collector.collect()
        metrics = {
            "timestamp": timestamp,
            "service_name": self.config.get("agent", {}).get("service_name", "unknown-service"),
            "environment": machine["os_environment"],
        }
        metrics.update(machine)
        metrics.update(self.cpu_collector.collect())
        metrics.update(self.memory_collector.collect())
        metrics.update(self.process_collector.collect())
        metrics.update(self.disk_collector.collect())
        metrics.update(self.network_collector.collect())
        metrics.update(self.jvm_collector.collect())
        metrics.update(self.trace_collector.collect())
        return metrics

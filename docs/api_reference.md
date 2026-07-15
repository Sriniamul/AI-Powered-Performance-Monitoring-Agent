# API Reference

This project currently exposes Python classes rather than an HTTP API.

## Main classes

- `AgentController`: orchestrates the monitoring cycle.
- `HybridAnomalyDetector`: detects anomalies from CPU and memory metrics.
- `DecisionEngine`: determines diagnostics and severity.
- `HeapDumpService`: captures JVM heap dumps.
- `ThreadDumpService`: captures JVM thread dumps.
- `ArtifactCollector`: packages diagnostic evidence.
- `JiraClient`: creates issues and uploads attachments.

# Architecture

The AI Performance Monitoring Agent uses a modular pipeline:

1. **Collectors** gather CPU, memory, JVM and log data.
2. **Anomaly Detector** uses hybrid rules and optional Isolation Forest detection.
3. **Decision Engine** determines whether to act and which diagnostics to capture.
4. **Diagnostics Services** generate heap and thread dumps when a JVM PID is configured.
5. **Artifact Collector** packages evidence into a ZIP file.
6. **JIRA Integration** creates an issue and attaches the evidence.
7. **RCA Engine** generates a concise insight and next action.

## Safety Guardrails

- Dry-run is enabled by default.
- No real JIRA calls are made unless `DRY_RUN=false`.
- Missing JVM tools do not crash the agent; marker files are created.
- Missing log files are ignored.

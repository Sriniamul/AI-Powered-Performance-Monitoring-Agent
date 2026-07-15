# Architecture

The AI Performance Monitoring Agent uses a modular pipeline:

1. **Collectors** gather CPU, memory, JVM and log data.
2. **Anomaly Detector** uses persisted rolling median/MAD baselines, persistence filtering, and optional static safety limits.
3. **Decision Engine** determines whether to act and which diagnostics to capture.
4. **Incident Deduplicator** suppresses matching service/anomaly incidents during the configured cooldown.
5. **Diagnostics Services** generate heap and thread dumps when a JVM PID is configured.
6. **Artifact Collector** packages evidence into a ZIP file.
7. **JIRA Integration** creates an issue and attaches the evidence.
8. **RCA Engine** generates a concise insight and next action.

## Safety Guardrails

- Dry-run is enabled by default.
- No real JIRA calls are made unless `DRY_RUN=false`.
- Missing JVM tools do not crash the agent; marker files are created.
- Missing log files are ignored.
- Agent and dashboard logs use bounded size-based rotation.
- Artifact retention protects anomaly and incident state while pruning old diagnostics.

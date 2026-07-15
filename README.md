# AI Performance Monitoring Agent

**AI Performance Monitoring Agent** learns each service's normal behavior, detects multi-signal performance anomalies, captures diagnostic evidence, correlates events, and creates a JIRA issue with a likely root cause and artifacts attached.

This repository is designed for hackathons, engineering demos, and enterprise innovation presentations.

---

## Key Capabilities

- CPU and memory monitoring
- JVM process discovery and diagnostics
- Adaptive rolling baselines (robust median/MAD) with persistence filtering
- Classification of memory leaks, latency degradation, thread starvation, database bottlenecks, JVM GC issues, traffic spikes, and resource contention
- Heap dump capture using `jcmd` or `jmap`
- Thread dump capture using `jcmd` or `jstack`
- Application log collection
- Correlated anomaly evidence with observed values and learned baselines
- Artifact packaging into a compressed `.zip`
- JIRA issue creation
- JIRA attachment upload for heap dump, thread dump, logs, and metrics snapshot
- Dry-run mode for safe local demos without JIRA credentials

---

## High-Level Architecture

```text
+--------------------+      +-----------------------+      +-------------------+
| Metrics Collectors | ---> | AI Anomaly Detector   | ---> | Decision Engine   |
| CPU, Memory, JVM   |      | Rules + Isolation     |      | Severity + Policy |
+--------------------+      +-----------------------+      +---------+---------+
                                                                  |
                                                                  v
+--------------------+      +-----------------------+      +-------------------+
| JIRA Integration   | <--- | Artifact Collector    | <--- | Diagnostics       |
| Issue + Attachments|      | logs, dumps, metadata |      | heap/thread dumps |
+--------------------+      +-----------------------+      +-------------------+
```

---

## Repository Structure

```text
ai-perf-agent/
├── agent/                  # Core Python package
│   ├── collectors/          # CPU, memory, JVM, and log collectors
│   ├── anomaly/             # AI and rules-based anomaly detection
│   ├── decision/            # Decision and severity logic
│   ├── diagnostics/         # Heap and thread dump capture
│   ├── artifact/            # Artifact collection and packaging
│   ├── jira/                # JIRA issue and attachment integration
│   ├── rca/                 # RCA insight generation
│   ├── notification/        # Console notifier placeholder
│   └── utils/               # Config and logging helpers
├── configs/                 # YAML configuration files
├── scripts/                 # Demo scripts
├── tests/                   # Unit tests
├── docker/                  # Dockerfile and compose file
├── docs/                    # Architecture and demo guide
├── .github/workflows/       # CI workflow
└── README.md
```

---

## Quick Start

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows PowerShell
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the agent

Copy the example environment file:

```bash
cp .env.example .env
```

For local demo, keep:

```bash
DRY_RUN=true
```

For real JIRA integration, set:

```bash
DRY_RUN=false
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_api_token
JIRA_PROJECT_KEY=PERF
```

### 4. Run the agent in demo mode

```bash
python -m agent.main --config configs/config.yaml --once
```

### 5. Simulate CPU spike

In another terminal:

```bash
python scripts/simulate_cpu_spike.py
```

### 6. Simulate memory pressure

```bash
python scripts/simulate_memory_pressure.py
```

### 7. Open the incident dashboard

Start the local dashboard in another terminal:

```bash
python -m agent.dashboard
```

Then open `http://127.0.0.1:8080`. The dashboard refreshes every five seconds and
shows detected issues with timestamps, environment, service, severity, CPU, and memory details.

---

## JVM Diagnostics

If you provide a JVM PID in `configs/config.yaml`, the agent can attempt to capture:

- Heap dump: `jcmd <pid> GC.heap_dump <file>` or `jmap -dump:live,format=b,file=<file> <pid>`
- Thread dump: `jcmd <pid> Thread.print` or `jstack -l <pid>`

The user running the agent must have permission to inspect the target JVM process.

---

## JIRA Ticket Creation

When an anomaly is detected, the agent can create a JIRA issue with:

- Service name
- Environment
- Severity
- CPU and memory values
- Anomaly reason
- RCA hint
- Artifact ZIP
- Individual files such as thread dump, heap dump, log sample, and metrics snapshot

### Dry-run behavior

When `DRY_RUN=true`, the agent does **not** call JIRA. Instead, it writes a local file under `artifacts/dry_run_jira_issue.json`.

---

## Demo Flow for Hackathon

1. Start the agent in dry-run mode.
2. Run CPU or memory pressure simulator.
3. The agent detects anomaly.
4. The agent captures diagnostics.
5. The agent packages artifacts.
6. The agent creates a dry-run JIRA issue JSON or real JIRA ticket if configured.

---

## Security Notes

- Do not commit `.env` files or API tokens.
- Heap dumps can contain sensitive data.
- Use retention policies for generated artifacts.
- Consider masking logs before upload.
- Validate attachment file size limits in your JIRA instance.

---

## Roadmap

- Kubernetes pod diagnostics
- Prometheus / OpenTelemetry integration
- GenAI RCA summarization
- JIRA deduplication using JQL
- Teams / Slack notification
- Cost and capacity recommendation engine

---

## License

MIT License. See [LICENSE](LICENSE).

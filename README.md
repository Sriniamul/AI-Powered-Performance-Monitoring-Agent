# AI-Powered Performance Monitoring Agent

The **AI-Powered Performance Monitoring Agent** learns a service's normal resource behavior, detects persistent multi-signal anomalies, captures diagnostic evidence, generates root-cause guidance, and creates a JIRA incident with supporting artifacts.

It can run entirely in dry-run mode for local development and demonstrations.

## Capabilities

- Collects machine, CPU, memory, process, disk, network, JVM, log, and trace data
- Learns per-metric rolling baselines using robust median/MAD scoring
- Persists learned baselines across agent restarts
- Filters transient deviations with relative-change and persistence requirements
- Suppresses duplicate incidents during a configurable cooldown period
- Optionally applies static emergency thresholds
- Correlates resource, JVM, database, latency, error, and traffic signals
- Classifies incidents as high or critical severity
- Captures JVM heap and thread dumps when configured and available
- Generates rule-based RCA guidance and optional LLM analysis
- Supports OpenAI and GitHub Copilot SDK analysis providers
- Packages metrics, logs, traces, and diagnostics into ZIP artifacts
- Removes expired artifacts and caps retained artifact file count
- Rotates agent and dashboard logs by size with bounded backups
- Creates JIRA issues and uploads diagnostic attachments
- Provides a live dashboard with incident IDs, metrics, causes, and suggested solutions
- Supports safe local operation without JIRA credentials through dry-run mode

## Architecture

```text
Collectors
  machine | CPU | memory | process | disk | network | JVM | logs | traces
      |
      v
Adaptive Anomaly Detector
  rolling median/MAD | persisted state | relative change | persistence
      |
      v
Decision Engine
  action policy | severity | diagnostic selection
      |
      +--------------------+
      |                    |
      v                    v
Diagnostics            LLM Analyzer
  heap/thread dumps       root cause | solution | confidence
      |                    |
      +----------+---------+
                 v
Artifact Collector and RCA Engine
  metrics snapshot | logs | traces | dumps | ZIP bundle
                 |
                 v
JIRA Integration and Notification
  issue key | attachments | console output
                 |
                 v
Dashboard
  incident ID | detected issue | evidence | cause | suggested solution
```

The controller in `agent/agent_controller.py` coordinates one pass through this pipeline. The long-running entry point in `agent/main.py` invokes it at the configured polling interval.

## Repository Structure

```text
AI-Powered-Performance-Monitoring-Agent/
|-- agent/
|   |-- main.py                 # Monitoring process entry point
|   |-- agent_controller.py     # Pipeline orchestration
|   |-- dashboard.py            # Local dashboard and JSON API
|   |-- collectors/             # Machine, resource, JVM, log, and trace collectors
|   |-- anomaly/                # Adaptive anomaly detection and feature logic
|   |-- decision/               # Incident policy and severity selection
|   |-- diagnostics/            # Heap, thread, and GC diagnostics
|   |-- artifact/               # Snapshot and ZIP artifact generation
|   |-- rca/                    # Rule-based and LLM incident analysis
|   |-- jira/                   # JIRA payload, client, issue, and attachment logic
|   |-- notification/           # Console, email, and Slack notifier modules
|   `-- utils/                  # Configuration, constants, logging, and helpers
|-- configs/
|   |-- config.yaml             # Active agent configuration
|   `-- thresholds.yaml         # Additional threshold configuration
|-- scripts/                    # Agent launcher and workload simulators
|-- tests/                      # Pytest suite
|-- docker/                     # Dockerfile and Docker Compose configuration
|-- docs/                       # Architecture, API, and demo documentation
|-- logs/                       # Runtime and configured application logs
|-- pyproject.toml              # Package metadata and dependencies
|-- requirements.txt            # Runtime and test dependencies
|-- .env.example                # Environment variable template
`-- README.md
```

Generated diagnostic files are written to `artifacts/`, runtime logs to `logs/`, and package builds to `dist/`.

## Requirements

- Python 3.10 or newer
- JDK diagnostic tools (`jcmd`, `jmap`, or `jstack`) only when JVM dump capture is required
- JIRA Cloud credentials only when dry-run mode is disabled
- An OpenAI API key or Copilot credentials only when the corresponding LLM provider is enabled

## Quick Start

### 1. Create and activate a virtual environment

Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install the project

```bash
python -m pip install -e .[test]
```

Alternatively, install the pinned project requirements:

```bash
python -m pip install -r requirements.txt
```

### 3. Create the environment file

Linux or macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Keep `DRY_RUN=true` for local use. The agent then writes the proposed JIRA payload to `artifacts/dry_run_jira_issue.json` and returns the incident ID `DRY-RUN-1` without contacting JIRA.

### 4. Start continuous monitoring

```bash
python -m agent.main --config configs/config.yaml
```

The default adaptive detector needs 30 samples to learn its baseline. With the default five-second polling interval, initial learning takes approximately 2.5 minutes. It then requires two consecutive anomalous samples before creating an incident.

Use `--once` for a collection smoke test:

```bash
python -m agent.main --config configs/config.yaml --once
```

A fresh adaptive detector normally reports `learning_baseline` during a single-cycle run.

### 5. Start the dashboard

In another terminal:

```bash
python -m agent.dashboard
```

Open `http://127.0.0.1:8080`. The dashboard refreshes every five seconds and reads incident snapshots from `artifacts/`.

Useful endpoints:

- Dashboard: `http://127.0.0.1:8080/`
- Incident API: `http://127.0.0.1:8080/api/issues?limit=250`
- Health check: `http://127.0.0.1:8080/health`

The incident table includes the created JIRA or dry-run incident ID. Snapshots created by older versions that do not contain an issue key display `-` in that column.

## Workload Simulators

Run a simulator while continuous monitoring is active and has learned a stable baseline:

```bash
python scripts/simulate_cpu_spike.py
python scripts/simulate_memory_pressure.py
```

The Java memory leak example is located at `scripts/simulate_memory_leak.java`.

## Configuration

The primary configuration file is `configs/config.yaml`.

### Log rotation and artifact retention

```yaml
logging:
  directory: logs
  level: INFO
  max_bytes: 5242880
  backup_count: 5

artifact_retention:
  enabled: true
  max_age_days: 14
  max_files: 500
```

The agent writes `logs/agent.log`, while the dashboard writes `logs/dashboard.log`. When a file reaches `max_bytes`, it is rolled to numbered backups such as `agent.log.1`; only `backup_count` backups are retained.

Artifact retention runs when the controller starts and after a successful incident is recorded. It removes files older than `max_age_days`, then retains only the newest `max_files` files across `artifacts/` and its subdirectories. The persistent `anomaly_state.json` and `incident_registry.json` files are always protected.

### Adaptive anomaly detection

```yaml
anomaly:
  mode: adaptive
  min_samples: 30
  window_size: 288
  z_threshold: 4.0
  min_relative_change: 0.20
  persistence: 2
  static_safety_limits: false
  persist_state: true
  state_path: artifacts/anomaly_state.json

incidents:
  deduplication_enabled: true
  cooldown_seconds: 3600
  state_path: artifacts/incident_registry.json
```

Set `static_safety_limits: true` to evaluate the values under `thresholds` in addition to learned baselines.

The detector writes its rolling history, counter values, and persistence streaks to `anomaly_state.json` after every sample. On restart, it restores that state instead of repeating the initial baseline-learning period.

Incident deduplication uses the configured service name plus the sorted anomaly types as its key. A matching anomaly detected within `cooldown_seconds` returns `duplicate_suppressed` and reuses the existing issue key without running diagnostics, LLM analysis, artifact generation, or JIRA creation again. Different services and different anomaly classifications remain independent. The registry is written only after successful incident creation.

### Logs and traces

Configure application logs under `logs.paths`. Missing files are ignored. Configure newline-delimited JSON span exports under `traces.paths`; the trace collector evaluates duration, status, span kind, and database-system attributes.

### LLM analysis

The `llm` section selects the provider, model, and timeout. Environment variables override provider credentials and model selection:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
LLM_PROVIDER=openai
COPILOT_KEY=
COPILOT_MODEL=gpt-5
```

When analysis is unavailable, incident creation continues with rule-based RCA instead of failing the monitoring cycle.

## JVM Diagnostics

Leave `jvm.pid: null` and `jvm.auto_discover: true` to select a local JVM automatically. The PID collected during each monitoring cycle is passed directly to heap and thread diagnostics. Set `jvm.pid` only when the agent must target a specific JVM.

- Heap dump: `jcmd <pid> GC.heap_dump <file>` or `jmap -dump:live,format=b,file=<file> <pid>`
- Thread dump: `jcmd <pid> Thread.print` or `jstack -l <pid>`

The account running the agent must be allowed to inspect the target JVM. Missing diagnostic tools are handled without crashing the monitoring cycle.

## JIRA Integration

For real JIRA issue creation, set the following values in `.env`:

```dotenv
DRY_RUN=false
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=replace_me
JIRA_PROJECT_KEY=PERF
JIRA_ISSUE_TYPE=Bug
```

For each actionable anomaly, the agent:

1. Collects diagnostics and relevant logs or traces.
2. Generates LLM and rule-based RCA guidance.
3. Writes `artifacts/metrics_snapshot_<timestamp>.json`.
4. Creates `artifacts/ai_perf_agent_artifacts_<timestamp>.zip`.
5. Creates a JIRA issue or dry-run payload.
6. Uploads available attachments when real JIRA integration is enabled.
7. Records the returned issue key in the metrics snapshot for the dashboard.

## Build and Test

Run the test suite:

```bash
python -m pytest -q
```

Build the wheel:

```bash
python -m pip install build
python -m build --wheel
```

The generated wheel is placed under `dist/`.

## Docker

Docker assets are stored under `docker/`:

```bash
docker build -f docker/Dockerfile -t ai-performance-agent .
docker compose -f docker/docker-compose.yml up
```

Review volume mounts, `.env`, JVM access, and artifact retention before using the container against a host workload.

## Security

- Never commit `.env`, API tokens, or credentials.
- Treat heap dumps, thread dumps, traces, and application logs as sensitive data.
- Apply retention and access policies to `artifacts/`.
- Mask secrets and personal data before uploading diagnostic files.
- Review JIRA attachment-size limits before enabling dump uploads.
- Run the agent with only the operating-system permissions it needs.

## Additional Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api_reference.md)
- [Demo guide](docs/demo_guide.md)
- [License](LICENSE)

## License

MIT License. See [LICENSE](LICENSE).

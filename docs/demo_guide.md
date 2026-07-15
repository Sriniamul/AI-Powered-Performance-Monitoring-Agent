# Demo Guide

## Local dry-run demo

```bash
pip install -r requirements.txt
cp .env.example .env
python -m agent.main --config configs/config.yaml --once
```

To force an anomaly quickly, lower the thresholds in `configs/config.yaml`:

```yaml
thresholds:
  cpu_percent: 1
  memory_percent: 1
```

Run again:

```bash
python -m agent.main --config configs/config.yaml --once
```

Expected output:

- `artifacts/dry_run_jira_issue.json`
- `artifacts/ai_perf_agent_artifacts_*.zip`
- `artifacts/metrics_snapshot_*.json`

## JVM demo

1. Compile and run the Java memory leak simulator:

```bash
javac scripts/simulate_memory_leak.java
java -Xmx256m -cp scripts SimulateMemoryLeak
```

2. Find the Java PID:

```bash
jps
```

3. Set PID in `configs/config.yaml`.
4. Run the agent.

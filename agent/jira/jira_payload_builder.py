import os


def build_issue_payload(config: dict, metrics: dict, decision: dict, insights: dict):
    jira_cfg = config.get("jira", {})
    project_key = os.getenv(jira_cfg.get("project_key_env", "JIRA_PROJECT_KEY"), jira_cfg.get("default_project_key", "PERF"))
    issue_type = os.getenv(jira_cfg.get("issue_type_env", "JIRA_ISSUE_TYPE"), jira_cfg.get("default_issue_type", "Bug"))
    labels = jira_cfg.get("labels", [])

    summary = f"AI Alert: {decision.get('severity', 'high').upper()} performance anomaly in {metrics.get('service_name')}"
    description = build_description(metrics, decision, insights)

    return {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
            "labels": labels,
        }
    }


def build_description(metrics: dict, decision: dict, insights: dict) -> str:
    fixes = insights.get("proposed_fixes", [])
    fixes_text = "\n".join(
        f"- {fix.get('action')} [{fix.get('risk', 'unknown')} risk]: {fix.get('when')}"
        for fix in fixes
    ) or "- No automated fix proposed; investigate the attached evidence."
    return (
        "AI Performance Monitoring Agent detected a performance anomaly.\n\n"
        f"Service: {metrics.get('service_name')}\n"
        f"Environment: {metrics.get('environment')}\n"
        f"Timestamp: {metrics.get('timestamp')}\n"
        f"Severity: {decision.get('severity')}\n"
        f"Reason: {decision.get('reason')}\n"
        f"CPU Percent: {metrics.get('cpu_percent')}\n"
        f"Memory Percent: {metrics.get('memory_percent')}\n\n"
        "Actions taken by agent:\n"
        f"- Capture heap dump: {decision.get('capture_heap_dump')}\n"
        f"- Capture thread dump: {decision.get('capture_thread_dump')}\n"
        "- Collect logs and metrics snapshot\n"
        "- Attach diagnostic artifacts to this issue\n\n"
        "RCA Insight:\n"
        f"{insights.get('summary')}\n\n"
        "Recommended next action:\n"
        f"{insights.get('recommendation')}\n\n"
        "Suggested fixes (operator approval required):\n"
        f"{fixes_text}\n"
    )

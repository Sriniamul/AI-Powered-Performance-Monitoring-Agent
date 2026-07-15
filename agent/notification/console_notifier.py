class ConsoleNotifier:
    def notify(self, issue_key: str, decision: dict, insights: dict):
        print("\n=== AI PERFORMANCE AGENT INCIDENT ===")
        print(f"Issue: {issue_key}")
        print(f"Severity: {decision.get('severity')}")
        print(f"Reason: {decision.get('reason')}")
        print(f"RCA: {insights.get('summary')}")
        print("=====================================\n")

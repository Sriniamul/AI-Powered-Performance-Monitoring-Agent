from agent.jira.jira_payload_builder import build_issue_payload
from agent.utils.logger import get_logger

logger = get_logger(__name__)


class JiraIssueCreator:
    def __init__(self, config: dict, jira_client):
        self.config = config
        self.jira = jira_client

    def create_incident(self, metrics: dict, decision: dict, insights: dict, artifacts: dict):
        payload = build_issue_payload(self.config, metrics, decision, insights)
        issue_key = self.jira.create_issue(payload)
        logger.info("JIRA issue created: %s", issue_key)

        bundle = artifacts.get("bundle")
        if bundle:
            self.jira.add_attachment(issue_key, bundle)

        for file_path in artifacts.get("files", []):
            self.jira.add_attachment(issue_key, file_path)

        return issue_key

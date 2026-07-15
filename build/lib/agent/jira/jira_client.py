import os
from pathlib import Path
import json
import requests
from requests.auth import HTTPBasicAuth

from agent.utils.logger import get_logger

logger = get_logger(__name__)


class JiraClient:
    def __init__(self, config: dict):
        self.config = config
        agent_cfg = config.get("agent", {})
        self.dry_run = str(os.getenv("DRY_RUN", str(agent_cfg.get("dry_run", True)))).lower() == "true"
        jira_cfg = config.get("jira", {})
        self.base_url = os.getenv(jira_cfg.get("base_url_env", "JIRA_BASE_URL"), "").rstrip("/")
        self.email = os.getenv(jira_cfg.get("email_env", "JIRA_EMAIL"), "")
        self.token = os.getenv(jira_cfg.get("api_token_env", "JIRA_API_TOKEN"), "")

    def create_issue(self, payload: dict):
        if self.dry_run:
            return self._write_dry_run_issue(payload)
        self._validate()
        url = f"{self.base_url}/rest/api/3/issue"
        response = requests.post(url, json=payload, auth=HTTPBasicAuth(self.email, self.token), headers={"Accept": "application/json"}, timeout=30)
        response.raise_for_status()
        return response.json()["key"]

    def add_attachment(self, issue_key: str, file_path: str):
        if self.dry_run:
            logger.info("DRY_RUN: would attach %s to %s", file_path, issue_key)
            return {"dry_run": True, "issue_key": issue_key, "file": file_path}
        self._validate()
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            logger.warning("Attachment skipped because file does not exist: %s", file_path)
            return None
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/attachments"
        headers = {"X-Atlassian-Token": "no-check", "Accept": "application/json"}
        with path.open("rb") as fh:
            response = requests.post(
                url,
                headers=headers,
                auth=HTTPBasicAuth(self.email, self.token),
                files={"file": (path.name, fh)},
                timeout=120,
            )
        response.raise_for_status()
        return response.json()

    def _validate(self):
        if not self.base_url or not self.email or not self.token:
            raise ValueError("JIRA configuration missing. Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN.")

    def _write_dry_run_issue(self, payload: dict):
        out_dir = Path("artifacts")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "dry_run_jira_issue.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("DRY_RUN: wrote local JIRA issue payload to %s", out_file)
        return "DRY-RUN-1"

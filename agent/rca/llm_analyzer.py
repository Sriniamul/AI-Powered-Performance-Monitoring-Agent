import asyncio
import json
import os
import re

import requests

from agent.utils.logger import get_logger

logger = get_logger(__name__)


class LlmIncidentAnalyzer:
    """Produces structured incident analysis through the OpenAI Responses API."""

    def __init__(self, config: dict, session=None):
        llm = config.get("llm", {})
        self.enabled = bool(llm.get("enabled", True))
        self.provider = os.getenv("LLM_PROVIDER", llm.get("provider", "openai")).lower()
        if self.provider == "copilot":
            self.model = os.getenv("COPILOT_MODEL", "gpt-5")
            self.api_key = (os.getenv("COPILOT_KEY") or os.getenv("COPILOT_GITHUB_TOKEN")
                            or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN", ""))
        else:
            self.model = os.getenv("OPENAI_MODEL", llm.get("model", "gpt-5-mini"))
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.timeout = float(llm.get("timeout_seconds", 30))
        self.session = session or requests

    def analyze(self, metrics: dict, decision: dict) -> dict:
        if not self.enabled:
            return _unavailable("disabled", "LLM analysis is disabled.")
        if not self.api_key:
            key_name = "COPILOT_KEY" if self.provider == "copilot" else "OPENAI_API_KEY"
            return _unavailable("not_configured", f"Set {key_name} to enable LLM analysis.", self.model)
        evidence = _safe_evidence(metrics, decision)
        if self.provider == "copilot":
            return self._analyze_copilot(evidence)
        payload = {
            "model": self.model,
            "instructions": (
                "You are a production performance engineer. Analyze only the supplied evidence. "
                "Do not claim certainty or invent facts. Identify the most likely root cause, explain confidence, "
                "and propose safe, specific remediation and validation steps. Consider connection-pool changes, "
                "a one-pod-at-a-time restart, deployment rollback, Kubernetes scaling, JVM heap tuning, or cache "
                "clearing only when supported by evidence. Mark disruptive changes as requiring operator approval."
            ),
            "input": json.dumps(evidence),
            "text": {"format": {"type": "json_schema", "name": "incident_analysis", "strict": True,
                     "schema": {"type": "object", "additionalProperties": False,
                                "properties": {
                                    "root_cause": {"type": "string"},
                                    "suggested_solution": {"type": "string"},
                                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]}},
                                "required": ["root_cause", "suggested_solution", "confidence"]}}},
            "max_output_tokens": 600,
        }
        try:
            response = self.session.post(
                f"{self.base_url}/responses", json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = json.loads(_extract_output_text(response.json()))
            return {"status": "completed", "model": self.model, **result}
        except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
            logger.warning("LLM incident analysis unavailable: %s", exc)
            return _unavailable("error", "LLM analysis failed; review agent logs for details.", self.model)

    def _analyze_copilot(self, evidence: dict) -> dict:
        try:
            result = asyncio.run(self._copilot_request(evidence))
            return {"status": "completed", "model": self.model, "provider": "copilot", **result}
        except Exception as exc:
            logger.warning("Copilot incident analysis unavailable: %s", exc)
            return _unavailable("error", "Copilot analysis failed; review agent logs for details.", self.model)

    async def _copilot_request(self, evidence: dict) -> dict:
        from copilot import CopilotClient

        client = CopilotClient(github_token=self.api_key, use_logged_in_user=False, log_level="error")
        await client.start()
        try:
            session = await client.create_session(model=self.model, available_tools=[], skip_custom_instructions=True)
            prompt = (
                "Act as a production performance engineer. Analyze only the JSON evidence below. Do not invent facts. "
                "Return JSON only with exactly these keys: root_cause, suggested_solution, confidence. "
                "confidence must be low, medium, or high. Include safe validation steps in suggested_solution.\n\n"
                + json.dumps(evidence)
            )
            event = await session.send_and_wait(prompt, timeout=self.timeout)
            if not event:
                raise ValueError("Copilot returned no assistant response")
            text = event.data.content.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
            result = json.loads(text)
            if not all(key in result for key in ("root_cause", "suggested_solution", "confidence")):
                raise ValueError("Copilot response did not contain required fields")
            return result
        finally:
            await client.stop()


def _safe_evidence(metrics: dict, decision: dict) -> dict:
    allowed = (
        "timestamp", "environment", "machine_name", "operating_system", "cpu_percent", "memory_percent",
        "disk_percent", "disk_free_gb", "network_sent_mb_s", "network_received_mb_s", "network_connections",
        "process_count", "zombie_process_count", "top_cpu_process", "top_memory_process", "jvm_available",
        "jvm_heap_percent", "jvm_heap_used_mb", "jvm_heap_capacity_mb", "jvm_young_gc_count",
        "jvm_full_gc_count", "jvm_gc_time_seconds", "jvm_thread_count", "jvm_deadlock_detected",
        "jvm_classes_loaded", "jvm_classes_unloaded",
    )
    return {"metrics": {key: metrics.get(key) for key in allowed if key in metrics}, "decision": decision}


def _extract_output_text(response: dict) -> str:
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    raise ValueError("Responses API returned no output text")


def _unavailable(status: str, message: str, model: str | None = None) -> dict:
    return {"status": status, "model": model, "root_cause": message, "suggested_solution": message, "confidence": "low"}

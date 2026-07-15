import json

from agent.rca.llm_analyzer import LlmIncidentAnalyzer, _extract_output_text


def test_llm_analyzer_gracefully_handles_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = LlmIncidentAnalyzer({"llm": {"enabled": True}}).analyze({}, {})

    assert result["status"] == "not_configured"
    assert result["confidence"] == "low"


def test_extract_responses_api_output_text():
    expected = {"root_cause": "Heap pressure", "suggested_solution": "Inspect retained objects", "confidence": "medium"}
    response = {"output": [{"content": [{"type": "output_text", "text": json.dumps(expected)}]}]}

    assert json.loads(_extract_output_text(response)) == expected


def test_copilot_provider_accepts_requested_key_alias(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "copilot")
    monkeypatch.setenv("COPILOT_KEY", "test-token")
    monkeypatch.setenv("COPILOT_MODEL", "gpt-5")

    analyzer = LlmIncidentAnalyzer({"llm": {"enabled": True}})

    assert analyzer.provider == "copilot"
    assert analyzer.api_key == "test-token"
    assert analyzer.model == "gpt-5"

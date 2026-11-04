"""Canonical UI choices: provider ID is stable, transport is explicit.

Only the four legacy provider IDs are stored for active historic tasks. API
choices are intentionally inert until official credentialed clients exist.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelChoice:
    value: str
    label: str
    provider_id: str
    transport: str
    available: bool
    status: str

CHOICES = (
    ModelChoice("chatgpt", "ChatGPT (chronos)", "chatgpt", "browser", True, "automatic_browser"),
    ModelChoice("gemini", "Gemini (chronos)", "gemini", "browser", True, "automatic_browser"),
    ModelChoice("deepseek", "DeepSeek (chronos)", "deepseek", "browser", True, "automatic_browser"),
    ModelChoice("ollama", "Ollama (automatic local)", "ollama", "local", True, "automatic_local"),
    ModelChoice("chatgpt:api", "ChatGPT (api)", "chatgpt", "api", False, "not_configured"),
    ModelChoice("gemini:api", "Gemini (api)", "gemini", "api", False, "not_configured"),
    ModelChoice("deepseek:api", "DeepSeek (api)", "deepseek", "api", False, "not_configured"),
)
ADVANCED = ("custom_web", "web_slot_2", "web_slot_3")
BY_VALUE = {option.value: option for option in CHOICES}

def selection(value: str, transport: str | None = None) -> ModelChoice:
    option = BY_VALUE.get(value)
    if option is None and value in ADVANCED:
        option = ModelChoice(value, value, value, "browser", True, "advanced_configured_browser")
    if option is None:
        raise ValueError("Unknown model selection")
    if transport is not None and transport != option.transport:
        raise ValueError("Model transport mismatch; API choices cannot be sent through browser")
    if not option.available:
        raise ValueError(f"{option.label} is not configured. Official API client, model and credentials are required. No task was created.")
    return option

def public_catalog() -> dict:
    return {"default": "chatgpt", "options": [vars(c) for c in CHOICES],
            "advanced": [vars(ModelChoice(v, v, v, "browser", True,
                                   "requires_operator_configuration")) for v in ADVANCED]}

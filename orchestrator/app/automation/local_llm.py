"""Exodia local autonomous inference: no account scraping, no developer keys."""
from __future__ import annotations
import os
import httpx


class LocalModelError(RuntimeError):
    pass


class OllamaBackend:
    """Use only the loopback Ollama API; avoid accidentally sending prompts to a remote host."""

    def __init__(self, model: str | None = None, *, client: httpx.AsyncClient | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.base = "http://127.0.0.1:11434"
        self.client = client

    async def _request(self, method: str, endpoint: str, *, payload=None, timeout=240):
        async def execute(c):
            return await c.request(method, self.base + endpoint, json=payload, timeout=timeout)
        try:
            if self.client is not None:
                response = await execute(self.client)
            else:
                async with httpx.AsyncClient(trust_env=False) as client:
                    response = await execute(client)
            response.raise_for_status()
            return response.json()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise LocalModelError("Ollama is not running. Install it, run 'ollama pull llama3.2:3b', and verify http://127.0.0.1:11434.") from None
        except httpx.TimeoutException:
            raise LocalModelError("Ollama timed out while generating. Try a smaller model or check your hardware.") from None
        except httpx.HTTPStatusError as exc:
            raise LocalModelError(f"Ollama HTTP {exc.response.status_code}. Confirm the model is downloaded using 'ollama list'.") from None
        except (ValueError, TypeError):
            raise LocalModelError("Ollama sent an invalid JSON response.") from None

    async def status(self) -> dict:
        try:
            data = await self._request("GET", "/api/tags", timeout=5)
            names = [m.get("name", "") for m in data.get("models", [])]
            return {"connected": True, "model": self.model,
                    "model_installed": self.model in names,
                    "available_models": names[:40],
                    "requires_api_key": False}
        except LocalModelError as exc:
            return {"connected": False, "model": self.model,
                    "model_installed": False, "requires_api_key": False,
                    "error": str(exc)}

    async def generate(self, prompt: str, *, companion: str) -> dict:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        if len(prompt) > 12000:
            raise ValueError("Prompt is too long")
        system = ("You are the AI assistant assigned to Exodia Tower as " + companion +
                  ". Be helpful and precise. Clearly distinguish facts from assumptions. "
                  "Do not invent live metrics, research sources, or completed external actions.")
        result = await self._request(
            "POST", "/api/chat",
            payload={"model": self.model, "stream": False, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt.strip()}
            ]})
        text = result.get("message", {}).get("content", "")
        if not isinstance(text, str) or not text.strip():
            raise LocalModelError("Ollama returned no text. Check model output in the local Ollama logs.")
        return {"answer": text.strip()[:100000], "provider": "ollama",
                "model": self.model, "source": "local_inference",
                "tokens": result.get("eval_count", 0)}

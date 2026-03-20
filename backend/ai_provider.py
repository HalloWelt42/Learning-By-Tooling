"""ai_provider.py -- Modulares KI-Provider-System.

Provider kapseln die Kommunikation mit verschiedenen LLM-Backends.
Aktuell: LM Studio. Erweiterbar um Ollama, OpenAI-kompatible APIs etc.
"""

import re, json, httpx
from collections import defaultdict

# Provider-Registry
PROVIDERS = {}

def register_provider(cls):
    PROVIDERS[cls.name] = cls
    return cls


class AIProvider:
    """Basisklasse fuer KI-Provider."""
    name: str = ""

    def __init__(self, base_url: str, **kwargs):
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages: list, max_tokens: int = 500,
                   temperature: float = 0.3, timeout: float = 30.0,
                   response_format: dict | None = None) -> str | None:
        raise NotImplementedError

    async def is_online(self) -> bool:
        raise NotImplementedError

    async def get_model_name(self) -> str:
        raise NotImplementedError


@register_provider
class LMStudioProvider(AIProvider):
    """LM Studio via OpenAI-kompatible API."""
    name = "lmstudio"
    _client: httpx.AsyncClient | None = None
    _model: str | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=10.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def get_model_name(self) -> str:
        if self._model:
            return self._model
        try:
            c = self._get_client()
            r = await c.get("/v1/models")
            if r.status_code == 200:
                models = r.json().get("data", [])
                if models:
                    self._model = models[0]["id"]
                    return self._model
        except Exception:
            pass
        return "local-model"

    async def is_online(self) -> bool:
        try:
            c = self._get_client()
            r = await c.get("/v1/models")
            if r.status_code != 200:
                return False
            models = r.json().get("data", [])
            if not models:
                return False
            self._model = models[0]["id"]
            return True
        except Exception:
            return False

    async def chat(self, messages: list, max_tokens: int = 500,
                   temperature: float = 0.3, timeout: float = 30.0,
                   response_format: dict | None = None) -> str | None:
        model = await self.get_model_name()
        # Qwen3: Thinking-Modus deaktivieren
        processed = []
        for msg in messages:
            if msg["role"] == "user":
                processed.append({**msg, "content": f"/no_think\n{msg['content']}"})
            else:
                processed.append(msg)

        payload = {
            "model": model, "messages": processed,
            "max_tokens": max_tokens, "temperature": temperature,
            "min_p": 0.05,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            c = self._get_client()
            r = await c.post("/v1/chat/completions", json=payload, timeout=timeout)
            if r.status_code == 200:
                text = r.json()["choices"][0]["message"]["content"].strip()
                # Qwen3: leeren Think-Block entfernen
                text = re.sub(r'^<think>\s*</think>\s*', '', text)
                return text
        except Exception:
            pass
        return None


@register_provider
class OllamaProvider(AIProvider):
    """Ollama via native API (Platzhalter fuer spaetere Implementierung)."""
    name = "ollama"
    _client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=10.0),
            )
        return self._client

    async def get_model_name(self) -> str:
        try:
            c = self._get_client()
            r = await c.get("/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                if models:
                    return models[0]["name"]
        except Exception:
            pass
        return "unknown"

    async def is_online(self) -> bool:
        try:
            c = self._get_client()
            r = await c.get("/api/tags")
            return r.status_code == 200
        except Exception:
            return False

    async def chat(self, messages: list, max_tokens: int = 500,
                   temperature: float = 0.3, timeout: float = 30.0,
                   response_format: dict | None = None) -> str | None:
        model = await self.get_model_name()
        payload = {
            "model": model, "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if response_format:
            payload["format"] = "json"
        try:
            c = self._get_client()
            r = await c.post("/api/chat", json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json().get("message", {}).get("content", "").strip()
        except Exception:
            pass
        return None


# -- Singleton-Cache fuer Provider-Instanzen --
_provider_cache: dict[str, AIProvider] = {}

def get_provider(settings: dict | None = None) -> AIProvider:
    """Gibt den konfigurierten Provider zurueck (gecacht)."""
    settings = settings or {}
    name = settings.get("ai_provider", "lmstudio")
    url = settings.get("ai_provider_url", "http://192.168.178.45:1234")

    key = f"{name}:{url}"
    if key not in _provider_cache:
        cls = PROVIDERS.get(name, LMStudioProvider)
        _provider_cache[key] = cls(base_url=url)
    return _provider_cache[key]


def render_template(tmpl: dict, variables: dict) -> tuple[str, str]:
    """Ersetzt {placeholders} in system_prompt und user_prompt."""
    safe_vars = defaultdict(str, variables)
    system = tmpl["system_prompt"].format_map(safe_vars)
    user = tmpl["user_prompt"].format_map(safe_vars)
    return system, user


def strip_json(raw: str) -> str:
    """Entfernt Markdown-Code-Bloecke von JSON-Antworten."""
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()

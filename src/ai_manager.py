"""
Optional LLM access for Legacy of Stars.

The game is fully playable without any language model: every caller of
generate_text() has a written fallback.  This module only adds flavour when
a provider is reachable.

Provider selection: AI_PROVIDER env var, else "default_provider" in
data/llm_providers.json.  LOS_OFFLINE=1 disables the LLM entirely.
A .env file in the project root is read at start-up (KEY=VALUE lines).
"""
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "llm_providers.json"
ENV_PATH = ROOT / ".env"

DEFAULT_TIMEOUT = 20.0   # seconds per generation request
PROBE_TIMEOUT = 2.0      # seconds for the one-time availability check
MAX_FAILURES = 2         # consecutive failures before the LLM is switched off for the session


def load_dotenv(path: Path = ENV_PATH, override: bool = False) -> Dict[str, str]:
    """Tiny .env reader: KEY=VALUE lines, '#' comments, optional quotes, optional 'export '."""
    loaded: Dict[str, str] = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return loaded
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


class AIManager:
    """Thin client for Ollama / OpenAI-compatible / Anthropic APIs with honest failure semantics."""

    def __init__(self, offline: bool = False, provider_alias: Optional[str] = None,
                 probe: bool = True, config_path: Path = CONFIG_PATH, env_path: Path = ENV_PATH):
        load_dotenv(env_path)
        self.offline = bool(offline) or os.getenv("LOS_OFFLINE") == "1"
        self.config = self.load_config(config_path)
        alias = provider_alias or os.getenv("AI_PROVIDER") or self.config.get("default_provider")
        self.provider_alias = alias
        self.current_provider = self.get_provider(alias)
        self.probe = probe
        self._available: Optional[bool] = None
        self.failures = 0
        self.last_error: Optional[str] = None

    # ------------------------------------------------------------------ config
    @staticmethod
    def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning(f"LLM config not found: {path} (AI features disabled)")
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning(f"Could not read LLM config {path}: {exc}")
        return {}

    def get_provider(self, alias: Optional[str]) -> Optional[Dict[str, Any]]:
        if not alias:
            return None
        for provider in self.config.get("providers", []):
            if provider.get("alias") == alias:
                return provider
        if self.config:
            logging.warning(f"LLM provider alias '{alias}' not found in config")
        return None

    def describe(self) -> str:
        """One line for the UI/help screen."""
        if self.offline:
            return "offline (LOS_OFFLINE=1)"
        if not self.current_provider:
            return "no LLM provider configured"
        p = self.current_provider
        where = p.get("host") or p.get("base_url") or p.get("type", "?")
        state = "available" if self.is_available() else f"unavailable ({self.last_error or 'not reachable'})"
        return f"{p.get('alias')} / {p.get('model', '?')} at {where}: {state}"

    # ------------------------------------------------------------------ availability
    def is_available(self) -> bool:
        if self.offline or not self.current_provider:
            return False
        if self._available is None:
            self._available = self._probe() if self.probe else True
            if not self._available:
                logging.info(f"LLM provider '{self.provider_alias}' unavailable: {self.last_error}")
        return self._available

    def _probe(self) -> bool:
        provider = self.current_provider or {}
        ptype = provider.get("type")
        try:
            if ptype == "ollama":
                host = provider.get("host", "http://127.0.0.1:11434").rstrip("/")
                with urllib.request.urlopen(f"{host}/api/tags", timeout=PROBE_TIMEOUT) as response:
                    return 200 <= response.status < 300
            if ptype == "openai_compatible":
                base_url = provider.get("base_url", "http://127.0.0.1:1234/v1").rstrip("/")
                request = urllib.request.Request(f"{base_url}/models", headers=self._auth_headers(provider))
                with urllib.request.urlopen(request, timeout=PROBE_TIMEOUT) as response:
                    return 200 <= response.status < 300
            if ptype in ("anthropic", "openai"):
                if self._api_key(provider):
                    return True
                self.last_error = "API key missing"
                return False
            self.last_error = f"provider type '{ptype}' not supported"
            return False
        except Exception as exc:  # noqa: BLE001 - any failure just means "no AI"
            self.last_error = str(exc)
            return False

    # ------------------------------------------------------------------ generation
    def generate_text(self, prompt: str, system_prompt: str = "You are a sci-fi game master.",
                      timeout: float = DEFAULT_TIMEOUT) -> Optional[str]:
        """Return generated text, or None when the LLM is unavailable or fails. Never raises."""
        if not self.is_available():
            return None
        provider = self.current_provider or {}
        ptype = provider.get("type")
        try:
            if ptype == "ollama":
                text = self._call_ollama(prompt, system_prompt, timeout)
            elif ptype == "anthropic":
                text = self._call_anthropic(prompt, system_prompt, timeout)
            elif ptype in ("openai", "openai_compatible"):
                text = self._call_openai(prompt, system_prompt, timeout)
            else:
                self.last_error = f"provider type '{ptype}' not supported"
                self._available = False
                return None
        except Exception as exc:  # noqa: BLE001 - flavour text must never break the game
            self.failures += 1
            self.last_error = str(exc)
            logging.warning(f"LLM request failed ({ptype}): {exc}")
            if self.failures >= MAX_FAILURES:
                logging.warning("LLM disabled for this session after repeated failures")
                self._available = False
            return None
        self.failures = 0
        text = (text or "").strip()
        return text or None

    # ------------------------------------------------------------------ providers
    @staticmethod
    def _api_key(provider: Dict[str, Any]) -> Optional[str]:
        env_name = provider.get("api_key_env")
        if env_name:
            return os.environ.get(env_name)
        return provider.get("api_key")

    def _auth_headers(self, provider: Dict[str, Any]) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self._api_key(provider)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    @staticmethod
    def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _call_ollama(self, prompt: str, system_prompt: str, timeout: float) -> str:
        provider = self.current_provider
        host = provider.get("host", "http://127.0.0.1:11434").rstrip("/")
        payload = {
            "model": provider.get("model", "llama3.1:8b"),
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }
        result = self._post_json(f"{host}/api/generate", payload, {"Content-Type": "application/json"}, timeout)
        return result.get("response", "")

    def _call_anthropic(self, prompt: str, system_prompt: str, timeout: float) -> str:
        provider = self.current_provider
        api_key = self._api_key(provider)
        if not api_key:
            raise RuntimeError("Missing API key (set ANTHROPIC_API_KEY)")
        payload = {
            "model": provider.get("model", "claude-haiku-4-5"),
            "max_tokens": provider.get("max_tokens", 1024),
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        result = self._post_json("https://api.anthropic.com/v1/messages", payload, headers, timeout)
        return result["content"][0]["text"]

    def _call_openai(self, prompt: str, system_prompt: str, timeout: float) -> str:
        provider = self.current_provider
        if provider.get("type") == "openai" and not self._api_key(provider):
            raise RuntimeError("Missing API key (set OPENAI_API_KEY)")
        base_url = provider.get("base_url", "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": provider.get("model", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }
        result = self._post_json(f"{base_url}/chat/completions", payload, self._auth_headers(provider), timeout)
        return result["choices"][0]["message"]["content"]

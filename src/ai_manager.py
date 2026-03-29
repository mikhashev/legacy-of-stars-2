import json
import urllib.request
import urllib.error
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

class AIManager:
    def __init__(self):
        self.config = self.load_config()
        self.current_provider = self.get_provider(self.config.get("default_provider"))
        # Wippy runtime endpoint
        self.wippy_url = os.getenv("WIPPY_URL", "http://localhost:8080/api")
        self.wippy_enabled = os.getenv("WIPPY_ENABLED", "true").lower() == "true"
        self.generation = 1  # Track current generation for learning

    def load_config(self) -> Dict[str, Any]:
        """Load LLM providers configuration"""
        try:
            path = Path("data/llm_providers.json")
            if not path.exists():
                print("Warning: data/llm_providers.json not found.")
                return {}
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading LLM config: {e}")
            return {}

    def get_provider(self, alias: str) -> Optional[Dict[str, Any]]:
        """Get provider config by alias"""
        if not self.config:
            return None
        
        for provider in self.config.get("providers", []):
            if provider["alias"] == alias:
                return provider
        return None

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama API"""
        host = self.current_provider.get("host", "http://127.0.0.1:11434")
        model = self.current_provider.get("model", "llama3.1:8b")
        url = f"{host}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
                
        except urllib.error.URLError as e:
            raise Exception(f"Connection failed - {e}")

    def _call_anthropic(self, prompt: str, system_prompt: str) -> str:
        """Call Anthropic API (Claude)"""
        import os
        
        api_key_env = self.current_provider.get("api_key_env")
        api_key = os.environ.get(api_key_env) if api_key_env else self.current_provider.get("api_key")
        
        if not api_key:
            raise Exception("Missing API Key. Please set ANTHROPIC_API_KEY environment variable.")
            
        model = self.current_provider.get("model", "claude-3-haiku-20240307")
        url = "https://api.anthropic.com/v1/messages"
        
        # Anthropic messages format
        payload = {
            "model": model,
            "max_tokens": self.current_provider.get("max_tokens", 1024),
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"]

    def _call_openai(self, prompt: str, system_prompt: str) -> str:
        """Call OpenAI or Compatible API"""
        import os
        
        api_key_env = self.current_provider.get("api_key_env")
        api_key = os.environ.get(api_key_env) if api_key_env else self.current_provider.get("api_key")
        
        if not api_key and self.current_provider.get("type") == "openai":
            raise Exception("Missing API Key.")
            
        base_url = self.current_provider.get("base_url", "https://api.openai.com/v1")
        url = f"{base_url}/chat/completions"
        model = self.current_provider.get("model", "gpt-3.5-turbo")
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]

    def _call_wippy(self, prompt: str, system_prompt: str = "You are a sci-fi game master.") -> str:
        """Delegate to Wippy AI runtime"""
        url = f"{self.wippy_url}/advisor/analyze"
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "generation": self.generation
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.URLError as e:
            logging.warning(f"Wippy runtime unavailable: {e}")
            raise

    def generate_text(self, prompt: str, system_prompt: str = "You are a sci-fi game master.") -> str:
        """Generate text using the current provider, with Wippy fallback"""
        # Try Wippy first if enabled
        if self.wippy_enabled:
            try:
                return self._call_wippy(prompt, system_prompt)
            except Exception as e:
                logging.warning(f"Wippy unavailable, using direct LLM: {e}")

        # Fallback to direct LLM call
        if not self.current_provider:
            return "AI Error: No provider configured."

        provider_type = self.current_provider.get("type")

        try:
            if provider_type == "ollama":
                return self._call_ollama(prompt, system_prompt)
            elif provider_type == "anthropic":
                return self._call_anthropic(prompt, system_prompt)
            elif provider_type == "openai" or provider_type == "openai_compatible":
                return self._call_openai(prompt, system_prompt)
            else:
                return f"AI Error: Provider type '{provider_type}' not yet implemented."
        except Exception as e:
            return f"AI Error ({provider_type}): {str(e)}"

    def check_wippy_health(self) -> bool:
        """Check if Wippy runtime is available"""
        if not self.wippy_enabled:
            return False

        try:
            url = f"{self.wippy_url}/advisor/health"
            with urllib.request.urlopen(url, timeout=5) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("status") == "healthy"
        except:
            return False

    def wippy_civ_response(self, params: Dict[str, Any]) -> Optional[Dict]:
        """Generate civilization response using Wippy"""
        if not self.wippy_enabled:
            return None

        try:
            url = f"{self.wippy_url}/civ_response/generate"
            data = json.dumps(params).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logging.warning(f"Wippy civ response failed: {e}")
            return None

    def wippy_director_log(self, params: Dict[str, Any]) -> Optional[str]:
        """Generate director log using Wippy"""
        if not self.wippy_enabled:
            return None

        try:
            url = f"{self.wippy_url}/director_log/narrate"
            data = json.dumps(params).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("log_entry")
        except Exception as e:
            logging.warning(f"Wippy director log failed: {e}")
            return None

    def wippy_learn(self, outcome: Dict[str, Any]) -> bool:
        """Send learning outcome to Wippy"""
        if not self.wippy_enabled:
            return False

        try:
            url = f"{self.wippy_url}/advisor/learn"
            data = json.dumps(outcome).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("success", False)
        except Exception as e:
            logging.warning(f"Wippy learn failed: {e}")
            return False

    def set_generation(self, generation: int):
        """Update current generation for learning context"""
        self.generation = generation


import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any

class AIManager:
    def __init__(self):
        self.config = self.load_config()
        self.current_provider = self.get_provider(self.config.get("default_provider"))

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

    def generate_text(self, prompt: str, system_prompt: str = "You are a sci-fi game master.") -> str:
        """Generate text using the current provider"""
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


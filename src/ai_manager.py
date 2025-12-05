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
        
        if provider_type == "ollama":
            return self._call_ollama(prompt, system_prompt)
        else:
            return f"AI Error: Provider type '{provider_type}' not yet implemented."

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
            return f"AI Error (Ollama): Connection failed - {e}"
        except Exception as e:
            return f"AI Error (Ollama): {e}"

# Test block
if __name__ == "__main__":
    ai = AIManager()
    print(f"Provider: {ai.current_provider.get('alias')}")
    print("Testing generation...")
    response = ai.generate_text("Greetings, Earthling. We come in peace.", "You are an alien diplomat.")
    print(f"Response: {response}")

import requests
import json
from typing import List, Dict, Any, Optional

class OllamaAPI:
    def __init__(self, base_url="http://localhost:11434"):
        """Initialize the Ollama API client."""
        self.base_url = base_url
        
    def list_models(self) -> List[Dict[str, Any]]:
        """Get a list of all available models from the Ollama API."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            
            if response.status_code == 200:
                return response.json().get("models", [])
            else:
                print(f"Error getting models: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"Exception when calling Ollama API: {e}")
            return []
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting model info: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception when calling Ollama API: {e}")
            return None
    
    def get_model_names(self) -> List[str]:
        """Get a list of available model names."""
        models = self.list_models()
        return [model.get("name") for model in models if "name" in model]
    
    def check_connection(self) -> bool:
        """Check if the Ollama API is accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/version")
            return response.status_code == 200
        except:
            return False
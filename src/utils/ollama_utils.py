import requests
import json
import time
from typing import List, Dict, Any, Optional

class OllamaAPI:
    def __init__(self, base_url="http://localhost:11434"):
        """Initialize the Ollama API client."""
        self.base_url = base_url
        self.timeout = 5  # 5 second timeout for API calls
        
    def list_models(self) -> List[Dict[str, Any]]:
        """Get a list of all available models from the Ollama API."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                return models
            else:
                print(f"Error getting models: {response.status_code} - {response.text}")
                return []
        except requests.exceptions.ConnectTimeout:
            print("Connection to Ollama API timed out.")
            return []
        except requests.exceptions.ConnectionError:
            print("Failed to connect to Ollama API. Make sure Ollama is running.")
            return []
        except Exception as e:
            print(f"Exception when calling Ollama API: {e}")
            return []
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting model info: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.ConnectTimeout:
            print("Connection to Ollama API timed out.")
            return None
        except requests.exceptions.ConnectionError:
            print("Failed to connect to Ollama API. Make sure Ollama is running.")
            return None
        except Exception as e:
            print(f"Exception when calling Ollama API: {e}")
            return None
    
    def get_model_names(self) -> List[str]:
        """Get a list of available model names."""
        models = self.list_models()
        model_names = [model.get("name").replace(":latest", "") for model in models if "name" in model]
        return sorted(model_names)
    
    def check_connection(self) -> bool:
        """Check if the Ollama API is accessible."""
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=self.timeout
            )
            return response.status_code == 200
        except requests.exceptions.ConnectTimeout:
            print("Connection to Ollama API timed out.")
            return False
        except requests.exceptions.ConnectionError:
            print("Failed to connect to Ollama API. Make sure Ollama is running.")
            return False
        except:
            return False
            
    def test_model(self, model_name: str) -> bool:
        """Test if a model is available and functioning."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "test",
                    "stream": False,
                    "options": {
                        "num_predict": 10  # Keep it small for quick testing
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"Error testing model: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Exception when testing model: {e}")
            return False
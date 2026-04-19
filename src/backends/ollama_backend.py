"""Ollama Backend - Opção A para download e gerenciamento de modelos."""
import requests
import subprocess
import platform
from typing import Optional, List, Dict, Callable


class OllamaBackend:
    """Interface com Ollama para download e gerenciamento de modelos."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def is_running(self) -> bool:
        """Verifica se o Ollama está rodando."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def start_ollama(self) -> bool:
        """Tenta iniciar o Ollama."""
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["ollama", "serve"], 
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(["ollama", "serve"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False
    
    def list_models(self) -> List[Dict]:
        """Lista modelos instalados localmente."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
        except requests.exceptions.RequestException:
            return []
    
    def pull_model(self, model_name: str, 
                   progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """Baixa um modelo do registro Ollama."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": True},
                stream=True,
                timeout=None
            )
            
            if response.status_code != 200:
                return False
            
            for line in response.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    status = data.get("status", "")
                    
                    if "total" in data and "completed" in data:
                        progress = (data["completed"] / data["total"]) * 100
                        if progress_callback:
                            progress_callback(status, progress)
                    elif progress_callback:
                        progress_callback(status, -1)
            
            return True
        except requests.exceptions.RequestException as e:
            print(f"Erro ao baixar modelo: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """Remove um modelo instalado."""
        try:
            response = self.session.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
                timeout=30
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Obtém informações de um modelo."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException:
            return None
    
    def chat(self, model_name: str, message: str, 
             stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """Envia mensagem para o modelo via Ollama."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": message,
                    "stream": True
                },
                stream=True,
                timeout=None
            )
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    token = data.get("response", "")
                    full_response += token
                    if stream_callback:
                        stream_callback(token)
            
            return full_response
        except requests.exceptions.RequestException as e:
            return f"Erro: {e}"
    
    @staticmethod
    def get_available_models() -> List[str]:
        """Retorna lista de modelos populares disponíveis para download."""
        return [
            "llama3.2:1b",
            "llama3.2:3b",
            "llama3.1:8b",
            "llama3.1:70b",
            "mistral:7b",
            "mixtral:8x7b",
            "codellama:7b",
            "codellama:13b",
            "phi3:mini",
            "phi3:medium",
            "gemma2:2b",
            "gemma2:9b",
            "qwen2.5:7b",
            "qwen2.5:14b",
            "deepseek-coder:6.7b",
        ]

"""LMStudio Backend - Option B for downloading and managing models."""
import requests
import subprocess
import platform
import os
from pathlib import Path
from typing import Optional, List, Dict, Callable


class LMStudioBackend:
    """Interface with LMStudio for downloading and managing models."""
    
    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url
        self.session = requests.Session()
        self._models_dir = self._get_models_directory()
    
    def _get_models_directory(self) -> Path:
        """Gets the LMStudio models directory."""
        if platform.system() == "Windows":
            return Path(os.environ.get("USERPROFILE", "")) / ".cache" / "lm-studio" / "models"
        elif platform.system() == "Darwin":
            return Path.home() / ".cache" / "lm-studio" / "models"
        else:
            return Path.home() / ".cache" / "lm-studio" / "models"
    
    def is_running(self) -> bool:
        """Checks if the LMStudio server is running."""
        try:
            response = self.session.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def start_lmstudio(self) -> bool:
        """Tries to start LMStudio (only notifies, user must open manually)."""
        # LMStudio needs to be opened manually by the user
        return False
    
    def list_models(self) -> List[Dict]:
        """Lists models available on the LMStudio server."""
        try:
            response = self.session.get(f"{self.base_url}/v1/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get("data", []):
                    models.append({
                        "name": model.get("id", ""),
                        "size": 0,
                        "modified_at": ""
                    })
                return models
            return []
        except requests.exceptions.RequestException:
            return []
    
    def list_local_models(self) -> List[Dict]:
        """Lists locally downloaded models in the LMStudio directory."""
        models = []
        if self._models_dir.exists():
            for org_dir in self._models_dir.iterdir():
                if org_dir.is_dir():
                    for model_dir in org_dir.iterdir():
                        if model_dir.is_dir():
                            # Search for GGUF files
                            gguf_files = list(model_dir.glob("*.gguf"))
                            for gguf in gguf_files:
                                models.append({
                                    "name": f"{org_dir.name}/{model_dir.name}/{gguf.name}",
                                    "size": gguf.stat().st_size,
                                    "path": str(gguf)
                                })
        return models
    
    def download_model_hf(self, repo_id: str, filename: str,
                          progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """Downloads a model from HuggingFace to the LMStudio directory."""
        try:
            from huggingface_hub import hf_hub_download
            
            if progress_callback:
                progress_callback(f"Downloading {filename}...", 0)
            
            # Download to the LMStudio models directory
            org_name = repo_id.split("/")[0] if "/" in repo_id else "models"
            model_name = repo_id.split("/")[1] if "/" in repo_id else repo_id
            
            local_dir = self._models_dir / org_name / model_name
            local_dir.mkdir(parents=True, exist_ok=True)
            
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(local_dir),
                local_dir_use_symlinks=False
            )
            
            if progress_callback:
                progress_callback("Download complete!", 100)
            
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}", -1)
            return False
    
    def delete_model(self, model_path: str) -> bool:
        """Removes an installed model."""
        try:
            path = Path(model_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def chat(self, model_name: str, message: str,
             system_prompt: str = "", max_tokens: int = 512, temperature: float = 0.7,
             stream_callback: Optional[Callable[[str], None]] = None,
             conversation_history: Optional[list] = None) -> str:
        """Sends a message to the model via LMStudio (OpenAI compatible API)."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history for context
            if conversation_history:
                for msg in conversation_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            
            messages.append({"role": "user", "content": message})

            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }

            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=None
            )
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        import json
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                full_response += token
                                if stream_callback:
                                    stream_callback(token)
                        except json.JSONDecodeError:
                            continue
            
            return full_response
        except requests.exceptions.RequestException as e:
            return f"Error: {e}"
    
    @staticmethod
    def get_popular_models() -> List[Dict[str, str]]:
        """Returns a list of popular GGUF models from HuggingFace."""
        return [
            {"repo": "TheBloke/Llama-2-7B-GGUF", "file": "llama-2-7b.Q4_K_M.gguf"},
            {"repo": "TheBloke/Llama-2-13B-GGUF", "file": "llama-2-13b.Q4_K_M.gguf"},
            {"repo": "TheBloke/Mistral-7B-v0.1-GGUF", "file": "mistral-7b-v0.1.Q4_K_M.gguf"},
            {"repo": "TheBloke/CodeLlama-7B-GGUF", "file": "codellama-7b.Q4_K_M.gguf"},
            {"repo": "TheBloke/Phi-2-GGUF", "file": "phi-2.Q4_K_M.gguf"},
            {"repo": "bartowski/gemma-2-2b-it-GGUF", "file": "gemma-2-2b-it-Q4_K_M.gguf"},
            {"repo": "bartowski/Qwen2.5-7B-Instruct-GGUF", "file": "Qwen2.5-7B-Instruct-Q4_K_M.gguf"},
            {"repo": "bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF", "file": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf"},
        ]

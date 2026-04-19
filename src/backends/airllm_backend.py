"""AirLLM Backend - For running large models with limited memory."""
import json
import os
import threading
import subprocess
import platform
from typing import Optional, Callable, Generator, List, Dict, TYPE_CHECKING
from pathlib import Path

import requests

from ..utils.airllm_import import ensure_airllm_path, try_import_airllm

if TYPE_CHECKING:
    from ..utils.config import Config


def _append_lmstudio_roots_from_json(path: Path, roots: List[Path]) -> None:
    """Reads model paths from LM Studio's settings.json (custom folders)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    for key in (
        "modelDownloadFolder",
        "modelsDirectory",
        "downloadFolder",
        "userModelDir",
        "modelDownloadPath",
        "modelsPath",
    ):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            p = Path(v.strip())
            if p.is_dir():
                roots.append(p)


class AirLLMBackend:
    """Interface with AirLLM for running large models with limited memory."""
    
    def __init__(self, config: Optional["Config"] = None):
        self.model = None
        self.tokenizer = None
        self.model_name = None
        self.model_path = None
        self._loading = False
        self._lock = threading.Lock()
        self._config = config
        self._ollama_models_dir = self._get_ollama_models_dir()
    
    def _ollama_api_base(self) -> str:
        url = "http://localhost:11434"
        if self._config is not None:
            url = (self._config.ollama_url or url).strip()
        return url.rstrip("/")
    
    def _get_ollama_models_dir(self) -> Path:
        """Root directory for Ollama models (manifests, blobs)."""
        env = os.environ.get("OLLAMA_MODELS", "").strip()
        if env:
            return Path(env)
        return Path.home() / ".ollama" / "models"
    
    def _lmstudio_candidate_roots(self) -> List[Path]:
        """Folders where LM Studio typically stores GGUF files (varies by version)."""
        roots: List[Path] = []
        env = os.environ.get("LMSTUDIO_MODELS", "").strip()
        if env:
            roots.append(Path(env))
        home = Path.home()
        roots.extend([
            home / ".cache" / "lm-studio" / "models",
            home / ".lmstudio" / "models",
        ])
        if platform.system() == "Windows":
            lad = os.environ.get("LOCALAPPDATA", "")
            if lad:
                roots.append(Path(lad) / "LM Studio" / "models")
        for name in ("settings.json", "config.json", "preferences.json"):
            p = home / ".lmstudio" / name
            if p.is_file():
                _append_lmstudio_roots_from_json(p, roots)
                break
        seen: set[str] = set()
        unique: List[Path] = []
        for r in roots:
            try:
                key = str(r.resolve())
            except OSError:
                continue
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique
    
    def list_ollama_models(self) -> List[Dict]:
        """Lists Ollama models. Prefers the API (reliable); falls back to disk."""
        models: List[Dict] = []
        base = self._ollama_api_base()
        try:
            r = requests.get(f"{base}/api/tags", timeout=8)
            if r.status_code == 200:
                for m in r.json().get("models", []):
                    name = m.get("name") or m.get("model")
                    if not name:
                        continue
                    models.append({
                        "name": name,
                        "source": "ollama",
                        "path": name,
                        "type": "ollama",
                    })
                if models:
                    return models
        except requests.exceptions.RequestException:
            pass
        
        manifests_dir = self._ollama_models_dir / "manifests" / "registry.ollama.ai" / "library"
        if manifests_dir.exists():
            for model_dir in manifests_dir.iterdir():
                if not model_dir.is_dir():
                    continue
                for version in model_dir.iterdir():
                    tag = version.name if version.is_dir() else version.stem
                    name = f"{model_dir.name}:{tag}"
                    models.append({
                        "name": name,
                        "source": "ollama",
                        "path": name,
                        "type": "ollama",
                    })
        return models
    
    def list_lmstudio_models(self) -> List[Dict]:
        """Lists GGUF files in all typical LM Studio folders."""
        models: List[Dict] = []
        seen: set[str] = set()
        for root in self._lmstudio_candidate_roots():
            if not root.is_dir():
                continue
            try:
                for gguf in root.rglob("*.gguf"):
                    if not gguf.is_file():
                        continue
                    try:
                        key = str(gguf.resolve())
                    except OSError:
                        key = str(gguf)
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        rel = gguf.relative_to(root)
                        parts = rel.parts
                        if len(parts) >= 2:
                            name = "/".join(parts[:-1]) + "/" + gguf.stem
                        else:
                            name = gguf.stem
                    except ValueError:
                        name = gguf.stem
                    try:
                        size = gguf.stat().st_size
                    except OSError:
                        size = 0
                    models.append({
                        "name": name,
                        "source": "lmstudio",
                        "path": str(gguf),
                        "type": "gguf",
                        "size": size,
                    })
            except OSError:
                continue
        models.sort(key=lambda x: x["name"].lower())
        return models
    
    def list_all_local_models(self) -> List[Dict]:
        """Lists all local models available for execution."""
        models = []
        models.extend(self.list_ollama_models())
        models.extend(self.list_lmstudio_models())
        return models
    
    def is_model_loaded(self) -> bool:
        """Checks if a model is loaded."""
        return self.model is not None
    
    def get_loaded_model_name(self) -> Optional[str]:
        """Returns the name of the loaded model."""
        return self.model_name
    
    # Constants to signal the UI which package is missing
    MISSING_AIRLLM = "AIRLLM_NOT_INSTALLED"
    MISSING_LLAMACPP = "LLAMACPP_NOT_INSTALLED"

    def load_model(self, model_path: str, 
                   progress_callback: Optional[Callable[[str], None]] = None,
                   compression: str = "4bit",
                   model_type: str = "huggingface") -> bool:
        """
        Loads a model using AirLLM.
        
        Args:
            model_path: Local path or HuggingFace ID (e.g., "meta-llama/Llama-2-7b-hf")
            progress_callback: Callback for loading status
            compression: Compression type ("4bit", "8bit", or "none")
            model_type: Model type ("huggingface", "gguf", "ollama")

        Raises:
            ImportError: With message containing MISSING_AIRLLM or MISSING_LLAMACPP
                         when the package is not installed. The caller (UI) should
                         catch this exception and offer automatic installation.
        """
        with self._lock:
            if self._loading:
                return False
            self._loading = True
        
        try:
            # -- GGUF via llama-cpp-python ----------------------------------
            if model_type == "gguf":
                if progress_callback:
                    progress_callback("Loading GGUF model with llama-cpp-python...")
                
                try:
                    from llama_cpp import Llama  # noqa: F811
                except ImportError:
                    raise ImportError(self.MISSING_LLAMACPP)

                self.model = Llama(
                    model_path=model_path,
                    n_ctx=4096,
                    n_threads=4,
                    verbose=False,
                )
                self.model_name = model_path
                self.model_path = model_path
                self._model_type = "gguf"
                    
                if progress_callback:
                    progress_callback("GGUF model loaded successfully!")
                return True

            # -- AirLLM / HuggingFace --------------------------------------
            if progress_callback:
                progress_callback("Importing AirLLM...")

            ensure_airllm_path()
            try:
                from airllm import AutoModel  # noqa: F811
            except ImportError:
                raise ImportError(self.MISSING_AIRLLM)
            
            if progress_callback:
                progress_callback(f"Loading model: {model_path}")
            
            # Compression settings
            kwargs = {}
            if compression == "4bit":
                kwargs["compression"] = "4bit"
            elif compression == "8bit":
                kwargs["compression"] = "8bit"
            
            # For Ollama models, convert the name to HuggingFace equivalent
            if model_type == "ollama":
                if progress_callback:
                    progress_callback(f"Converting Ollama model to HuggingFace: {model_path}")
                # Ollama to HuggingFace model mapping
                ollama_to_hf = {
                    "llama3.2:1b": "meta-llama/Llama-3.2-1B",
                    "llama3.2:3b": "meta-llama/Llama-3.2-3B",
                    "llama3.2:latest": "meta-llama/Llama-3.2-3B",
                    "llama3.1:8b": "meta-llama/Llama-3.1-8B",
                    "llama3.1:latest": "meta-llama/Llama-3.1-8B",
                    "llama2:7b": "meta-llama/Llama-2-7b-hf",
                    "llama2:13b": "meta-llama/Llama-2-13b-hf",
                    "mistral:7b": "mistralai/Mistral-7B-v0.1",
                    "mistral:latest": "mistralai/Mistral-7B-v0.1",
                    "codellama:7b": "codellama/CodeLlama-7b-hf",
                    "phi3:mini": "microsoft/phi-3-mini-4k-instruct",
                    "phi3:latest": "microsoft/phi-3-mini-4k-instruct",
                    "gemma2:2b": "google/gemma-2-2b",
                    "gemma2:latest": "google/gemma-2-2b",
                    "qwen2.5:7b": "Qwen/Qwen2.5-7B",
                    "qwen2.5:latest": "Qwen/Qwen2.5-7B",
                }
                # Exact name (e.g., llama3.2:latest) or first:last segment
                base_model = model_path
                if ":" in model_path:
                    parts = model_path.split(":")
                    if len(parts) >= 2:
                        base_model = f"{parts[0]}:{parts[-1]}"
                model_path = ollama_to_hf.get(model_path, ollama_to_hf.get(base_model, model_path))
                if progress_callback:
                    progress_callback(f"Using HuggingFace model: {model_path}")
            
            # Load the HuggingFace model with AirLLM
            self.model = AutoModel.from_pretrained(
                model_path,
                **kwargs
            )
            self.model_name = model_path
            self.model_path = model_path
            self._model_type = "airllm"
            
            if progress_callback:
                progress_callback("Model loaded successfully!")
            
            return True
            
        except ImportError:
            # Re-raise ImportError with markers for the caller (UI)
            raise
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error loading model: {e}")
            return False
        finally:
            with self._lock:
                self._loading = False
    
    def unload_model(self) -> bool:
        """Unloads the model from memory."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
                self.model_name = None
                
                # Clear cache
                import gc
                gc.collect()
                
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
                
            return True
        except Exception:
            return False
    
    def generate(self, prompt: str, 
                 max_new_tokens: int = 256,
                 temperature: float = 0.7,
                 top_p: float = 0.9,
                 stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Generates text using the loaded model.
        
        Args:
            prompt: Input text
            max_new_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
            top_p: Top-p (nucleus) sampling
            stream_callback: Callback for generated tokens (streaming)
        """
        if not self.is_model_loaded():
            return "Error: No model loaded"
        
        try:
            # For GGUF models (llama-cpp)
            if hasattr(self, '_model_type') and self._model_type == "gguf":
                response = ""
                for token in self.model(
                    prompt,
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stream=True
                ):
                    text = token["choices"][0]["text"]
                    response += text
                    if stream_callback:
                        stream_callback(text)
                return response
            
            # For AirLLM models (HuggingFace)
            # Tokenize the prompt
            input_ids = self.model.tokenizer(
                prompt, 
                return_tensors="pt"
            ).input_ids
            
            # Generate the response
            generation_output = self.model.generate(
                input_ids=input_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                use_cache=True,
                return_dict_in_generate=True
            )
            
            # Decode the output
            output_ids = generation_output.sequences[0]
            response = self.model.tokenizer.decode(
                output_ids[len(input_ids[0]):], 
                skip_special_tokens=True
            )
            
            if stream_callback:
                # Simulate streaming (AirLLM doesn't support native streaming)
                for char in response:
                    stream_callback(char)
            
            return response
            
        except Exception as e:
            return f"Generation error: {e}"
    
    def chat(self, message: str, 
             system_prompt: str = "You are a helpful assistant.",
             max_new_tokens: int = 256,
             stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Simplified chat interface.
        
        Args:
            message: User message
            system_prompt: System prompt
            max_new_tokens: Maximum tokens
            stream_callback: Callback for streaming
        """
        # Format as chat
        full_prompt = f"""### System:
{system_prompt}

### User:
{message}

### Assistant:
"""
        return self.generate(
            full_prompt, 
            max_new_tokens=max_new_tokens,
            stream_callback=stream_callback
        )
    
    @staticmethod
    def get_supported_models() -> list:
        """Returns a list of recommended models for use with AirLLM."""
        return [
            {
                "name": "meta-llama/Llama-2-7b-hf",
                "description": "Llama 2 7B - Good balance",
                "size": "~13GB"
            },
            {
                "name": "meta-llama/Llama-2-13b-hf", 
                "description": "Llama 2 13B - Higher quality",
                "size": "~26GB"
            },
            {
                "name": "mistralai/Mistral-7B-v0.1",
                "description": "Mistral 7B - Fast and efficient",
                "size": "~14GB"
            },
            {
                "name": "microsoft/phi-2",
                "description": "Phi-2 - Small but powerful",
                "size": "~5GB"
            },
            {
                "name": "Qwen/Qwen2.5-7B",
                "description": "Qwen 2.5 7B - Multilingual",
                "size": "~14GB"
            },
            {
                "name": "google/gemma-2-2b",
                "description": "Gemma 2 2B - Compact",
                "size": "~4GB"
            },
        ]
    
    @staticmethod
    def check_requirements() -> dict:
        """Checks system requirements for AirLLM."""
        result = {
            "airllm_installed": False,
            "airllm_import_error": None,
            "torch_installed": False,
            "cuda_available": False,
            "gpu_name": None,
            "gpu_memory": None
        }

        ok, err = try_import_airllm()
        result["airllm_installed"] = ok
        result["airllm_import_error"] = err
        
        try:
            import torch
            result["torch_installed"] = True
            result["cuda_available"] = torch.cuda.is_available()
            
            if result["cuda_available"]:
                result["gpu_name"] = torch.cuda.get_device_name(0)
                result["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
        except ImportError:
            pass
        
        return result

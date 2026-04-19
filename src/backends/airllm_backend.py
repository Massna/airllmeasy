"""AirLLM Backend - Para execução de modelos grandes com pouca memória."""
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
    """Lê caminhos de modelos no settings.json do LM Studio (pastas personalizadas)."""
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
    """Interface com AirLLM para executar modelos grandes com memória limitada."""
    
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
        """Diretório raiz de modelos do Ollama (manifests, blobs)."""
        env = os.environ.get("OLLAMA_MODELS", "").strip()
        if env:
            return Path(env)
        return Path.home() / ".ollama" / "models"
    
    def _lmstudio_candidate_roots(self) -> List[Path]:
        """Pastas onde o LM Studio costuma guardar GGUF (varia por versão)."""
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
        """Lista modelos Ollama. Preferimos a API (fiável); disco em fallback."""
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
        """Lista GGUFs em todas as pastas típicas do LM Studio."""
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
        """Lista todos os modelos locais disponíveis para execução."""
        models = []
        models.extend(self.list_ollama_models())
        models.extend(self.list_lmstudio_models())
        return models
    
    def is_model_loaded(self) -> bool:
        """Verifica se um modelo está carregado."""
        return self.model is not None
    
    def get_loaded_model_name(self) -> Optional[str]:
        """Retorna o nome do modelo carregado."""
        return self.model_name
    
    def load_model(self, model_path: str, 
                   progress_callback: Optional[Callable[[str], None]] = None,
                   compression: str = "4bit",
                   model_type: str = "huggingface") -> bool:
        """
        Carrega um modelo usando AirLLM.
        
        Args:
            model_path: Caminho local ou ID do HuggingFace (ex: "meta-llama/Llama-2-7b-hf")
            progress_callback: Callback para status de carregamento
            compression: Tipo de compressão ("4bit", "8bit", ou "none")
            model_type: Tipo do modelo ("huggingface", "gguf", "ollama")
        """
        with self._lock:
            if self._loading:
                return False
            self._loading = True
        
        try:
            if progress_callback:
                progress_callback("Importando AirLLM...")

            ensure_airllm_path()
            from airllm import AutoModel
            
            if progress_callback:
                progress_callback(f"Carregando modelo: {model_path}")
            
            # Configurações de compressão
            kwargs = {}
            if compression == "4bit":
                kwargs["compression"] = "4bit"
            elif compression == "8bit":
                kwargs["compression"] = "8bit"
            
            # Para modelos GGUF (LMStudio), precisamos converter ou usar llama-cpp
            if model_type == "gguf":
                if progress_callback:
                    progress_callback("Carregando modelo GGUF com llama-cpp-python...")
                
                try:
                    from llama_cpp import Llama
                    self.model = Llama(
                        model_path=model_path,
                        n_ctx=4096,
                        n_threads=4,
                        verbose=False
                    )
                    self.model_name = model_path
                    self.model_path = model_path
                    self._model_type = "gguf"
                    
                    if progress_callback:
                        progress_callback("Modelo GGUF carregado com sucesso!")
                    return True
                except ImportError:
                    if progress_callback:
                        progress_callback("Instalando llama-cpp-python...")
                    # Tenta instalar llama-cpp-python
                    import subprocess
                    subprocess.run(["pip", "install", "llama-cpp-python"], check=True)
                    from llama_cpp import Llama
                    self.model = Llama(
                        model_path=model_path,
                        n_ctx=4096,
                        n_threads=4,
                        verbose=False
                    )
                    self.model_name = model_path
                    self.model_path = model_path
                    self._model_type = "gguf"
                    
                    if progress_callback:
                        progress_callback("Modelo GGUF carregado com sucesso!")
                    return True
            
            # Para modelos Ollama, convertemos o nome para HuggingFace equivalente
            if model_type == "ollama":
                if progress_callback:
                    progress_callback(f"Convertendo modelo Ollama para HuggingFace: {model_path}")
                # Mapeamento de modelos Ollama para HuggingFace
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
                # Nome exato (ex.: llama3.2:latest) ou primeiro:último segmento
                base_model = model_path
                if ":" in model_path:
                    parts = model_path.split(":")
                    if len(parts) >= 2:
                        base_model = f"{parts[0]}:{parts[-1]}"
                model_path = ollama_to_hf.get(model_path, ollama_to_hf.get(base_model, model_path))
                if progress_callback:
                    progress_callback(f"Usando modelo HuggingFace: {model_path}")
            
            # Carrega o modelo HuggingFace com AirLLM
            self.model = AutoModel.from_pretrained(
                model_path,
                **kwargs
            )
            self.model_name = model_path
            self.model_path = model_path
            self._model_type = "airllm"
            
            if progress_callback:
                progress_callback("Modelo carregado com sucesso!")
            
            return True
            
        except ImportError as e:
            if progress_callback:
                progress_callback(f"Erro: AirLLM não instalado - {e}")
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(f"Erro ao carregar modelo: {e}")
            return False
        finally:
            with self._lock:
                self._loading = False
    
    def unload_model(self) -> bool:
        """Descarrega o modelo da memória."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
                self.model_name = None
                
                # Limpa cache
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
        Gera texto usando o modelo carregado.
        
        Args:
            prompt: Texto de entrada
            max_new_tokens: Máximo de tokens a gerar
            temperature: Temperatura para sampling
            top_p: Top-p (nucleus) sampling
            stream_callback: Callback para tokens gerados (streaming)
        """
        if not self.is_model_loaded():
            return "Erro: Nenhum modelo carregado"
        
        try:
            # Para modelos GGUF (llama-cpp)
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
            
            # Para modelos AirLLM (HuggingFace)
            # Tokeniza o prompt
            input_ids = self.model.tokenizer(
                prompt, 
                return_tensors="pt"
            ).input_ids
            
            # Gera a resposta
            generation_output = self.model.generate(
                input_ids=input_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                use_cache=True,
                return_dict_in_generate=True
            )
            
            # Decodifica a saída
            output_ids = generation_output.sequences[0]
            response = self.model.tokenizer.decode(
                output_ids[len(input_ids[0]):], 
                skip_special_tokens=True
            )
            
            if stream_callback:
                # Simula streaming (AirLLM não suporta streaming nativo)
                for char in response:
                    stream_callback(char)
            
            return response
            
        except Exception as e:
            return f"Erro na geração: {e}"
    
    def chat(self, message: str, 
             system_prompt: str = "Você é um assistente útil.",
             max_new_tokens: int = 256,
             stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Interface de chat simplificada.
        
        Args:
            message: Mensagem do usuário
            system_prompt: Prompt de sistema
            max_new_tokens: Máximo de tokens
            stream_callback: Callback para streaming
        """
        # Formata como chat
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
        """Retorna lista de modelos recomendados para usar com AirLLM."""
        return [
            {
                "name": "meta-llama/Llama-2-7b-hf",
                "description": "Llama 2 7B - Bom equilíbrio",
                "size": "~13GB"
            },
            {
                "name": "meta-llama/Llama-2-13b-hf", 
                "description": "Llama 2 13B - Maior qualidade",
                "size": "~26GB"
            },
            {
                "name": "mistralai/Mistral-7B-v0.1",
                "description": "Mistral 7B - Rápido e eficiente",
                "size": "~14GB"
            },
            {
                "name": "microsoft/phi-2",
                "description": "Phi-2 - Pequeno mas poderoso",
                "size": "~5GB"
            },
            {
                "name": "Qwen/Qwen2.5-7B",
                "description": "Qwen 2.5 7B - Multilingual",
                "size": "~14GB"
            },
            {
                "name": "google/gemma-2-2b",
                "description": "Gemma 2 2B - Compacto",
                "size": "~4GB"
            },
        ]
    
    @staticmethod
    def check_requirements() -> dict:
        """Verifica requisitos do sistema para AirLLM."""
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

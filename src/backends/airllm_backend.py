"""AirLLM Backend - Para execução de modelos grandes com pouca memória."""
import os
import threading
import subprocess
import platform
from typing import Optional, Callable, Generator, List, Dict
from pathlib import Path

from ..utils.airllm_import import ensure_airllm_path


class AirLLMBackend:
    """Interface com AirLLM para executar modelos grandes com memória limitada."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name = None
        self.model_path = None
        self._loading = False
        self._lock = threading.Lock()
        self._ollama_models_dir = self._get_ollama_models_dir()
        self._lmstudio_models_dir = self._get_lmstudio_models_dir()
    
    def _get_ollama_models_dir(self) -> Path:
        """Obtém o diretório de modelos do Ollama."""
        if platform.system() == "Windows":
            return Path(os.environ.get("USERPROFILE", "")) / ".ollama" / "models"
        elif platform.system() == "Darwin":
            return Path.home() / ".ollama" / "models"
        else:
            return Path.home() / ".ollama" / "models"
    
    def _get_lmstudio_models_dir(self) -> Path:
        """Obtém o diretório de modelos do LMStudio."""
        if platform.system() == "Windows":
            return Path(os.environ.get("USERPROFILE", "")) / ".cache" / "lm-studio" / "models"
        elif platform.system() == "Darwin":
            return Path.home() / ".cache" / "lm-studio" / "models"
        else:
            return Path.home() / ".cache" / "lm-studio" / "models"
    
    def list_ollama_models(self) -> List[Dict]:
        """Lista modelos baixados pelo Ollama que podem ser usados."""
        models = []
        manifests_dir = self._ollama_models_dir / "manifests" / "registry.ollama.ai" / "library"
        
        if manifests_dir.exists():
            for model_dir in manifests_dir.iterdir():
                if model_dir.is_dir():
                    for version in model_dir.iterdir():
                        models.append({
                            "name": f"{model_dir.name}:{version.name}",
                            "source": "ollama",
                            "path": str(model_dir),
                            "type": "ollama"
                        })
        return models
    
    def list_lmstudio_models(self) -> List[Dict]:
        """Lista modelos GGUF baixados pelo LMStudio."""
        models = []
        if self._lmstudio_models_dir.exists():
            for org_dir in self._lmstudio_models_dir.iterdir():
                if org_dir.is_dir():
                    for model_dir in org_dir.iterdir():
                        if model_dir.is_dir():
                            gguf_files = list(model_dir.glob("*.gguf"))
                            for gguf in gguf_files:
                                models.append({
                                    "name": f"{org_dir.name}/{model_dir.name}/{gguf.stem}",
                                    "source": "lmstudio",
                                    "path": str(gguf),
                                    "type": "gguf",
                                    "size": gguf.stat().st_size
                                })
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
                    "llama3.1:8b": "meta-llama/Llama-3.1-8B",
                    "llama2:7b": "meta-llama/Llama-2-7b-hf",
                    "llama2:13b": "meta-llama/Llama-2-13b-hf",
                    "mistral:7b": "mistralai/Mistral-7B-v0.1",
                    "codellama:7b": "codellama/CodeLlama-7b-hf",
                    "phi3:mini": "microsoft/phi-3-mini-4k-instruct",
                    "gemma2:2b": "google/gemma-2-2b",
                    "qwen2.5:7b": "Qwen/Qwen2.5-7B",
                }
                # Remove tag de versão para buscar
                base_model = model_path.split(":")[0] + ":" + model_path.split(":")[-1] if ":" in model_path else model_path
                model_path = ollama_to_hf.get(base_model, model_path)
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
            "torch_installed": False,
            "cuda_available": False,
            "gpu_name": None,
            "gpu_memory": None
        }

        ensure_airllm_path()
        try:
            import airllm
            result["airllm_installed"] = True
        except ImportError:
            pass
        
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

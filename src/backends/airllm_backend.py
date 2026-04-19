"""AirLLM Backend - Para execução de modelos grandes com pouca memória."""
import os
import threading
from typing import Optional, Callable, Generator
from pathlib import Path


class AirLLMBackend:
    """Interface com AirLLM para executar modelos grandes com memória limitada."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name = None
        self._loading = False
        self._lock = threading.Lock()
    
    def is_model_loaded(self) -> bool:
        """Verifica se um modelo está carregado."""
        return self.model is not None
    
    def get_loaded_model_name(self) -> Optional[str]:
        """Retorna o nome do modelo carregado."""
        return self.model_name
    
    def load_model(self, model_path: str, 
                   progress_callback: Optional[Callable[[str], None]] = None,
                   compression: str = "4bit") -> bool:
        """
        Carrega um modelo usando AirLLM.
        
        Args:
            model_path: Caminho local ou ID do HuggingFace (ex: "meta-llama/Llama-2-7b-hf")
            progress_callback: Callback para status de carregamento
            compression: Tipo de compressão ("4bit", "8bit", ou "none")
        """
        with self._lock:
            if self._loading:
                return False
            self._loading = True
        
        try:
            if progress_callback:
                progress_callback("Importando AirLLM...")
            
            from airllm import AutoModel
            
            if progress_callback:
                progress_callback(f"Carregando modelo: {model_path}")
            
            # Configurações de compressão
            kwargs = {}
            if compression == "4bit":
                kwargs["compression"] = "4bit"
            elif compression == "8bit":
                kwargs["compression"] = "8bit"
            
            # Carrega o modelo
            self.model = AutoModel.from_pretrained(
                model_path,
                **kwargs
            )
            self.model_name = model_path
            
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

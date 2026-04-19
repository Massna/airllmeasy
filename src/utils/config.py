"""Gerenciador de configurações da aplicação."""
import json
import os
from pathlib import Path
from typing import Any, Optional


class Config:
    """Gerencia as configurações da aplicação."""
    
    DEFAULT_CONFIG = {
        "backend": "ollama",  # "ollama" (A) ou "lmstudio" (B)
        "execution_backend": "airllm",  # "airllm", "ollama", ou "lmstudio"
        "ollama_url": "http://localhost:11434",
        "lmstudio_url": "http://localhost:1234",
        "theme": "dark",
        "language": "pt-BR",
        "max_tokens": 512,
        "temperature": 0.7,
        "airllm_compression": "4bit",  # "4bit", "8bit", "none"
        "last_model": None,
        "window_geometry": None,
    }
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Diretório de configuração padrão
            if os.name == "nt":  # Windows
                app_data = os.environ.get("APPDATA", "")
                self.config_path = Path(app_data) / "AILocalManager" / "config.json"
            else:  # Linux/Mac
                self.config_path = Path.home() / ".config" / "ailocalmanager" / "config.json"
        
        self._config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> bool:
        """Carrega configurações do arquivo."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    # Merge com defaults (mantém novos campos)
                    self._config.update(saved_config)
                return True
            return False
        except (json.JSONDecodeError, IOError):
            return False
    
    def save(self) -> bool:
        """Salva configurações no arquivo."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor de configuração."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Define um valor de configuração."""
        self._config[key] = value
    
    def reset(self) -> None:
        """Reseta para configurações padrão."""
        self._config = self.DEFAULT_CONFIG.copy()
    
    @property
    def download_backend(self) -> str:
        """Backend atual para download de modelos (A=ollama, B=lmstudio)."""
        return self._config.get("backend", "ollama")
    
    @download_backend.setter
    def download_backend(self, value: str) -> None:
        if value in ("ollama", "lmstudio"):
            self._config["backend"] = value
    
    @property
    def ollama_url(self) -> str:
        return self._config.get("ollama_url", "http://localhost:11434")
    
    @ollama_url.setter
    def ollama_url(self, value: str) -> None:
        self._config["ollama_url"] = value
    
    @property
    def lmstudio_url(self) -> str:
        return self._config.get("lmstudio_url", "http://localhost:1234")
    
    @lmstudio_url.setter
    def lmstudio_url(self, value: str) -> None:
        self._config["lmstudio_url"] = value
    
    @property
    def theme(self) -> str:
        return self._config.get("theme", "dark")
    
    @theme.setter
    def theme(self, value: str) -> None:
        if value in ("dark", "light"):
            self._config["theme"] = value
    
    @property
    def max_tokens(self) -> int:
        return self._config.get("max_tokens", 512)
    
    @max_tokens.setter
    def max_tokens(self, value: int) -> None:
        self._config["max_tokens"] = max(1, min(4096, value))
    
    @property
    def temperature(self) -> float:
        return self._config.get("temperature", 0.7)
    
    @temperature.setter
    def temperature(self, value: float) -> None:
        self._config["temperature"] = max(0.0, min(2.0, value))
    
    @property
    def airllm_compression(self) -> str:
        return self._config.get("airllm_compression", "4bit")
    
    @airllm_compression.setter
    def airllm_compression(self, value: str) -> None:
        if value in ("4bit", "8bit", "none"):
            self._config["airllm_compression"] = value

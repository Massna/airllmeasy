"""Configuration manager for the application."""
import json
import os
from pathlib import Path
from typing import Any, Optional


class Config:
    """Manages application settings."""
    
    DEFAULT_CONFIG = {
        "backend": "ollama",  # "ollama" (A) or "lmstudio" (B)
        "execution_backend": "airllm",  # "airllm", "ollama", or "lmstudio"
        "ollama_url": "http://localhost:11434",
        "lmstudio_url": "http://localhost:1234",
        "theme": "dark",
        "language": "en",
        "max_tokens": 512,
        "temperature": 0.7,
        "airllm_compression": "4bit",  # "4bit", "8bit", "none"
        "airllm_packages_path": None,  # site-packages where the airllm package is installed (optional)
        "last_model": None,
        "window_geometry": None,
    }
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default configuration directory
            if os.name == "nt":  # Windows
                app_data = os.environ.get("APPDATA", "")
                self.config_path = Path(app_data) / "AILocalManager" / "config.json"
            else:  # Linux/Mac
                self.config_path = Path.home() / ".config" / "ailocalmanager" / "config.json"
        
        self._config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> bool:
        """Load settings from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    # Merge with defaults (preserves new fields)
                    self._config.update(saved_config)
                return True
            return False
        except (json.JSONDecodeError, IOError):
            return False
    
    def save(self) -> bool:
        """Save settings to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config[key] = value
    
    def reset(self) -> None:
        """Reset to default settings."""
        self._config = self.DEFAULT_CONFIG.copy()
    
    @property
    def download_backend(self) -> str:
        """Current backend for model downloads (A=ollama, B=lmstudio)."""
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

    @property
    def airllm_packages_path(self) -> Optional[str]:
        """site-packages folder (or venv root) where pip installed the airllm package."""
        v = self._config.get("airllm_packages_path")
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @airllm_packages_path.setter
    def airllm_packages_path(self, value: Optional[str]) -> None:
        if value is None or not str(value).strip():
            self._config["airllm_packages_path"] = None
        else:
            self._config["airllm_packages_path"] = str(value).strip()

import json
import os
from pathlib import Path
from typing import Dict, Any

class I18n:
    _instance = None
    _translations: Dict[str, Any] = {}
    _current_lang = "en"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(I18n, cls).__new__(cls)
        return cls._instance

    def load_language(self, lang_code: str):
        """Load translations for a specific language code."""
        self._current_lang = lang_code
        
        # Try to load from src/utils/languages/{lang_code}.json
        lang_file = Path(__file__).parent / "languages" / f"{lang_code}.json"
        
        if not lang_file.exists():
            # Fallback to English if file not found
            if lang_code != "en":
                self.load_language("en")
            return

        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
        except Exception as e:
            print(f"Error loading language {lang_code}: {e}")
            if lang_code != "en":
                self.load_language("en")

    def t(self, key: str, default: str = None) -> str:
        """Translate a key. Supports nested keys with dot notation (e.g. 'menu.file')."""
        default = default or key
        keys = key.split(".")
        val = self._translations
        
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        
        return str(val) if val is not None else default

# Global instance
_i18n_instance = I18n()

def t(key: str, default: str = None) -> str:
    return _i18n_instance.t(key, default)

def load_language(lang_code: str):
    _i18n_instance.load_language(lang_code)

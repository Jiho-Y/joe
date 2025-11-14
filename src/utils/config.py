"""
Configuration management for Research Paper Manager.
Handles API keys, preferences, and application settings.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Application configuration manager."""

    DEFAULT_CONFIG = {
        "semantic_scholar": {
            "enabled": True,
            "api_key": None,  # Optional API key for higher rate limits
            "timeout": 10,  # seconds
            "max_retries": 2,
        },
        "search": {
            "default_limit": 100,
            "enable_fts5": True,
            "enable_fallback": True,
        },
        "pdf_processing": {
            "max_pages_for_metadata": 3,
            "max_pages_for_full_text": 50,
            "extract_references": True,
        },
        "keywords": {
            "default_method": "yake",  # "yake" or "keybert"
            "top_n": 10,
        },
        "ui": {
            "theme": "light",  # "light" or "dark"
            "show_abstract_length": True,
            "auto_refresh": True,
        },
    }

    def __init__(self, config_path: str = "data/config.json"):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(exist_ok=True, parents=True)

        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)

                # Merge with defaults (in case new settings were added)
                config = self.DEFAULT_CONFIG.copy()
                self._deep_update(config, loaded)

                return config

            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self.save()
            return self.DEFAULT_CONFIG.copy()

    def _deep_update(self, base: dict, update: dict):
        """Recursively update nested dict."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key_path: str, default=None) -> Any:
        """
        Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., "semantic_scholar.api_key")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """
        Set configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., "semantic_scholar.api_key")
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value

        # Auto-save
        self.save()

    # Convenience methods for common settings

    def get_semantic_scholar_api_key(self) -> Optional[str]:
        """Get Semantic Scholar API key."""
        return self.get("semantic_scholar.api_key")

    def set_semantic_scholar_api_key(self, api_key: Optional[str]):
        """Set Semantic Scholar API key."""
        self.set("semantic_scholar.api_key", api_key)

    def is_semantic_scholar_enabled(self) -> bool:
        """Check if Semantic Scholar integration is enabled."""
        return self.get("semantic_scholar.enabled", True)

    def enable_semantic_scholar(self, enabled: bool):
        """Enable or disable Semantic Scholar integration."""
        self.set("semantic_scholar.enabled", enabled)

    def get_search_limit(self) -> int:
        """Get default search result limit."""
        return self.get("search.default_limit", 100)

    def get_keyword_method(self) -> str:
        """Get default keyword extraction method."""
        return self.get("keywords.default_method", "yake")

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self.config.copy()


# Global config instance
_config = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config():
    """Reload configuration from file."""
    global _config
    _config = Config()
    return _config

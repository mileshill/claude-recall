"""
Unified configuration management for analytics features.

Provides centralized configuration with:
- JSON file loading with defaults
- Environment variable overrides
- Dot-notation access
- Feature enable/disable flags
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


class AnalyticsConfig:
    """
    Singleton configuration manager for analytics features.

    Usage:
        from metrics.config import config

        if config.is_enabled('telemetry'):
            # ... telemetry code

        log_path = config.get('telemetry.log_path')
    """

    _instance = None
    _config = None
    _config_loaded = False

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: Optional[Path] = None):
        """
        Load configuration from file.

        Args:
            config_path: Path to analytics_config.json (optional)
        """
        if self._config_loaded:
            return  # Already loaded

        if config_path is None:
            # Default path
            config_path = Path(__file__).parent.parent.parent / "config" / "analytics_config.json"

        if not config_path.exists():
            # Use defaults
            self._config = self._get_defaults()
        else:
            try:
                with open(config_path) as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
                self._config = self._get_defaults()

        # Apply environment variable overrides
        self._apply_env_overrides()

        self._config_loaded = True

    def _get_defaults(self) -> dict:
        """
        Get default configuration.

        Returns:
            Dictionary with default settings
        """
        return {
            "version": "1.0.0",
            "telemetry": {
                "enabled": True,
                "log_path": "~/.claude/context/sessions/recall_analytics.jsonl",
                "sampling_rate": 1.0,
                "batch_size": 10,
                "batch_flush_interval_sec": 5.0,
                "pii_redaction": True,
                "buffer_writes": True
            },
            "impact_analysis": {
                "enabled": True,
                "log_path": "~/.claude/context/sessions/context_impact.jsonl",
                "auto_analyze_on_session_end": True,
                "min_recall_events": 1
            },
            "quality_scoring": {
                "enabled": False,
                "mode": "llm",
                "api_key_env": "ANTHROPIC_API_KEY",
                "model": "claude-3-haiku-20240307",
                "sampling_rate": 0.1,
                "log_path": "~/.claude/context/sessions/quality_scores.jsonl",
                "fallback_to_heuristic": True,
                "async_evaluation": True,
                "timeout_sec": 30,
                "monthly_budget_usd": 5.0
            },
            "quality_checks": {
                "enabled": True,
                "schedule": "daily",
                "log_path": "~/.claude/context/sessions/quality_check_log.jsonl",
                "checks": {
                    "low_relevance": {
                        "enabled": True,
                        "threshold": 0.4,
                        "window_size": 100
                    },
                    "high_latency": {
                        "enabled": True,
                        "threshold_ms": 100.0,
                        "p95_threshold_ms": 200.0
                    },
                    "no_results": {
                        "enabled": True,
                        "max_rate": 0.15
                    },
                    "embedding_drift": {
                        "enabled": True,
                        "threshold": 0.2,
                        "min_samples": 20
                    },
                    "false_positive": {
                        "enabled": True,
                        "low_score_threshold": 2.5,
                        "max_rate": 0.1
                    },
                    "usage_anomaly": {
                        "enabled": True,
                        "std_dev_threshold": 3.0
                    },
                    "index_health": {
                        "enabled": True
                    }
                },
                "alert_methods": ["log", "stderr"]
            },
            "reporting": {
                "enabled": True,
                "default_period_days": 30,
                "default_format": "markdown",
                "output_dir": "~/.claude/context/reports",
                "include_charts": False
            },
            "retention": {
                "log_retention_days": 90,
                "auto_cleanup": False
            }
        }

    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Check for API key
        api_key_env = self._config.get("quality_scoring", {}).get("api_key_env", "ANTHROPIC_API_KEY")
        if api_key_env in os.environ:
            if "quality_scoring" not in self._config:
                self._config["quality_scoring"] = {}
            self._config["quality_scoring"]["api_key"] = os.environ[api_key_env]

        # Allow disabling features via env vars
        # RECALL_ANALYTICS_TELEMETRY_ENABLED=false
        if "RECALL_ANALYTICS_TELEMETRY_ENABLED" in os.environ:
            value = os.environ["RECALL_ANALYTICS_TELEMETRY_ENABLED"].lower()
            self._config["telemetry"]["enabled"] = value in ("true", "1", "yes")

        if "RECALL_ANALYTICS_QUALITY_SCORING_ENABLED" in os.environ:
            value = os.environ["RECALL_ANALYTICS_QUALITY_SCORING_ENABLED"].lower()
            self._config["quality_scoring"]["enabled"] = value in ("true", "1", "yes")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with dot notation.

        Args:
            key: Configuration key (e.g., "telemetry.enabled")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if not self._config_loaded:
            self.load()

        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    def set(self, key: str, value: Any):
        """
        Set configuration value (runtime only, not persisted).

        Args:
            key: Configuration key (dot notation)
            value: Value to set
        """
        if not self._config_loaded:
            self.load()

        keys = key.split('.')
        config = self._config

        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set value
        config[keys[-1]] = value

    def is_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature: Feature name (e.g., "telemetry", "quality_scoring")

        Returns:
            True if enabled, False otherwise
        """
        return self.get(f"{feature}.enabled", False)

    def reload(self):
        """Force reload configuration from file."""
        self._config_loaded = False
        self.load()

    def get_all(self) -> dict:
        """
        Get entire configuration dictionary.

        Returns:
            Full configuration
        """
        if not self._config_loaded:
            self.load()
        return self._config.copy()


# Singleton instance for import
config = AnalyticsConfig()

# Auto-load on import
config.load()

"""Configuration handling for Paper Loupe."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast

import yaml
from rich.console import Console

console = Console()

# Environment variable names for API keys
ENV_OPENAI_API_KEY = "PAPER_LOUPE_OPENAI_API_KEY"
ENV_ANTHROPIC_API_KEY = "PAPER_LOUPE_ANTHROPIC_API_KEY"


def load_config(config_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = cast(Dict[str, Any], yaml.safe_load(f))
        return config
    except FileNotFoundError:
        console.print(
            f"[bold red]Error:[/bold red] Configuration file not found at {config_path}"
        )
        return None
    except yaml.YAMLError as e:
        console.print(
            f"[bold red]Error:[/bold red] Invalid YAML in configuration file: {e}"
        )
        return None


def validate_config(config: Optional[Dict[str, Any]]) -> bool:
    """Validate configuration structure."""
    if not config:
        return False

    # Check for required sections
    required_sections = ["questions"]

    for section in required_sections:
        if section not in config:
            console.print(
                f"[bold red]Error:[/bold red] Missing '{section}' section in configuration"
            )
            return False

    # Validate questions section
    if not isinstance(config["questions"], list) or not config["questions"]:
        console.print(
            "[bold red]Error:[/bold red] 'questions' must be a non-empty list"
        )
        return False

    return True


def create_default_config_dir() -> Path:
    """Create default configuration directory if it doesn't exist."""
    config_dir = Path.home() / ".config" / "paper-loupe"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_api_key(config: Dict[str, Any], provider: str) -> Optional[str]:
    """Get API key for a provider from config or environment variables.

    Args:
        config: The loaded configuration dictionary
        provider: The provider name ('openai' or 'anthropic')

    Returns:
        The API key if found, None otherwise
    """
    # Try to get from environment variables first
    env_var_name = {
        "openai": ENV_OPENAI_API_KEY,
        "anthropic": ENV_ANTHROPIC_API_KEY,
    }.get(provider)

    if env_var_name and os.environ.get(env_var_name):
        return cast(Optional[str], os.environ.get(env_var_name))

    # Try to get from config file
    if "api_keys" in config and provider in config["api_keys"]:
        return cast(Optional[str], config["api_keys"][provider])

    return None

"""Configuration handling for Paper Loupe."""

from pathlib import Path
from typing import Any, Dict, Optional, Union, cast

import yaml
from rich.console import Console

console = Console()


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

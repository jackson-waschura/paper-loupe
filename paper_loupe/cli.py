"""Command-line interface for Paper Loupe."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from paper_loupe import __version__
from paper_loupe.models import SUPPORTED_MODELS

console = Console()

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "paper-loupe" / "config.yaml"
DEFAULT_CREDENTIALS_PATH = Path.home() / ".config" / "paper-loupe" / "credentials.json"
DEFAULT_SINCE_DAYS = 30


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """Paper Loupe - Manage and prioritize your research paper backlog."""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration YAML file",
)
def setup(config: Optional[str]) -> None:
    """Setup Paper Loupe with Gmail API authentication."""
    console.print(Panel("Setting up Paper Loupe", style="green"))
    console.print(
        "This command would guide you through the OAuth consent flow for Gmail API."
    )
    console.print("For now, this is just a placeholder for the actual implementation.")
    console.print(f"Would create credentials at: {DEFAULT_CREDENTIALS_PATH}")


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration YAML file",
)
@click.option(
    "--since",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Process emails since this date (YYYY-MM-DD)",
)
@click.option(
    "--model",
    default="gpt-4o",
    type=click.Choice(list(SUPPORTED_MODELS.keys())),
    help="LLM model to use for relevance scoring",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Path to save the ranked papers",
)
def process(
    config: Optional[str], since: Optional[datetime], model: str, output: Optional[str]
) -> None:
    """Process emails and rank papers based on relevance to your questions."""
    # Use default date if not specified (30 days ago)
    if not since:
        since = datetime.now() - timedelta(days=DEFAULT_SINCE_DAYS)
        since_str = since.strftime("%Y-%m-%d")
    else:
        since_str = since.strftime("%Y-%m-%d")

    # Use default config path if not specified
    config_path = config if config else DEFAULT_CONFIG_PATH

    # In a real implementation, we would load and validate the config here
    console.print(Panel("Paper Loupe - Processing Mode", style="blue"))
    console.print(f"[bold]Config:[/bold] {config_path}")
    console.print(f"[bold]Since:[/bold] {since_str}")
    console.print(f"[bold]Model:[/bold] {model}")
    console.print(
        f"[bold]Output:[/bold] {output or 'Not specified (will print to console only)'}"
    )

    # Display the workflow that would happen
    with console.status("[bold green]Processing emails...") as status:
        console.print("1. Would authenticate with Gmail API")
        console.print("2. Would search for Scholar Alert Digest emails")
        console.print("3. Would parse emails to extract paper details")
        console.print("4. Would query arXiv for paper information")
        console.print("5. Would store paper data in a local dataframe")

        status.update("[bold yellow]Analyzing papers...")
        console.print("6. Would analyze paper relevance using LLM")
        console.print("7. Would rank papers based on relevance")

        status.update("[bold blue]Generating results...")
        console.print("8. Would display top 5 most relevant papers")

    console.print(
        Panel("This is a demo version without actual implementation", style="yellow")
    )


@cli.command()
@click.argument("paper_id", required=False)
def show(paper_id: Optional[str]) -> None:
    """Show details of a specific paper or list all papers."""
    if paper_id:
        console.print(f"Would show details for paper with ID: {paper_id}")
    else:
        console.print("Would list all papers in the database")


@cli.command()
@click.argument("model_key", required=False)
def models(model_key: Optional[str]) -> None:
    """List available models or show details for a specific model."""
    if model_key:
        # Show details for a specific model
        if model_key not in SUPPORTED_MODELS:
            console.print(f"[bold red]Error:[/bold red] Model '{model_key}' not found.")
            return

        model = SUPPORTED_MODELS[model_key]
        console.print(Panel(f"[bold]{model['name']}[/bold]", style="blue"))
        console.print(f"[bold]Provider:[/bold] {model['provider'].capitalize()}")
        console.print(f"[bold]Description:[/bold] {model['description']}")
        console.print(f"[bold]Context Window:[/bold] {model['context_window']} tokens")
        console.print(f"[bold]API Model ID:[/bold] {model['api_model_id']}")
        console.print("[bold]Pricing:[/bold]")
        console.print(f"  Input: ${model['pricing']['input']} per 1M tokens")
        console.print(f"  Output: ${model['pricing']['output']} per 1M tokens")
    else:
        # List all available models
        table = Table(title="Available Models")
        table.add_column("Key", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Provider", style="yellow")
        table.add_column("Description")

        for key, model_info in SUPPORTED_MODELS.items():
            table.add_row(
                key,
                model_info["name"],
                model_info["provider"].capitalize(),
                model_info["description"],
            )

        console.print(table)


if __name__ == "__main__":
    cli()

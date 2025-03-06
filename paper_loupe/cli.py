"""Command-line interface for Paper Loupe."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

import click
from google.auth.exceptions import RefreshError  # type: ignore
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
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
    default="gpt-4o-mini",
    type=click.Choice(list(SUPPORTED_MODELS.keys())),
    help="LLM model to use for relevance scoring",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Path to save the ranked papers",
)
@click.option(
    "--top-n",
    "-n",
    type=int,
    default=10,
    help="Number of top papers to display",
)
def process(
    config: Optional[str],
    since: Optional[datetime],
    model: str,
    output: Optional[str],
    top_n: int,
) -> None:
    """Process emails and rank papers based on relevance to your questions."""
    # Use default date if not specified (30 days ago)
    if not since:
        since = datetime.now() - timedelta(days=DEFAULT_SINCE_DAYS)
        since_str = since.strftime("%Y-%m-%d")
    else:
        since_str = since.strftime("%Y-%m-%d")

    # Use default config path if not specified
    config_path: Union[str, Path] = config if config else DEFAULT_CONFIG_PATH

    # Load and validate the configuration
    from paper_loupe.config import load_config, validate_config

    console.print(Panel("Paper Loupe - Processing Mode", style="blue"))
    console.print(f"[bold]Config:[/bold] {config_path}")
    console.print(f"[bold]Since:[/bold] {since_str}")
    console.print(f"[bold]Model:[/bold] {model}")
    console.print(
        f"[bold]Output:[/bold] {output or 'Not specified (will print to console only)'}"
    )

    config_data = load_config(config_path)
    if not config_data or not validate_config(config_data):
        console.print(
            "[bold red]Error:[/bold red] Invalid configuration. Please check your config file."
        )
        return

    # Get research questions from config
    research_questions = config_data.get("questions", [])
    if not research_questions:
        console.print(
            "[bold red]Error:[/bold red] No research questions found in configuration."
        )
        return

    # Implementation of the full workflow
    with console.status("[bold green]Processing emails...") as status:
        # Step 1: Authenticate with Gmail and fetch paper data from emails
        from paper_loupe.email_processor import (
            authenticate_gmail,
            fetch_and_parse_scholar_alerts,
        )

        console.print("1. Authenticating with Gmail API...")
        try:
            gmail_service = authenticate_gmail()
            if not gmail_service:
                console.print(
                    "[bold red]Error:[/bold red] Failed to authenticate with Gmail API. "
                    "Please check your credentials and try again."
                )
                return
        except FileNotFoundError as e:
            console.print(f"[bold red]Credentials Error:[/bold red] {str(e)}")
            return
        except RefreshError as e:
            console.print(
                f"[bold red]Token Error:[/bold red] {str(e)}\n"
                "Your authentication token has expired or been revoked. "
                "The system will attempt to re-authenticate when you run the command again."
            )
            return
        except Exception as e:
            console.print(
                f"[bold red]Authentication Error:[/bold red] {str(e)}\n"
                "If you're experiencing authentication issues, try running the command again. "
                "If the problem persists, you may need to delete your token file and re-authenticate."
            )
            return

        console.print("2. Searching for Scholar Alert Digest emails...")
        console.print("3. Parsing emails to extract paper details...")
        raw_papers = fetch_and_parse_scholar_alerts(gmail_service, since)
        if not raw_papers:
            console.print(
                f"[bold yellow]Warning:[/bold yellow] No papers found in emails since {since_str}."
            )
            return

        console.print(f"Found {len(raw_papers)} papers in emails.")

        # Step 2: Fetch additional paper data from arXiv
        from paper_loupe.arxiv_lookup import search_with_fallback

        status.update("[bold green]Querying arXiv for paper information...")
        console.print("4. Querying arXiv for paper information...")

    # Exit the status context manager before starting the progress display
    enriched_papers = []
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[bold green]Processing papers...", total=len(raw_papers)
        )
        not_found_count = 0
        for paper in raw_papers:
            title = paper.get("title", "")
            authors = paper.get("authors", "").split(", ")

            arxiv_results = search_with_fallback(title, authors)
            if arxiv_results:
                arxiv_paper = arxiv_results[0]
                paper["abstract"] = arxiv_paper.summary.replace("\n", " ")
                paper["arxiv_id"] = arxiv_paper.entry_id.split("/")[-1]
                paper["categories"] = arxiv_paper.categories
                paper["pdf_url"] = arxiv_paper.pdf_url
                enriched_papers.append(paper)
            else:
                not_found_count += 1
            progress.update(task, advance=1)

    # Count papers not found on arXiv
    if not_found_count > 0:
        console.print(
            f"[bold yellow]Note:[/bold yellow] {not_found_count} out of {len(raw_papers)} papers were not found on arXiv."
        )

    # Resume with a new status for the remaining steps
    with console.status("[bold green]Processing data...") as status:
        # Step 3: Store papers in a dataframe
        from paper_loupe.paper_store import (
            create_dataframe,
            deduplicate_papers,
            save_dataframe,
        )

        status.update("[bold green]Storing paper data...")
        console.print("5. Storing paper data in a local dataframe...")

        papers_df = create_dataframe(enriched_papers)
        papers_df = deduplicate_papers(papers_df)

        # Step 4: Analyze papers with LLM
        from paper_loupe.llm_analyzer import batch_analyze

        status.update("[bold yellow]Analyzing papers with LLM...")
        console.print("6. Analyzing paper relevance using LLM...")

        analysis_results: Dict[str, Dict[str, Dict[str, Any]]]
        token_usage: Dict[str, float]
        analysis_results, token_usage = batch_analyze(
            papers_df.to_dict("records"), research_questions, config_data, model
        )

        # Display token usage and cost information
        # Create a cost summary table
        cost_table = Table(title=f"LLM API Usage Summary ({model})")
        cost_table.add_column("Metric", style="cyan")
        cost_table.add_column("Value", style="green", justify="right")

        # Add rows for token usage
        cost_table.add_row(
            "Input Tokens", f"{token_usage.get('total_prompt_tokens', 0):,}"
        )
        cost_table.add_row(
            "Output Tokens", f"{token_usage.get('total_completion_tokens', 0):,}"
        )
        cost_table.add_row("Total Tokens", f"{token_usage.get('total_tokens', 0):,}")

        # Add estimated cost
        estimated_cost = token_usage.get("estimated_cost", 0.0)
        cost_table.add_row("Estimated Cost", f"${estimated_cost:.6f} USD")

        # Display the cost summary
        console.print("\n[bold]LLM API Usage Summary:[/bold]")
        console.print(cost_table)

        # Step 5: Rank papers based on relevance
        from paper_loupe.paper_store import rank_papers

        status.update("[bold blue]Ranking papers...")
        console.print("7. Ranking papers based on relevance...")

        # Extract the average relevance score for each paper
        relevance_scores: Dict[str, float] = {}
        for paper_id, question_scores in analysis_results.items():
            scores = [
                score_data.get("relevance_score", 0)
                for q, score_data in question_scores.items()
            ]
            relevance_scores[paper_id] = sum(scores) / len(scores) if scores else 0

        ranked_df = rank_papers(papers_df, relevance_scores)

        # Step 6: Save results if output path specified
        if output:
            output_path = Path(output)
            console.print(f"8. Saving ranked papers to {output_path}...")
            save_dataframe(ranked_df, output_path)

        # Step 7: Display top papers
        status.update("[bold green]Generating results...")
        console.print("9. Displaying top papers...")

        # Create a nice output table
        table = Table(title="Top Ranked Papers")
        table.add_column("Rank", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Authors", style="yellow")
        table.add_column("Score", style="magenta")
        table.add_column("arxiv ID", style="blue")

        # Display top N papers or all if less than N
        top_papers = ranked_df.head(top_n).to_dict("records")
        for i, paper in enumerate(top_papers, 1):
            table.add_row(
                str(i),
                paper.get("title", "N/A"),
                paper.get("authors", "N/A"),
                f"{paper['score']:.2f}",
                paper.get("arxiv_id", "N/A"),
            )

        console.print(table)


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

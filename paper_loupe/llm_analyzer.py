"""LLM analysis for Paper Loupe.

This module handles:
1. Connecting to OpenAI or Anthropic API
2. Creating prompts to assess paper relevance
3. Processing responses to extract relevance scores
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console

from paper_loupe.config import get_api_key
from paper_loupe.models import SUPPORTED_MODELS, ModelInfo

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
console = Console()

# Try to import LLM provider libraries
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. OpenAI models will not be available.")

try:
    import anthropic  # type: ignore

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning(
        "Anthropic package not installed. Claude models will not be available."
    )


class LLMError(Exception):
    """Exception raised for errors related to LLM API calls."""

    pass


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze(
        self, prompt: str, model_id: str, max_tokens: int
    ) -> Tuple[str, Dict[str, Any]]:
        """Analyze text using the LLM.

        Args:
            prompt: The prompt to send to the LLM
            model_id: The model identifier to use
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (response text, metadata)

        Raises:
            LLMError: If the API call fails
        """
        raise NotImplementedError("Subclasses must implement analyze method")


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI models."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = openai.OpenAI(api_key=api_key)

    def analyze(
        self, prompt: str, model_id: str, max_tokens: int
    ) -> Tuple[str, Dict[str, Any]]:
        """Analyze text using OpenAI API.

        Args:
            prompt: The prompt to send to the LLM
            model_id: The model identifier to use
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (response text, metadata)

        Raises:
            LLMError: If the API call fails
        """
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful research assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )

            # Extract the content from the response
            content = response.choices[0].message.content or ""

            # Prepare metadata
            metadata = {
                "model": model_id,
                "provider": "openai",
                "prompt_tokens": response.usage.prompt_tokens,  # type: ignore
                "completion_tokens": response.usage.completion_tokens,  # type: ignore
                "total_tokens": response.usage.total_tokens,  # type: ignore
            }

            return content, metadata

        except Exception as e:
            raise LLMError(f"OpenAI API error: {str(e)}")


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude models."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze(
        self, prompt: str, model_id: str, max_tokens: int
    ) -> Tuple[str, Dict[str, Any]]:
        """Analyze text using Anthropic API.

        Args:
            prompt: The prompt to send to the LLM
            model_id: The model identifier to use
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (response text, metadata)

        Raises:
            LLMError: If the API call fails
        """
        try:
            response = self.client.messages.create(
                model=model_id,
                system="You are a helpful research assistant.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )

            # Extract the content from the response
            content = response.content[0].text

            # Prepare metadata (Anthropic API doesn't provide token counts in the same way)
            metadata = {
                "model": model_id,
                "provider": "anthropic",
                # These will be estimated later if needed
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            }

            return content, metadata

        except Exception as e:
            raise LLMError(f"Anthropic API error: {str(e)}")


def get_provider(
    config: Dict[str, Any], model_info: ModelInfo
) -> Optional[LLMProvider]:
    """Get the appropriate LLM provider for a model.

    Args:
        config: The loaded configuration
        model_info: The model information from SUPPORTED_MODELS

    Returns:
        LLMProvider instance or None if not available
    """
    provider_name = model_info["provider"]
    api_key = get_api_key(config, provider_name)

    if not api_key:
        logger.warning(f"No API key available for {provider_name}")
        return None

    if provider_name == "openai":
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI package not available")
            return None
        return OpenAIProvider(api_key)

    elif provider_name == "anthropic":
        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not available")
            return None
        return AnthropicProvider(api_key)

    return None


def analyze_relevance(
    paper_data: Dict[str, Any],
    question: str,
    config: Dict[str, Any],
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """Analyze the relevance of a paper to a research question.

    Args:
        paper_data: Dictionary containing paper metadata
        question: Research question to evaluate relevance against
        config: Configuration dictionary with API keys
        model: The model ID to use for analysis

    Returns:
        Dictionary with analysis results including relevance score and explanation

    Raises:
        ValueError: If paper_data is missing required fields like 'id' or 'title'
    """
    console = Console()

    # Validate paper data has required fields
    if "arxiv_id" not in paper_data:
        raise ValueError("Paper data is missing required 'arxiv_id' field")

    if "title" not in paper_data:
        raise ValueError("Paper data is missing required 'title' field")

    model_info = SUPPORTED_MODELS.get(model)
    if not model_info:
        console.print(f"[bold red]Error:[/bold red] Model '{model}' not supported.")
        return {
            "relevance_score": 0.0,
            "explanation": f"Error: Model '{model}' not supported.",
            "error": True,
            "arxiv_id": paper_data["arxiv_id"],
            "title": paper_data["title"],
        }

    provider = get_provider(config, model_info)
    if not provider:
        console.print(
            f"[bold red]Error:[/bold red] Failed to initialize {model_info['provider']} provider."
        )
        return {
            "relevance_score": 0.0,
            "explanation": f"Error: Failed to initialize {model_info['provider']} provider.",
            "error": True,
            "arxiv_id": paper_data["arxiv_id"],
            "title": paper_data["title"],
        }

    prompt = create_prompt(paper_data, question)
    try:
        # Call the LLM to analyze relevance
        response_text, metadata = provider.analyze(
            prompt, model_info["api_model_id"], max_tokens=1000
        )

        # Parse the response
        result = parse_relevance_response(response_text)

        # Add metadata about the analysis
        result["question"] = question
        result["arxiv_id"] = paper_data["arxiv_id"]
        result["title"] = paper_data["title"]
        result["metadata"] = metadata

        return result
    except LLMError as e:
        console.print(f"[bold red]LLM Error:[/bold red] {str(e)}")
        return {
            "relevance_score": 0.0,
            "explanation": f"Error from LLM: {str(e)}",
            "error": True,
            "question": question,
            "arxiv_id": paper_data["arxiv_id"],
            "title": paper_data["title"],
            "metadata": {"model_used": model},
        }


def create_prompt(paper_data: Dict[str, Any], question: str) -> str:
    """Create a prompt for the LLM to analyze paper relevance to a question.

    Args:
        paper_data: Dictionary containing paper metadata
        question: Research question to evaluate relevance against

    Returns:
        Formatted prompt string for the LLM
    """
    # Extract paper information
    title = paper_data.get("title", "Untitled Paper")
    authors = paper_data.get("authors", "Unknown Authors")
    abstract = paper_data.get("abstract", "No abstract available.")

    # Clean up abstract (ensure it's not too long)
    if len(abstract) > 2000:
        abstract = abstract[:1997] + "..."

    # Format categories if available
    categories = paper_data.get("categories", [])
    categories_str = ", ".join(categories) if categories else "Not specified"

    # Create the prompt with clear instructions and structured format, placing task and response format first
    prompt = f"""You are a research assistant helping to evaluate papers for relevance to specific research questions.

TASK:
Describe whether the topic of the paper or any of its results have any bearing on the research question below. Then produce a final score between 0 and 10, where:
- 0: Completely irrelevant, no connection to the research question
- 5: Somewhat relevant, has some connection but not directly addressing the question
- 10: Highly relevant, directly addresses the core of the research question

REQUIRED RESPONSE FORMAT:
Provide your response in the following XML format:
<explanation>
Your detailed explanation of whether and how the paper relates to the research question. Analyze both the topic and any results mentioned in the abstract.
</explanation>
<score>X</score>
Where X is an integer between 0 and 10.

PAPER DETAILS:
Title: {title}
Authors: {authors}
Categories: {categories_str}
Abstract: {abstract}

RESEARCH QUESTION:
{question}

IMPORTANT: Return ONLY the XML formatted output, with no additional text before or after.
"""
    return prompt


def parse_relevance_response(response: str) -> Dict[str, Any]:
    """Parse the LLM response to extract relevance score and explanation.

    Args:
        response: LLM response text in XML format

    Returns:
        Dictionary with only the explanation and relevance_score
    """
    try:
        # Extract XML from response (in case there's any text before or after)
        xml_content = response.strip()

        # If the response is wrapped with a code block, extract it
        if "```xml" in xml_content and "```" in xml_content:
            start_idx = xml_content.find("```xml") + 7
            end_idx = xml_content.rfind("```")
            xml_content = xml_content[start_idx:end_idx].strip()
        elif "```" in xml_content:
            start_idx = xml_content.find("```") + 3
            end_idx = xml_content.rfind("```")
            xml_content = xml_content[start_idx:end_idx].strip()

        # Extract explanation and score using regex for robustness
        import re

        explanation_match = re.search(
            r"<explanation>(.*?)</explanation>", xml_content, re.DOTALL
        )
        score_match = re.search(r"<score>(.*?)</score>", xml_content, re.DOTALL)

        if not explanation_match or not score_match:
            raise ValueError("Failed to find explanation or score in XML response")

        explanation = explanation_match.group(1).strip()
        try:
            score = float(score_match.group(1).strip())
        except ValueError:
            raise ValueError(
                f"Could not convert score to float: {score_match.group(1)}"
            )

        # Convert the 0-10 scale to a 0-1 scale for consistency with previous format
        relevance_score = score / 10.0

        # Return only the explanation and relevance score
        return {"relevance_score": relevance_score, "explanation": explanation}
    except Exception as e:
        # Fallback for failed parsing
        return {
            "relevance_score": 0.0,
            "explanation": f"Failed to parse LLM response: {str(e)}\nOriginal response: {response[:200]}...",
            "parse_error": str(e),
        }


def batch_analyze(
    papers: List[Dict[str, Any]],
    questions: List[str],
    config: Dict[str, Any],
    model: str = "gpt-4o-mini",
) -> Tuple[Dict[str, Dict[str, Dict[str, Any]]], Dict[str, float]]:
    """Analyze multiple papers against multiple questions.

    Args:
        papers: List of paper data dictionaries
        questions: List of questions
        config: The loaded configuration
        model: The LLM model to use

    Returns:
        Tuple of (results, token_usage)

    Raises:
        ValueError: If any paper is missing a required field
    """
    results: Dict[str, Dict[str, Dict[str, Any]]] = {}
    token_usage = {
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost": 0.0,
    }

    # Get pricing information for the model
    model_info = SUPPORTED_MODELS.get(model)
    if not model_info:
        raise ValueError(f"Model '{model}' not supported")

    # Validate all papers have IDs before starting
    for i, paper in enumerate(papers):
        if "arxiv_id" not in paper:
            raise ValueError(f"Paper at index {i} is missing required 'arxiv_id' field")
        if "title" not in paper:
            raise ValueError(
                f"Paper {paper.get('arxiv_id', f'at index {i}')} is missing required 'title' field"
            )

    for paper in papers:
        paper_id = paper["arxiv_id"]
        results[paper_id] = {}

        for question in questions:
            analysis_result = analyze_relevance(paper, question, config, model)
            results[paper_id][question] = analysis_result

            # Update token usage statistics if available
            metadata = analysis_result.get("metadata", {})
            prompt_tokens = metadata.get("prompt_tokens", 0)
            completion_tokens = metadata.get("completion_tokens", 0)
            total_tokens = metadata.get("total_tokens", 0)

            token_usage["total_prompt_tokens"] += prompt_tokens
            token_usage["total_completion_tokens"] += completion_tokens
            token_usage["total_tokens"] += total_tokens

            # Calculate cost based on model pricing
            input_cost = prompt_tokens * model_info["pricing"]["input"] / 1_000_000
            output_cost = (
                completion_tokens * model_info["pricing"]["output"] / 1_000_000
            )
            token_usage["estimated_cost"] += input_cost + output_cost

    return results, token_usage


if __name__ == "__main__":
    """Run a demo of the paper relevance analysis when module is executed directly."""
    import getpass

    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table

    console.print(
        Panel.fit(
            "[bold blue]Paper Loupe - LLM Analysis Demo[/bold blue]\n"
            "This demo will analyze a sample paper against research questions."
        )
    )

    # Prompt for OpenAI API key
    api_key = getpass.getpass("Enter your OpenAI API key: ")

    # Create a sample config with the API key
    config = {"api_keys": {"openai": api_key}}

    # Model selection
    console.print("\n[bold]Model Selection:[/bold]")
    model_options = {"1": "gpt-4o-mini", "2": "gpt-4o"}

    console.print("Available models:")
    for option, model_name in model_options.items():
        model_info = SUPPORTED_MODELS[model_name]
        console.print(
            f"  {option}. [bold]{model_info['name']}[/bold] - {model_info['description']}"
        )
        console.print(
            f"     Pricing: ${model_info['pricing']['input']:,.2f}/1M input tokens, "
            f"${model_info['pricing']['output']:,.2f}/1M output tokens"
        )

    model_choice = ""
    while model_choice not in model_options:
        model_choice = console.input("\nSelect a model (1-2): ")
        if model_choice not in model_options:
            console.print("[bold red]Invalid selection. Please try again.[/bold red]")

    model = model_options[model_choice]
    console.print(
        f"[bold green]Selected model:[/bold green] {SUPPORTED_MODELS[model]['name']}"
    )

    # Sample paper data
    sample_paper = {
        "id": "demo_paper_1",
        "title": "Deep Learning Approaches to Medical Image Segmentation",
        "authors": "A. Researcher, B. Scientist, C. Engineer",
        "abstract": """
            This paper presents a comprehensive review of deep learning approaches
            to medical image segmentation. We examine various neural network
            architectures including U-Net, V-Net, and nnU-Net, and their
            applications to segmenting anatomical structures in MRI, CT, and
            ultrasound images. We also discuss recent advancements in transfer
            learning and self-supervised techniques for limited labeled data
            scenarios, which are common in medical imaging.
        """,
    }

    # Sample research questions
    questions = [
        "What are the most effective neural network architectures for brain tumor segmentation in MRI images?",
        "How can reinforcement learning be applied to stock market prediction?",
        "What methods exist for handling limited labeled data in medical image segmentation?",
    ]

    console.print("\n[bold]Sample Paper:[/bold]")
    console.print(f"[bold]Title:[/bold] {sample_paper['title']}")
    console.print(f"[bold]Authors:[/bold] {sample_paper['authors']}")
    console.print(f"[bold]Abstract:[/bold] {sample_paper['abstract'].strip()}")

    console.print("\n[bold]Analyzing relevance to research questions...[/bold]")

    # Prepare a cost tracking table
    cost_table = Table(title="Cost Estimation")
    cost_table.add_column("Question", style="cyan")
    cost_table.add_column("Input Tokens", justify="right", style="green")
    cost_table.add_column("Output Tokens", justify="right", style="green")
    cost_table.add_column("Total Tokens", justify="right", style="bold green")
    cost_table.add_column("Estimated Cost (USD)", justify="right", style="yellow")

    # Track total costs
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    # Analyze relevance for each question
    for i, question in enumerate(questions, 1):
        console.print(f"\n[bold]Question {i}:[/bold] {question}")

        with console.status(
            f"[bold green]Analyzing with {SUPPORTED_MODELS[model]['name']}...[/bold green]"
        ):
            result = analyze_relevance(sample_paper, question, config, model)

        if result.get("error"):
            console.print(f"[bold red]Error:[/bold red] {result.get('explanation')}")
            continue

        # Extract token usage from metadata
        metadata = result.get("metadata", {})
        prompt_tokens = metadata.get("prompt_tokens", 0)
        completion_tokens = metadata.get("completion_tokens", 0)
        total_tokens = metadata.get("total_tokens", 0)

        # Calculate cost
        model_info = SUPPORTED_MODELS[model]
        input_cost = prompt_tokens * model_info["pricing"]["input"] / 1_000_000
        output_cost = completion_tokens * model_info["pricing"]["output"] / 1_000_000
        request_cost = input_cost + output_cost

        # Update totals
        total_input_tokens += prompt_tokens
        total_output_tokens += completion_tokens
        total_cost += request_cost

        # Add to cost table
        cost_table.add_row(
            f"Question {i}",
            f"{prompt_tokens:,}",
            f"{completion_tokens:,}",
            f"{total_tokens:,}",
            f"${request_cost:.6f}",
        )

        # Display token usage and cost
        console.print(
            f"[bold]Token Usage:[/bold] {prompt_tokens:,} input, {completion_tokens:,} output"
        )
        console.print(f"[bold]Estimated Cost:[/bold] ${request_cost:.6f} USD")

        # Display score with color based on relevance
        score = result.get("score")
        if score is not None:
            color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
            console.print(
                f"[bold]Relevance Score:[/bold] [{color}]{score}/100[/{color}]"
            )
        else:
            console.print("[bold red]No score returned[/bold red]")

        # Display explanation
        explanation = result.get("explanation", "No explanation provided")
        console.print(Panel(Markdown(explanation), title="Analysis", width=100))

    # Add the totals row
    cost_table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_input_tokens:,}[/bold]",
        f"[bold]{total_output_tokens:,}[/bold]",
        f"[bold]{total_input_tokens + total_output_tokens:,}[/bold]",
        f"[bold]${total_cost:.6f}[/bold]",
    )

    # Display the cost summary table
    console.print("\n[bold]Cost Summary:[/bold]")
    console.print(cost_table)

    console.print("\n[bold green]Demo completed![/bold green]")

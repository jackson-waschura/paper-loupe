"""Paper storage for Paper Loupe.

This module handles:
1. Creating and managing dataframes of paper information
2. Saving and loading dataframes to/from parquet files
3. Deduplicating and ranking papers
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd  # type: ignore[import-untyped]


def create_dataframe(papers: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create a dataframe from a list of paper dictionaries.

    Args:
        papers: List of paper data dictionaries

    Returns:
        pandas DataFrame containing paper information
    """
    if not papers:
        return pd.DataFrame()

    # Create the DataFrame from the list of dictionaries
    df = pd.DataFrame(papers)

    # Convert date strings to datetime objects if present
    if "email_date" in df.columns:
        df["email_date"] = pd.to_datetime(df["email_date"], errors="coerce")

    # Ensure relevance is numeric
    if "relevance" in df.columns:
        df["relevance"] = pd.to_numeric(df["relevance"], errors="coerce")

    return df


def save_dataframe(df: pd.DataFrame, output_path: Union[str, Path]) -> bool:
    """Save a dataframe to a parquet file.

    Args:
        df: pandas DataFrame
        output_path: Path to save the parquet file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert path to Path object if it's a string
        if isinstance(output_path, str):
            output_path = Path(output_path)

        # Ensure parent directories exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save DataFrame to parquet file
        df.to_parquet(output_path)
        return True
    except Exception as e:
        print(f"Error saving dataframe: {e}")
        return False


def load_dataframe(input_path: Union[str, Path]) -> Optional[pd.DataFrame]:
    """Load a dataframe from a parquet file.

    Args:
        input_path: Path to the parquet file

    Returns:
        pandas DataFrame or None if loading failed
    """
    try:
        # Convert path to Path object if it's a string
        if isinstance(input_path, str):
            input_path = Path(input_path)

        # Check if file exists
        if not input_path.exists():
            print(f"File not found: {input_path}")
            return None

        # Load DataFrame from parquet file
        df = pd.read_parquet(input_path)

        return df
    except Exception as e:
        print(f"Error loading dataframe: {e}")
        return None


def deduplicate_papers(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate papers based on arXiv ID.

    Args:
        df: pandas DataFrame

    Returns:
        pandas DataFrame with duplicates removed
    """
    # This would remove duplicates based on arXiv ID
    # For now, it's just a stub
    return df


def rank_papers(df: pd.DataFrame, relevance_scores: Dict[str, float]) -> pd.DataFrame:
    """Rank papers based on relevance scores.

    Args:
        df: pandas DataFrame
        relevance_scores: Dictionary mapping paper IDs to relevance scores

    Returns:
        pandas DataFrame sorted by relevance score
    """
    # This would sort the dataframe based on relevance scores
    # For now, it's just a stub
    return df

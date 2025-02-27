"""arXiv lookup for Paper Loupe.

This module handles:
1. Querying arXiv to find papers based on title and authors
2. Implementing proper rate limiting to respect arXiv's API guidelines
3. Fetching paper abstracts and other metadata
"""

import random
import time
from typing import Any, Callable, List, TypeVar, cast

import arxiv

T = TypeVar("T")


def search_arxiv_by_title(title: str, max_results: int = 5) -> List[Any]:
    """Search arXiv for papers matching the given title.

    Args:
        title: Paper title to search for
        max_results: Maximum number of results to return

    Returns:
        List of arXiv paper objects
    """
    # Create an arXiv client
    client = arxiv.Client()

    # Create the search query
    search = arxiv.Search(
        query=f"ti:{title}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    # Execute the search with throttling to respect arXiv's rate limits
    return list(throttled_request(client.results, search))


def search_with_fallback(
    title: str, authors: List[str], max_results: int = 5
) -> List[Any]:
    """Search arXiv with fallback strategies if exact match fails.

    Implements the following fallback strategy:
    1. First try searching with quoted title to get exact matches
    2. If no results, try without quotes to get partial matches
    3. If still no results, try searching by first author's last name AND a distinctive phrase from the title

    Args:
        title: Paper title
        authors: List of author names
        max_results: Maximum number of results to return

    Returns:
        List of arXiv paper objects
    """
    # Strategy 1: Search with quoted title for exact match
    quoted_title = f'"{title}"'
    results = search_arxiv_by_title(quoted_title, max_results=max_results)
    if results:
        return results

    # Strategy 2: Search without quotes for partial match
    results = search_arxiv_by_title(title, max_results=max_results)
    if results:
        return results

    # Strategy 3: Use first author's last name AND a key phrase from the title
    if authors and len(authors) > 0:
        # Extract last name of first author
        first_author = authors[0]
        last_name = first_author.split(",")[0].strip()

        # Extract a distinctive phrase from the title (first 2-3 words, skipping common words)
        common_words = ["a", "an", "the", "on", "of", "for", "and", "in", "to", "with"]
        title_words = title.split()
        key_phrase = []

        for word in title_words:
            # Remove any punctuation from the word
            clean_word = "".join(c for c in word if c.isalnum() or c.isspace())
            if clean_word.lower() not in common_words:
                key_phrase.append(clean_word)
                if len(key_phrase) >= 2:
                    break

        if key_phrase:
            key_phrase_str = " ".join(key_phrase)
            author_query = f'author:{last_name} AND "{key_phrase_str}"'
            results = search_arxiv_by_title(author_query, max_results=max_results)
            if results:
                return results

    # If all strategies fail, return empty list
    return []


def throttled_request(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Execute a function with rate limiting.

    Ensures requests are spaced by at least 1 second with some jitter
    to respect arXiv's rate limits.

    Args:
        func: Function to execute
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Result of the function call
    """
    # Add jitter to the delay (±0.2 seconds)
    jitter = random.uniform(-0.2, 0.2)
    delay = 1.0 + jitter

    # Ensure minimum delay of 0.8 seconds
    if delay < 0.8:
        delay = 0.8

    # Apply the delay
    time.sleep(delay)

    # Execute the function and return its results
    return cast(T, func(*args, **kwargs))


if __name__ == "__main__":
    """Simple demo that runs when this module is executed directly."""
    import sys

    # Define sample search parameters
    sample_title = "Attention is All You Need"
    sample_authors = ["Vaswani, Ashish", "Shazeer, Noam", "Parmar, Niki"]

    print(f"Searching arXiv for papers related to: '{sample_title}'")
    print(f"Authors: {', '.join(sample_authors)}")
    print("\nPerforming search with fallback strategy...")

    # Perform the search
    results = search_with_fallback(sample_title, sample_authors, max_results=3)

    # Display results
    if results:
        print(f"\nFound {len(results)} papers:")
        for i, paper in enumerate(results, 1):
            print(f"\n--- Paper {i} ---")
            print(f"Title: {paper.title}")
            print(f"Authors: {', '.join(author.name for author in paper.authors)}")
            print(f"Published: {paper.published}")
            print(f"arXiv ID: {paper.entry_id.split('/')[-1]}")
            print(f"PDF URL: {paper.pdf_url}")
            print("\nAbstract:")
            # Limit abstract length for display
            abstract = paper.summary.strip().replace("\n", " ")
            if len(abstract) > 300:
                abstract = abstract[:297] + "..."
            print(abstract)
    else:
        print("\nNo papers found matching the search criteria.")

    print("\nSearch completed.")
    sys.exit(0)

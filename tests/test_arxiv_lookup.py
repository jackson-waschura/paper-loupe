"""Tests for arxiv_lookup.py module."""

import time
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from paper_loupe.arxiv_lookup import (
    search_arxiv_by_title,
    search_with_fallback,
    throttled_request,
)


class TestArxivLookup(unittest.TestCase):
    """Test cases for arxiv_lookup module."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create mock arxiv paper objects
        self.mock_paper1 = {
            "title": "Deep Learning: A Comprehensive Survey",
            "authors": ["Smith, John", "Johnson, Emily"],
            "entry_id": "http://arxiv.org/abs/2201.12345",
            "summary": "This paper provides a comprehensive survey of deep learning approaches.",
            "published": "2022-01-15",
        }

        self.mock_paper2 = {
            "title": "Machine Learning Applications",
            "authors": ["Brown, Robert", "Wilson, David"],
            "entry_id": "http://arxiv.org/abs/2202.54321",
            "summary": "This paper discusses various applications of machine learning.",
            "published": "2022-02-20",
        }

    @patch("arxiv.Client")
    @patch("arxiv.Search")
    def test_search_arxiv_by_title_exact_match(
        self, mock_search: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test searching arXiv by title with an exact match."""
        # Set up mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        mock_search_instance = MagicMock()
        mock_search.return_value = mock_search_instance

        # Mock the client.results method to return our test data
        mock_client_instance.results.return_value = [self.mock_paper1]

        # Call function
        results = search_arxiv_by_title("Deep Learning: A Comprehensive Survey")

        # Assertions
        self.assertEqual(len(results), 1)
        mock_search.assert_called_once()
        mock_client_instance.results.assert_called_once_with(mock_search_instance)

        # Verify search parameters
        search_args = mock_search.call_args[1]
        self.assertIn("Deep Learning: A Comprehensive Survey", search_args["query"])
        self.assertEqual(search_args["max_results"], 5)

    @patch("arxiv.Client")
    @patch("arxiv.Search")
    def test_search_arxiv_by_title_no_results(
        self, mock_search: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test searching arXiv by title with no results."""
        # Set up mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        mock_search_instance = MagicMock()
        mock_search.return_value = mock_search_instance

        # Mock the client.results method to return an empty list
        mock_client_instance.results.return_value = []

        # Call function
        results = search_arxiv_by_title("Nonexistent Paper Title")

        # Assertions
        self.assertEqual(len(results), 0)
        mock_search.assert_called_once()
        mock_client_instance.results.assert_called_once_with(mock_search_instance)

    @patch("paper_loupe.arxiv_lookup.search_arxiv_by_title")
    def test_search_with_fallback_exact_match(self, mock_search: MagicMock) -> None:
        """Test search_with_fallback when exact title match succeeds."""
        # Set up mock
        mock_search.return_value = [self.mock_paper1]

        # Call function
        results = search_with_fallback(
            "Deep Learning: A Comprehensive Survey", ["Smith, John", "Johnson, Emily"]
        )

        # Assertions
        self.assertEqual(len(results), 1)
        mock_search.assert_called_once_with(
            '"Deep Learning: A Comprehensive Survey"', max_results=5
        )

    @patch("paper_loupe.arxiv_lookup.search_arxiv_by_title")
    def test_search_with_fallback_partial_match(self, mock_search: MagicMock) -> None:
        """Test search_with_fallback when exact match fails but partial match succeeds."""

        # Mock responses for different calls
        def side_effect(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
            if query.startswith('"'):  # Exact match attempt
                return []
            else:  # Partial match attempt
                return [self.mock_paper1]

        mock_search.side_effect = side_effect

        # Call function
        results = search_with_fallback(
            "Deep Learning: A Comprehensive Survey", ["Smith, John", "Johnson, Emily"]
        )

        # Assertions
        self.assertEqual(len(results), 1)
        self.assertEqual(mock_search.call_count, 2)
        # First call with quoted title
        mock_search.assert_any_call(
            '"Deep Learning: A Comprehensive Survey"', max_results=5
        )
        # Second call without quotes
        mock_search.assert_any_call(
            "Deep Learning: A Comprehensive Survey", max_results=5
        )

    @patch("paper_loupe.arxiv_lookup.search_arxiv_by_title")
    def test_search_with_fallback_author_match(self, mock_search: MagicMock) -> None:
        """Test search_with_fallback when title matches fail but author+key phrase succeeds."""

        # Mock responses for different calls
        def side_effect(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
            if "Smith" in query and "Deep Learning" in query:
                return [self.mock_paper1]
            else:
                return []

        mock_search.side_effect = side_effect

        # Call function
        results = search_with_fallback(
            "Deep Learning: A Comprehensive Survey", ["Smith, John", "Johnson, Emily"]
        )

        # Assertions
        self.assertEqual(len(results), 1)
        self.assertEqual(mock_search.call_count, 3)
        # Third call with author name and key phrase
        mock_search.assert_any_call('author:Smith AND "Deep Learning"', max_results=5)

    @patch("paper_loupe.arxiv_lookup.search_arxiv_by_title")
    def test_search_with_fallback_no_match(self, mock_search: MagicMock) -> None:
        """Test search_with_fallback when all strategies fail."""
        # No results for any search
        mock_search.return_value = []

        # Call function
        results = search_with_fallback(
            "Completely Nonexistent Paper", ["Unknown, Author"]
        )

        # Assertions
        self.assertEqual(len(results), 0)
        self.assertEqual(mock_search.call_count, 3)

    def test_throttled_request(self) -> None:
        """Test that throttled_request properly rate limits API calls."""

        # Create a simple test function
        def test_func(x: int) -> int:
            return x * 2

        # Measure execution time for multiple calls
        start_time = time.time()
        results = [
            throttled_request(test_func, 1),
            throttled_request(test_func, 2),
            throttled_request(test_func, 3),
        ]
        end_time = time.time()

        # Assertions
        self.assertEqual(results, [2, 4, 6])  # Function results are correct
        execution_time = end_time - start_time
        # With 3 calls at ~1 second each, should take at least ~2 seconds
        self.assertGreaterEqual(execution_time, 2.0)


if __name__ == "__main__":
    unittest.main()

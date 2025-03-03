"""Tests for paper_store.py"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from paper_loupe.paper_store import create_dataframe, load_dataframe, save_dataframe


class TestPaperStore(unittest.TestCase):
    """Test case for paper storage functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Sample papers data based on what we've seen in the email processor tests
        self.sample_papers = [
            {
                "title": "Scholar Alert Digest AA/BB",
                "email_id": "msg1",
                "email_date": "Fri, 01 Jan 2021 00:00:00 +0000",
                "authors": "Author One, Author Two",
                "relevance": 80,
                "venue": "Journal of Example",
                "url": "https://example.com/paper",
            },
            {
                "title": "Another Research Paper",
                "email_id": "msg2",
                "email_date": "Sat, 02 Jan 2021 12:00:00 +0000",
                "authors": "Author Three, Author Four",
                "relevance": 65,
                "venue": "Conference Proceedings",
                "url": "https://example.com/paper2",
            },
        ]

    def test_create_dataframe(self) -> None:
        """Test creating a dataframe from paper dictionaries."""
        # Create dataframe
        df = create_dataframe(self.sample_papers)

        # Assertions
        self.assertEqual(len(df), 2)
        # Check that email_date was converted to timestamp
        self.assertTrue(isinstance(df["email_date"].iloc[0], pd.Timestamp))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["relevance"]))
        self.assertEqual(df.loc[0, "authors"], "Author One, Author Two")
        self.assertEqual(df.loc[1, "venue"], "Conference Proceedings")
        self.assertEqual(df.loc[0, "title"], "Scholar Alert Digest AA/BB")
        self.assertEqual(df.loc[1, "title"], "Another Research Paper")

    def test_create_dataframe_empty(self) -> None:
        """Test creating a dataframe with empty list."""
        df = create_dataframe([])
        self.assertTrue(df.empty)

    def test_save_and_load_dataframe(self) -> None:
        """Test saving and loading a dataframe."""
        # Create temporary file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test_papers.parquet"

            # Create and save dataframe
            df = create_dataframe(self.sample_papers)
            result = save_dataframe(df, temp_file)

            # Assertions for save
            self.assertTrue(result)
            self.assertTrue(temp_file.exists())

            # Load dataframe
            loaded_df = load_dataframe(temp_file)

            # Assertions for load
            self.assertIsNotNone(loaded_df)
            if loaded_df is not None:  # To satisfy type checker
                self.assertEqual(len(loaded_df), 2)
                self.assertEqual(
                    loaded_df.loc[0, "title"], "Scholar Alert Digest AA/BB"
                )
                self.assertEqual(loaded_df.loc[1, "title"], "Another Research Paper")

    def test_load_nonexistent_file(self) -> None:
        """Test loading a file that doesn't exist."""
        non_existent_file = Path("non_existent_file.parquet")
        result = load_dataframe(non_existent_file)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

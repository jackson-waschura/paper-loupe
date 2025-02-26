"""Tests for the Paper Loupe CLI."""

import subprocess
import sys

from paper_loupe import __version__


def test_version() -> None:
    """Test that the CLI reports the correct version."""
    result = subprocess.run(
        [sys.executable, "-m", "paper_loupe.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert f"version {__version__}" in result.stdout


def test_help() -> None:
    """Test that the CLI help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "paper_loupe.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (
        "Paper Loupe - Manage and prioritize your research paper backlog"
        in result.stdout
    )

    # Check that all subcommands are listed
    assert "setup" in result.stdout
    assert "process" in result.stdout
    assert "show" in result.stdout
    assert "models" in result.stdout

# Paper Loupe

A CLI-based application to manage and prioritize your research paper backlog.

## Overview

Paper Loupe helps you stay on top of your research paper reading list by:

1. Accessing your Gmail to find Scholar Alert Digest emails
2. Extracting paper information from these digests
3. Finding corresponding arXiv entries
4. Scoring papers based on relevance to your research questions
5. Presenting a ranked list of papers to help you prioritize your reading

## Installation

This is a first-pass implementation to demonstrate the CLI interface without full functionality.

### Prerequisites

- Gmail account with Scholar Alert Digests
- uv package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/paper-loupe.git
cd paper-loupe
```

2. Install the tool using uv:
```bash
uv sync
```

## Configuration

1. Create a configuration directory:
```bash
mkdir -p ~/.config/paper-loupe
```

2. Copy the example configuration file:
```bash
cp config_example.yaml ~/.config/paper-loupe/config.yaml
```

3. Edit the configuration file to include your research questions:
```bash
vim ~/.config/paper-loupe/config.yaml
```

## Usage

Paper Loupe provides the following commands:

### Setup

Initialize Paper Loupe and set up Gmail API authentication:

```bash
uv run paper-loupe setup
```

### Process

Process emails and rank papers based on relevance:

```bash
# Process emails from the last 30 days
uv run paper-loupe process

# Process emails since a specific date
uv run paper-loupe process --since 2023-01-01

# Use a specific LLM model
uv run paper-loupe process --model gpt-4o

# Save output to a file
uv run paper-loupe process --output ~/paper_rankings.csv
```

### Show

Show details of papers in the database:

```bash
# List all papers
uv run paper-loupe show

# Show details for a specific paper
uv run paper-loupe show PAPER_ID
```

## Development

### Testing

Run tests with pytest:

```bash
# First install all dependencies
uv sync

# Then run pytest
uv run -m pytest -xvs
```

### Automated Code Quality with Pre-commit

This project is set up with pre-commit to automatically run code quality tools before each commit:

1. Set up the git hooks:
```bash
uv run pre-commit install
```

3. Now, each time you commit code, the following checks will run automatically:
   - Black (code formatting)
   - isort (import sorting)
   - Ruff (linting)
   - Type checking with mypy
   - Other checks like trailing whitespace and YAML validation

If any check fails, the commit will be aborted, giving you a chance to fix the issues first.

You can also run the checks manually:
```bash
uv run pre-commit run --all-files
```

## Future Improvements

This is a first-pass implementation that demonstrates the CLI interface. Future improvements will include:

1. Full implementation of Gmail API authentication and email processing
2. Complete arXiv integration with proper throttling
3. LLM-based relevance scoring
4. Complete data storage with parquet files
5. Additional testing and error handling

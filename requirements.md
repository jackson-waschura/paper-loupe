# Paper Loupe Requirements

## Overview

This CLI-based application is designed to help manage and prioritize your research paper backlog. The app will:

- Use the Gmail API (with read-only permissions) to access your email.
- Identify and process emails containing your "Scholar Alert Digest".
- Parse these emails to extract details for the 5 recommended papers per digest.
- Locate the corresponding arXiv entry for each paper using the most common, dependable method available, with built-in throttling to respect free API limits.
- Store the parsed paper data in a local dataframe saved as a parquet file.
- Accept user-defined questions from a configuration YAML file.
- Use OpenAI's LLM APIs to assess the relevance of each paper to the provided question.
- Rank the papers solely based on their relevance to your question.
- Log progress and errors clearly to the terminal while keeping output concise.

## Functional Requirements

### 1. Email Processing
- **Access**:
  - Utilize the Gmail API with read-only permissions to retrieve emails.
  - Configuration: Gmail API credentials and related email settings must be provided in a separate configuration or environment file (not committed to version control).
  - **Authentication Flow**:
    - Implement OAuth 2.0 authentication using Application Default Credentials (ADC).
    - The application must request only the minimal scope needed: `https://www.googleapis.com/auth/gmail.readonly`.
    - First-time setup should guide the user through the OAuth consent flow:
      1. When first run, the application should open a browser window directing the user to Google's OAuth consent screen.
      2. After the user grants permission, Google will provide an authorization code.
      3. The application should exchange this code for refresh and access tokens.
      4. These tokens should be securely stored in the user's home directory (e.g., `~/.config/paper-loupe/credentials.json`).
    - Subsequent runs should use the stored refresh token to obtain new access tokens without requiring user interaction.
    - Include clear error messages and recovery steps if authentication fails.
  - **API Error Handling**:
    - Implement exponential backoff for retrying failed API requests (starting with a 1-second delay, doubling up to a maximum of 32 seconds).
    - For rate limit errors (HTTP 429), pause processing and retry after the time specified in the `Retry-After` header.
    - If authentication errors occur (HTTP 401/403), prompt the user to re-authenticate by deleting the stored credentials and restarting the OAuth flow.
    - For persistent failures after 5 retries, log the error details and gracefully exit with a non-zero status code and clear error message.
    - Implement partial success handling: if some emails are processed successfully before a failure occurs, save the partial results to avoid reprocessing.
- **Time Period Control**:
  - The CLI must accept a `--since` parameter in ISO date format (YYYY-MM-DD) to specify how far back in time to search for emails.
  - The application is designed for batch processing of historical emails received since the specified date.
  - If no `--since` parameter is provided, the application should default to processing emails from the last 30 days.
  - Example: `--since 2023-01-01` would process all Scholar Alert Digest emails received since January 1, 2023.
- **Digest Filtering**:
  - Identify emails whose subject line contains the string "Scholar Alert Digest".
  - Log the number of emails processed and the number of emails kept.
- **Email Parsing**:
  - Process each digest email that contains 5 paper recommendations.
  - Extract the following details for each paper:
    - Title
    - Authors
    - Date Published
  - Remove duplicate entries based on exact title matches.
- **ArXiv Lookup**:
  - Query arXiv using a dependable method (e.g., the public arXiv API or a well-established Python library) to locate the corresponding arXiv entry based on the paper details.
  - **API/Library Selection**:
    - Use the official `arxiv` Python package (https://pypi.org/project/arxiv/) to query the arXiv API.
    - The package provides a clean interface to search for papers by title, author, or other metadata.
    - Example usage:
      ```python
      import arxiv
      search = arxiv.Search(
        query = "ti:\"Exact Title Here\"",
        max_results = 5,
        sort_by = arxiv.SortCriterion.Relevance
      )
      results = list(search.results())
      ```
  - **Fallback Strategy**:
    - If an exact title match fails, implement a fuzzy matching approach:
      1. First try searching with quoted title to get exact matches
      2. If no results, try without quotes to get partial matches
      3. If still no results, try searching by first author's last name AND a distinctive phrase from the title
      4. If all searches fail, log a warning and skip the paper.
  - **Throttling Implementation**:
    - Limit API requests to no more than 1 request per second to respect arXiv's rate limits.
    - Implement a request queue with a time-based throttle to ensure consistent spacing between requests.
    - Add jitter (±0.2 seconds) to request timing to avoid creating patterns that might trigger rate limiting.
  - **Duplicate Identification**:
    - Consider papers as duplicates if they have identical arXiv IDs.

### 2. Data Storage
- **Dataframe Creation**:
  - Structure the parsed data into a dataframe with columns for title, authors, publication date, arXiv entry/link, and the digest's recommendation date.
  - Save the dataframe as a parquet file.

### 3. Question Processing and Analysis
- **Configuration Input**:
  - Accept questions via a configuration file in YAML format.
  - Separation of Concerns: API keys and email settings should be stored separately (in a config or env file) and not be part of the version-controlled configuration file that contains questions.
- **CLI Operation**:
  - Run the tool as a CLI, reading the configuration file to obtain the questions.
  - Display real-time progress updates and concise error messages in the terminal.
- **LLM API Integration**:
  - For each paper, call the OpenAI or AnthropicAPI to evaluate its relevance solely with respect to the provided question.
  - Allow the user to specify which LLM model to call.
  - Construct clear prompts that include the paper's details (e.g., title, abstract) for relevance assessment.
  - Collect and store relevance scores for each paper.

### 4. Paper Ranking
- **Ranking Mechanism**:
  - Rank papers based on the relevance scores obtained from the LLM API.
- **Output**:
  - Present the ranked list of papers in a clear format via the CLI.
  - Save the ranked list of papers to a file.
  - Display the top 5 papers in the terminal.

### 5. Logging and Error Handling
- **Progress Logging**:
  - Provide visual status updates (e.g., "Fetching emails…", "Parsing digest…", "Locating arXiv entries…", "Processing relevance scores…", "Ranking complete") in the terminal.
- **Error Logging**:
  - Log errors clearly and concisely, ensuring critical issues are highlighted without overwhelming the terminal.
  - Specify error handling strategy (retry, abort, skip) for different error types.
- **Verbosity Control**:
  - The CLI should minimize output clutter while still conveying sufficient progress and error information.

## Non-Functional Requirements

### Configurability
- Sensitive details (e.g., API keys, email settings) must be provided via separate config or environment files that are excluded from version control.
- The main configuration YAML file will contain the user-defined questions.

### Modularity
- The application should be organized into clearly separated components:
  - Gmail API handling
  - Email filtering and parsing
  - arXiv lookup (with built-in throttling)
  - Data storage (dataframe creation and parquet file management)
  - Relevance analysis via LLM API
  - CLI and logging management

### Documentation
- Provide comprehensive inline documentation.
- Include a README with setup instructions, configuration details (including how to set up separate config/env files), and usage examples.

### Testing
- Develop unit tests for key functionalities (e.g., email parsing, duplicate removal, arXiv lookup, API integration).
- Use pytest for testing.

### Performance
- While designed for ~200 papers, ensure the system handles the workload efficiently.

## Implementation Details

### Programming Language
- Python

### Key Libraries/Tools
- **Email Access**: Gmail API client library.
- **Email Parsing**: Libraries such as regex and BeautifulSoup.
- **Data Manipulation and Storage**: pandas and pyarrow (for saving parquet files).
- **API Calls**: openai Python client.
- **Logging**: Python's built-in logging module with configurable verbosity.
- **Testing**: pytest.
- **Package Management**: uv.

## Development Process

- Use uv to manage dependencies including python version.
- Use test-driven development to ensure each incremental change is tested and existing tests pass.

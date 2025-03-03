"""Email processing for Paper Loupe.

This module handles:
1. Authentication with Gmail API
2. Fetching Scholar Alert Digest emails
3. Parsing emails to extract paper information

Run a simple API test with:
```bash
uv run -m paper_loupe.email_processor
```
"""

import base64
import json
import os.path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# These imports lack type stubs, so we need to ignore mypy warnings
from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

# If modifying these scopes, delete the token.json file.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = os.path.join("secrets", "gmail", "token.json")
CREDENTIALS_PATH = os.path.join("secrets", "gmail", "credentials.json")


def authenticate_gmail(
    credentials_path: Optional[str] = None, token_path: Optional[str] = None
) -> Optional[Any]:
    """Authenticate with Gmail API using OAuth 2.0.

    Args:
        credentials_path: Path to the credentials.json file. If None, uses default.
        token_path: Path to save/load the token.json file. If None, uses default.

    Returns:
        Authenticated Gmail API service or None if authentication fails
    """
    credentials_path = credentials_path or CREDENTIALS_PATH
    token_path = token_path or TOKEN_PATH

    creds = None
    # The token.json file stores the user's access and refresh tokens and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_info(
            json.loads(open(token_path).read()), SCOPES
        )

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    try:
        # Build the Gmail API service
        service = build("gmail", "v1", credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def fetch_scholar_alerts(service: Any, since_date: datetime) -> List[Any]:
    """Fetch Scholar Alert Digest emails since the given date.

    Args:
        service: Authenticated Gmail API service
        since_date: datetime object representing the cutoff date

    Returns:
        List of email objects containing Scholar Alert Digests
    """
    try:
        # Convert date to Gmail API search format (YYYY/MM/DD)
        date_str = since_date.strftime("%Y/%m/%d")

        # Query for Scholar Alert emails after the specified date
        query = f'subject:"Scholar Alert" after:{date_str}'

        # Get message IDs matching the query
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No Scholar Alert emails found.")
            return []

        # Fetch full message details for each message ID
        emails = []
        for message in messages:
            msg = (
                service.users().messages().get(userId="me", id=message["id"]).execute()
            )
            emails.append(msg)

        return emails

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def parse_email(email: Any) -> list[Dict[str, Any]]:
    """Parse a Scholar Alert Digest email to extract paper information.

    Args:
        email: Email object from Gmail API

    Returns:
        List of dictionaries containing paper information
    """
    papers: List[Dict[str, Any]] = []

    if not email:
        return papers

    # Get headers
    headers = {}
    if "payload" in email and "headers" in email["payload"]:
        for header in email["payload"]["headers"]:
            headers[header["name"]] = header["value"]

    subject = headers.get("Subject", "No Subject")
    sender = headers.get("From", "No From")
    date_str = headers.get("Date", "")

    # Extract email body content
    body_html = ""
    if "payload" in email:
        # For simple messages
        if "body" in email["payload"] and "data" in email["payload"]["body"]:
            body_data = email["payload"]["body"]["data"]
            body_html = base64.urlsafe_b64decode(body_data).decode("utf-8")
        # For multipart messages
        elif "parts" in email["payload"]:
            for part in email["payload"]["parts"]:
                if part["mimeType"] == "text/html":
                    if "data" in part["body"]:
                        body_data = part["body"]["data"]
                        body_html = base64.urlsafe_b64decode(body_data).decode("utf-8")

    # Parse HTML to extract paper information
    if body_html and "scholar-inbox.com" in body_html:
        # Use BeautifulSoup to parse the HTML content
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(body_html, "html.parser")

        # Find all paper articles
        articles = soup.find_all("article")

        for article in articles:
            paper = {
                "email_id": email.get("id", ""),
                "email_date": date_str,
                "email_subject": subject,
                "email_sender": sender,
            }

            # Extract paper title
            title_element = article.find("h2")
            if title_element and title_element.find("a"):
                paper["title"] = title_element.find("a").text.strip()

            # Extract authors
            authors_element = article.find("p")
            if authors_element:
                paper["authors"] = authors_element.text.strip()

            # Extract relevance score
            relevance_span = article.find(
                "span", string=lambda text: "Relevance:" in text if text else False
            )
            if relevance_span:
                relevance_text = relevance_span.text.strip()
                try:
                    paper["relevance"] = int(
                        relevance_text.replace("Relevance:", "").strip()
                    )
                except ValueError:
                    paper["relevance"] = 0

            # Extract publication venue/date
            venue_div = article.find(
                "div",
                {
                    "style": lambda style: (
                        "display:inline;float:right;" in style if style else False
                    )
                },
            )
            if venue_div:
                paper["venue"] = venue_div.text.strip()

            # Add paper URL
            url_element = title_element.find("a") if title_element else None
            if url_element and "href" in url_element.attrs:
                paper["url"] = url_element["href"]

            papers.append(paper)

    return papers


def fetch_and_parse_scholar_alerts(
    service: Any, since_date: datetime
) -> List[Dict[str, Any]]:
    """Fetch and parse Scholar Alert Digest emails since the given date.

    Args:
        service: Authenticated Gmail API service
        since_date: datetime object representing the cutoff date

    Returns:
        List of dictionaries containing papers extracted from Scholar Alert emails
    """
    all_papers = []

    # Fetch raw emails
    emails = fetch_scholar_alerts(service, since_date)

    # Process each email to extract papers
    for email in emails:
        papers = parse_email(email)
        all_papers.extend(papers)

    return all_papers


def clean_paper_data(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean and normalize paper data extracted from emails.

    Args:
        papers: List of paper dictionaries extracted from emails

    Returns:
        List of cleaned paper dictionaries with consistent formatting
    """
    cleaned_papers = []

    for paper in papers:
        cleaned_paper = {
            "title": paper.get("title", "")
            .strip()
            .replace("\n", " ")
            .replace("  ", " "),
            "authors": paper.get("authors", "")
            .strip()
            .replace("\n", ", ")
            .replace("  ", " "),
            "relevance": paper.get("relevance", 0),
            "venue": paper.get("venue", "").strip(),
            "url": paper.get("url", ""),
            "email_id": paper.get("email_id", ""),
            "email_date": paper.get("email_date", ""),
        }

        # Try to parse the date string into a datetime object
        if cleaned_paper["email_date"]:
            try:
                from email.utils import parsedate_to_datetime

                date_obj = parsedate_to_datetime(cleaned_paper["email_date"])
                cleaned_paper["date"] = date_obj
            except Exception:
                # If parsing fails, keep the original string
                cleaned_paper["date"] = None

        # Extract ArXiv ID if present in the URL
        if "arxiv.org" in cleaned_paper.get("url", ""):
            import re

            arxiv_match = re.search(r"arxiv.org/abs/(\d+\.\d+)", cleaned_paper["url"])
            if arxiv_match:
                cleaned_paper["arxiv_id"] = arxiv_match.group(1)

        cleaned_papers.append(cleaned_paper)

    return cleaned_papers


def get_recent_papers(days: int = 30) -> List[Dict[str, Any]]:
    """Get papers from Scholar Alerts from the last specified number of days.

    This function provides a simple interface for other modules to access
    paper data from recent Scholar Alert emails.

    Args:
        days: Number of days to look back for Scholar Alert emails

    Returns:
        List of cleaned paper dictionaries
    """
    # Authenticate with Gmail API
    service = authenticate_gmail()

    if not service:
        print("Authentication failed.")
        return []

    # Fetch papers from the last specified number of days
    since_date = datetime.now() - timedelta(days=days)
    papers = fetch_and_parse_scholar_alerts(service, since_date)

    # Clean and return the paper data
    return clean_paper_data(papers)


# Example usage
if __name__ == "__main__":
    # Authenticate with Gmail API
    service = authenticate_gmail()

    if service:
        print("Authentication successful!")

        # Fetch Scholar Alert emails from the last 7 days
        cleaned_papers = get_recent_papers(7)

        # Print paper information
        print(f"Found {len(cleaned_papers)} papers in Scholar Alerts")
        for i, paper in enumerate(cleaned_papers):
            print(f"\nPaper {i + 1}:")
            print(f"Title: {paper.get('title', 'No Title')}")
            print(f"Authors: {paper.get('authors', 'No Authors')}")
            print(f"Relevance: {paper.get('relevance', 'N/A')}")
            print(f"Venue: {paper.get('venue', 'N/A')}")
            print(f"URL: {paper.get('url', 'No URL')}")
            if paper.get("date"):
                date = paper.get("date")
                print(f"Date: {date.strftime('%Y-%m-%d') if date else 'No Date'}")
            print("-" * 50)
    else:
        print("Authentication failed.")

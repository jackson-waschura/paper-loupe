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
    # Basic implementation to extract email subject and snippet
    # In a real implementation, you would parse the email body to extract paper details
    papers: List[Dict[str, Any]] = []

    if not email:
        return papers

    # Get headers
    headers = email.get("payload", {}).get("headers", [])
    subject = next(
        (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
    )

    # Get snippet (preview of email content)
    snippet = email.get("snippet", "")

    # For now, just return a single entry with basic info
    # A more complete implementation would parse HTML content to extract paper details
    papers.append(
        {
            "title": subject,
            "snippet": snippet,
            "email_id": email.get("id", ""),
            "timestamp": email.get("internalDate", ""),
        }
    )

    return papers


def list_labels(service: Any) -> List[str]:
    """List all available labels in the user's Gmail account.

    This is primarily for demonstration/testing of the API connection.

    Args:
        service: Authenticated Gmail API service

    Returns:
        List of label names
    """
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        if not labels:
            print("No labels found.")
            return []

        label_names = [label["name"] for label in labels]
        return label_names

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


# Example usage
if __name__ == "__main__":
    # List Gmail labels to verify the connection
    def test_list_labels(service: Any) -> None:
        labels = list_labels(service)
        print("Labels:")
        for label in labels:
            print(f"- {label}")

    # Authenticate with Gmail API
    service = authenticate_gmail()

    if service:
        print("Authentication successful!")

        # Test listing labels
        test_list_labels(service)

        # Fetch Scholar Alert emails from the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        emails = fetch_scholar_alerts(service, thirty_days_ago)

        # Parse emails
        for email in emails:
            papers = parse_email(email)
            for paper in papers:
                print(f"Paper: {paper['title']}")
    else:
        print("Authentication failed.")

"""Tests for email_processor.py without requiring OAuth flow."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from paper_loupe.email_processor import (
    authenticate_gmail,
    fetch_scholar_alerts,
    parse_email,
)


class TestEmailProcessor(unittest.TestCase):
    """Test cases for email_processor module."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a mock service
        self.mock_service = MagicMock()

        self.mock_messages_list_response = {
            "messages": [
                {"id": "msg1"},
                {"id": "msg2"},
            ]
        }

        self.mock_message_response = {
            "id": "msg1",
            "threadId": "thread1",
            "labelIds": ["INBOX"],
            "snippet": "This is a paper about machine learning",
            "internalDate": "1609459200000",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Scholar Alert Digest AA/BB"},
                    {
                        "name": "From",
                        "value": "Google Scholar <scholaralerts-noreply@google.com>",
                    },
                ]
            },
        }

    @patch("paper_loupe.email_processor.Credentials")
    @patch("paper_loupe.email_processor.InstalledAppFlow")
    @patch("paper_loupe.email_processor.build")
    def test_authenticate_gmail_with_existing_token(
        self, mock_build: MagicMock, mock_flow: MagicMock, mock_credentials: MagicMock
    ) -> None:
        """Test authentication when token exists."""
        # Create a temporary token file
        with tempfile.NamedTemporaryFile(delete=False) as temp_token:
            temp_token.write(json.dumps({"token": "fake_token"}).encode())
            temp_token_path = temp_token.name

        # Mock the credentials and service
        mock_creds = MagicMock()
        mock_credentials.from_authorized_user_info.return_value = mock_creds
        mock_creds.valid = True
        mock_build.return_value = self.mock_service

        # Call the function with our temporary token
        service = authenticate_gmail(
            credentials_path="fake_path", token_path=temp_token_path
        )

        # Assertions
        self.assertEqual(service, self.mock_service)
        mock_credentials.from_authorized_user_info.assert_called_once()
        mock_flow.assert_not_called()  # Should not need to run the flow
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

        # Clean up
        os.unlink(temp_token_path)

    def test_fetch_scholar_alerts(self) -> None:
        """Test fetching Scholar Alert emails."""
        # Set up the mock service
        messages_list_mock = self.mock_service.users().messages().list
        messages_list_mock.return_value.execute.return_value = (
            self.mock_messages_list_response
        )

        message_get_mock = self.mock_service.users().messages().get
        message_get_mock.return_value.execute.return_value = self.mock_message_response

        # Call the function
        since_date = datetime.now() - timedelta(days=7)
        emails = fetch_scholar_alerts(self.mock_service, since_date)

        # Assertions
        self.assertEqual(len(emails), 2)
        date_str = since_date.strftime("%Y/%m/%d")
        messages_list_mock.assert_called_once_with(
            userId="me", q=f'subject:"Scholar Alert" after:{date_str}'
        )
        self.assertEqual(message_get_mock.call_count, 2)

    def test_parse_email(self) -> None:
        """Test parsing email to extract paper information."""
        # Call the function
        papers = parse_email(self.mock_message_response)

        # Assertions
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["title"], "Scholar Alert Digest AA/BB")
        self.assertEqual(papers[0]["snippet"], "This is a paper about machine learning")
        self.assertEqual(papers[0]["email_id"], "msg1")
        self.assertEqual(papers[0]["timestamp"], "1609459200000")


if __name__ == "__main__":
    unittest.main()

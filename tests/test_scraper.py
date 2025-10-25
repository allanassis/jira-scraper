"""Tests for Jira scraper."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from jira_scraper.scraper import JiraScraper


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    return tmp_path / "output"


@pytest.fixture
def scraper(temp_output_dir):
    """Create JiraScraper instance."""
    return JiraScraper(
        projects=["TEST"],
        output_dir=temp_output_dir,
        max_concurrent=1,
        rate_limit_delay=0.1,
    )


@pytest.mark.asyncio
async def test_scraper_initialization(scraper, temp_output_dir):
    """Test scraper initialization."""
    assert scraper.projects == ["TEST"]
    assert scraper.output_dir == temp_output_dir
    assert temp_output_dir.exists()


@pytest.mark.asyncio
async def test_state_management(scraper):
    """Test state save/load functionality."""
    scraper.processed_issues.add("TEST-123")
    scraper.save_state()

    # Create new scraper instance
    new_scraper = JiraScraper(
        projects=["TEST"],
        output_dir=scraper.output_dir,
    )

    assert "TEST-123" in new_scraper.processed_issues


def test_issue_from_api_response():
    """Test issue creation from API response."""
    api_response = {
        "key": "TEST-123",
        "id": "123",
        "fields": {
            "project": {"key": "TEST"},
            "summary": "Test issue",
            "description": "Test description",
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "John Doe"},
            "reporter": {"displayName": "Jane Doe"},
            "created": "2023-01-01T00:00:00.000Z",
            "updated": "2023-01-02T00:00:00.000Z",
            "labels": ["bug", "urgent"],
            "components": [{"name": "core"}],
            "comment": {
                "comments": [
                    {
                        "id": "1",
                        "author": {"displayName": "Commenter"},
                        "body": "Test comment",
                        "created": "2023-01-01T01:00:00.000Z",
                        "updated": "2023-01-01T01:00:00.000Z",
                    }
                ]
            },
        },
    }

    from jira_scraper.models import JiraIssue

    issue = JiraIssue.from_api_response(api_response)

    assert issue.key == "TEST-123"
    assert issue.summary == "Test issue"
    assert issue.status == "Open"
    assert len(issue.comments) == 1
    assert issue.comments[0].body == "Test comment"


@pytest.mark.asyncio
async def test_scraper_cleanup(scraper):
    """Test scraper cleanup."""
    await scraper.close()
    # Verify client is closed (would raise exception if used after close)

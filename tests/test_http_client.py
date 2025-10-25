"""Tests for HTTP client."""

from unittest.mock import AsyncMock, patch

import pytest

from jira_scraper.http_client import JiraHttpClient


@pytest.fixture
def http_client():
    """Create HTTP client instance."""
    return JiraHttpClient(rate_limit_delay=0.1)


@pytest.mark.asyncio
async def test_http_client_initialization(http_client):
    """Test HTTP client initialization."""
    assert http_client.base_url == "https://issues.apache.org/jira"
    assert http_client.rate_limit_delay == 0.1


@pytest.mark.asyncio
async def test_search_issues(http_client):
    """Test search issues method."""
    mock_response = {
        "issues": [
            {"key": "TEST-1"},
            {"key": "TEST-2"},
        ],
        "total": 2,
    }
    
    with patch.object(http_client, "get", return_value=mock_response):
        issues = []
        async for issue in http_client.search_issues("TEST"):
            issues.append(issue)
        
        assert len(issues) == 2
        assert issues[0]["key"] == "TEST-1"


@pytest.mark.asyncio
async def test_get_issue(http_client):
    """Test get single issue."""
    mock_response = {
        "key": "TEST-123",
        "fields": {"summary": "Test issue"},
    }
    
    with patch.object(http_client, "get", return_value=mock_response):
        issue = await http_client.get_issue("TEST-123")
        assert issue["key"] == "TEST-123"


@pytest.mark.asyncio
async def test_client_cleanup(http_client):
    """Test client cleanup."""
    await http_client.close()

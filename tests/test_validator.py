"""Tests for Pydantic validator."""

import pytest
from pydantic import ValidationError

from jira_scraper.validator import (
    JiraIssueValidator,
    JiraSearchValidator,
    validate_issue,
    validate_search_response,
)


def test_valid_issue():
    """Test validation of valid issue."""
    valid_issue = {
        "key": "TEST-123",
        "id": "123",
        "fields": {
            "project": {"key": "TEST"},
            "summary": "Test issue",
            "status": {"name": "Open"},
            "reporter": {"displayName": "John Doe"},
            "created": "2023-01-01T00:00:00.000Z",
            "updated": "2023-01-02T00:00:00.000Z",
            "labels": ["bug"],
            "components": [],
        },
    }
    
    is_valid, errors = validate_issue(valid_issue)
    assert is_valid
    assert len(errors) == 0


def test_invalid_issue_missing_key():
    """Test validation fails for missing key."""
    invalid_issue = {
        "id": "123",
        "fields": {
            "project": {"key": "TEST"},
            "summary": "Test issue",
            "status": {"name": "Open"},
            "reporter": {"displayName": "John Doe"},
            "created": "2023-01-01T00:00:00.000Z",
            "updated": "2023-01-02T00:00:00.000Z",
        },
    }
    
    is_valid, errors = validate_issue(invalid_issue)
    assert not is_valid
    assert len(errors) > 0


def test_search_response_validation():
    """Test search response validation."""
    valid_response = {
        "issues": [
            {
                "key": "TEST-123",
                "id": "123",
                "fields": {
                    "project": {"key": "TEST"},
                    "summary": "Test issue",
                    "status": {"name": "Open"},
                    "reporter": {"displayName": "John Doe"},
                    "created": "2023-01-01T00:00:00.000Z",
                    "updated": "2023-01-02T00:00:00.000Z",
                    "labels": [],
                    "components": [],
                },
            }
        ],
        "total": 1,
    }
    
    is_valid, errors = validate_search_response(valid_response)
    assert is_valid
    assert len(errors) == 0

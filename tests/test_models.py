"""Tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from jira_scraper.models import JiraComment, JiraIssue, LLMTrainingRecord


def test_jira_comment():
    """Test JiraComment model."""
    comment = JiraComment(
        id="123",
        author="test_user",
        body="Test comment",
        created=datetime.now(),
    )
    assert comment.id == "123"
    assert comment.author == "test_user"


def test_jira_issue():
    """Test JiraIssue model."""
    issue = JiraIssue(
        key="TEST-123",
        id="123",
        project="TEST",
        summary="Test issue",
        status="Open",
        reporter="test_user",
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert issue.key == "TEST-123"
    assert issue.project == "TEST"


def test_llm_training_record():
    """Test LLMTrainingRecord creation from JiraIssue."""
    issue = JiraIssue(
        key="TEST-123",
        id="123",
        project="TEST",
        summary="Test issue",
        description="Test description",
        status="Open",
        priority="High",
        reporter="test_user",
        created=datetime.now(),
        updated=datetime.now(),
        comments=[
            JiraComment(
                id="1",
                author="commenter",
                body="Test comment",
                created=datetime.now(),
            )
        ],
    )
    
    record = LLMTrainingRecord.from_jira_issue(issue)
    
    assert record.issue_key == "TEST-123"
    assert record.project == "TEST"
    assert "Test description" in record.text_content
    assert "Test comment" in record.text_content
    assert record.metadata["summary"] == "Test issue"
    assert "summarization" in record.tasks
    assert "classification" in record.tasks
    assert "qa" in record.tasks


def test_jira_issue_validation_missing_key():
    """Test JiraIssue validation fails for missing key."""
    with pytest.raises(ValidationError) as exc_info:
        JiraIssue(
            key=None,
            id="123",
            project="TEST",
            summary="Test issue",
            status="Open",
            reporter="test_user",
            created=datetime.now(),
            updated=datetime.now(),
        )
    assert "1 validation error for JiraIssue\nkey\n  Input should be a valid string" in str(exc_info.value)


def test_jira_issue_validation_missing_project():
    """Test JiraIssue validation fails for missing project."""
    with pytest.raises(ValidationError) as exc_info:
        JiraIssue(
            key="TEST-123",
            id="123",
            project=None,
            summary="Test issue",
            status="Open",
            reporter="test_user",
            created=datetime.now(),
            updated=datetime.now(),
        )
    assert "1 validation error for JiraIssue\nproject\n  Input should be a valid string" in str(exc_info.value)


def test_jira_issue_validation_missing_status():
    """Test JiraIssue validation fails for missing status."""
    with pytest.raises(ValidationError) as exc_info:
        JiraIssue(
            key="TEST-123",
            id="123",
            project="TEST",
            summary="Test issue",
            status=None,
            reporter="test_user",
            created=datetime.now(),
            updated=datetime.now(),
        )
    assert "1 validation error for JiraIssue\nstatus\n  Input should be a valid string" in str(exc_info.value)


def test_jira_issue_validation_missing_reporter():
    """Test JiraIssue validation fails for missing reporter."""
    with pytest.raises(ValidationError) as exc_info:
        JiraIssue(
            key="TEST-123",
            id="123",
            project="TEST",
            summary="Test issue",
            status="Open",
            reporter=None,
            created=datetime.now(),
            updated=datetime.now(),
        )
    assert "1 validation error for JiraIssue\nreporter\n  Input should be a valid string" in str(exc_info.value)


def test_jira_issue_from_api_response_invalid_data():
    """Test JiraIssue.from_api_response with invalid data raises ValidationError."""
    invalid_data = {
        "key": None,  # Missing required field
        "fields": {
            "project": {"key": "TEST"},
            "summary": "Test issue",
            "status": {"name": "Open"},
            "reporter": {"displayName": "John Doe"},
            "created": "2023-01-01T00:00:00.000Z",
            "updated": "2023-01-02T00:00:00.000Z",
        },
    }
    
    with pytest.raises(ValidationError):
        JiraIssue.from_api_response(invalid_data)


def test_jira_issue_from_api_response_empty_data():
    """Test JiraIssue.from_api_response with empty data raises ValidationError."""
    with pytest.raises(ValidationError):
        JiraIssue.from_api_response({})


def test_jira_issue_from_api_response_none_data():
    """Test JiraIssue.from_api_response with None data raises ValidationError."""
    with pytest.raises(ValidationError):
        JiraIssue.from_api_response(None)

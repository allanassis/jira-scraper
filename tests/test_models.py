"""Tests for data models."""

from datetime import datetime

import pytest

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

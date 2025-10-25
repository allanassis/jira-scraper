"""Tests for data transformer."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from jira_scraper.models import JiraComment, JiraIssue
from jira_scraper.transformer import DataTransformer


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    return tmp_path / "output"


@pytest.fixture
def transformer(temp_output_dir):
    """Create DataTransformer instance."""
    return DataTransformer(temp_output_dir)


@pytest.fixture
def sample_issues():
    """Create sample Jira issues."""
    return [
        JiraIssue(
            key="TEST-123",
            id="123",
            project="TEST",
            summary="Test issue 1",
            description="Test description 1",
            status="Open",
            priority="High",
            reporter="user1",
            created=datetime.now(),
            updated=datetime.now(),
            comments=[
                JiraComment(
                    id="1",
                    author="commenter1",
                    body="Comment 1",
                    created=datetime.now(),
                )
            ],
        ),
        JiraIssue(
            key="TEST-124",
            id="124",
            project="TEST",
            summary="Test issue 2",
            description="Test description 2",
            status="Closed",
            priority="Low",
            reporter="user2",
            created=datetime.now(),
            updated=datetime.now(),
        ),
    ]


@pytest.mark.asyncio
async def test_transform_issues(transformer, sample_issues, temp_output_dir):
    """Test issue transformation to JSONL."""
    await transformer.transform_issues(sample_issues)
    
    output_file = temp_output_dir / "training_data.jsonl"
    assert output_file.exists()
    
    # Read and verify JSONL content
    lines = output_file.read_text().strip().split("\n")
    assert len(lines) == 2
    
    # Parse first record
    record = json.loads(lines[0])
    assert record["issue_key"] == "TEST-123"
    assert record["project"] == "TEST"
    assert "Test description 1" in record["text_content"]
    assert "Comment 1" in record["text_content"]


@pytest.mark.asyncio
async def test_save_raw_data(transformer, sample_issues, temp_output_dir):
    """Test saving raw issue data."""
    await transformer.save_raw_data(sample_issues)
    
    output_file = temp_output_dir / "raw_issues.json"
    assert output_file.exists()
    
    # Verify content
    data = json.loads(output_file.read_text())
    assert len(data) == 2
    assert data[0]["key"] == "TEST-123"


def test_generate_stats(transformer, sample_issues):
    """Test statistics generation."""
    stats = transformer.generate_stats(sample_issues)
    
    assert stats["total_issues"] == 2
    assert stats["projects"]["TEST"] == 2
    assert stats["statuses"]["Open"] == 1
    assert stats["statuses"]["Closed"] == 1
    assert stats["priorities"]["High"] == 1
    assert stats["priorities"]["Low"] == 1
    assert stats["total_comments"] == 1


def test_generate_stats_empty(transformer):
    """Test statistics generation with empty list."""
    stats = transformer.generate_stats([])
    assert stats == {}

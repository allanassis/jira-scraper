"""Data models for Jira scraping."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JiraComment(BaseModel):
    """Jira comment model."""
    
    id: str
    author: str
    body: str
    created: datetime
    updated: Optional[datetime] = None


class JiraIssue(BaseModel):
    """Jira issue model."""
    
    key: str
    id: str
    project: str
    summary: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    assignee: Optional[str] = None
    reporter: str
    created: datetime
    updated: datetime
    resolved: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)
    comments: List[JiraComment] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class LLMTrainingRecord(BaseModel):
    """Training record for LLM."""
    
    issue_key: str
    project: str
    metadata: Dict[str, Any]
    text_content: str
    tasks: Dict[str, Any]
    
    @classmethod
    def from_jira_issue(cls, issue: JiraIssue) -> "LLMTrainingRecord":
        """Convert Jira issue to training record."""
        # Combine description and comments
        text_parts = []
        if issue.description:
            text_parts.append(f"Description: {issue.description}")
        
        for comment in issue.comments:
            text_parts.append(f"Comment by {comment.author}: {comment.body}")
        
        text_content = "\n\n".join(text_parts)
        
        # Create metadata
        metadata = {
            "summary": issue.summary,
            "status": issue.status,
            "priority": issue.priority,
            "assignee": issue.assignee,
            "reporter": issue.reporter,
            "created": issue.created.isoformat(),
            "updated": issue.updated.isoformat(),
            "resolved": issue.resolved.isoformat() if issue.resolved else None,
            "labels": issue.labels,
            "components": issue.components,
            "comment_count": len(issue.comments),
        }
        
        # Create training tasks
        tasks = {
            "summarization": {
                "input": text_content,
                "target": issue.summary,
            },
            "classification": {
                "input": text_content,
                "target": {
                    "status": issue.status,
                    "priority": issue.priority,
                    "labels": issue.labels,
                }
            },
            "qa": {
                "context": text_content,
                "questions": [
                    f"What is the status of issue {issue.key}?",
                    f"Who reported issue {issue.key}?",
                    f"What is the priority of this issue?",
                ]
            }
        }
        
        return cls(
            issue_key=issue.key,
            project=issue.project,
            metadata=metadata,
            text_content=text_content,
            tasks=tasks,
        )

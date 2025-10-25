"""Data models for Jira scraping with validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class JiraComment(BaseModel):
    """Jira comment model."""

    id: str
    author: str
    body: str
    created: datetime
    updated: Optional[datetime] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "JiraComment":
        """Create from Jira API response with None handling."""
        if not data:
            data = {}

        author = data.get("author") or {}

        created = None
        updated = None

        if data.get("created"):
            try:
                created = datetime.fromisoformat(data["created"].replace("Z", "+00:00"))
            except Exception:
                pass

        if data.get("updated"):
            try:
                updated = datetime.fromisoformat(data["updated"].replace("Z", "+00:00"))
            except Exception:
                pass

        return cls(
            id=data.get("id") or "",
            author=author.get("displayName") or "",
            body=data.get("body") or "",
            created=created or datetime.now(),
            updated=updated,
        )


class JiraIssue(BaseModel):
    """Jira issue model with validation."""

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

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Key is required")
        return v

    @field_validator("project")
    @classmethod
    def validate_project(cls, v: str) -> str:
        if not v:
            raise ValueError("Project is required")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if not v:
            raise ValueError("Status is required")
        return v

    @field_validator("reporter")
    @classmethod
    def validate_reporter(cls, v: str) -> str:
        if not v:
            raise ValueError("Reporter is required")
        return v

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "JiraIssue":
        """Create and validate from Jira API response with None handling."""
        if not data:
            data = {}

        fields = data.get("fields") or {}

        # Parse comments with None handling
        comments = []
        comment_data = fields.get("comment")
        if comment_data and isinstance(comment_data, dict):
            for comment in comment_data.get("comments", []):
                if comment:
                    try:
                        comments.append(JiraComment.from_api_response(comment))
                    except Exception:
                        continue

        # Parse dates with None handling
        created = None
        updated = None
        resolved = None

        if fields.get("created"):
            try:
                created = datetime.fromisoformat(
                    fields["created"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        if fields.get("updated"):
            try:
                updated = datetime.fromisoformat(
                    fields["updated"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        if fields.get("resolutiondate"):
            try:
                resolved = datetime.fromisoformat(
                    fields["resolutiondate"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        # Extract fields with safe None handling
        project = fields.get("project") or {}
        status = fields.get("status") or {}
        reporter = fields.get("reporter") or {}
        priority = fields.get("priority") or {}
        assignee = fields.get("assignee") or {}

        return cls(
            key=data.get("key") or "",
            id=data.get("id") or "",
            project=project.get("key") or "",
            summary=fields.get("summary") or "",
            description=fields.get("description"),
            status=status.get("name") or "",
            priority=priority.get("name"),
            assignee=assignee.get("displayName"),
            reporter=reporter.get("displayName") or "",
            created=created or datetime.now(),
            updated=updated or datetime.now(),
            resolved=resolved,
            labels=fields.get("labels") or [],
            components=[
                c.get("name", "")
                for c in (fields.get("components") or [])
                if c and isinstance(c, dict)
            ],
            comments=comments,
            raw_data=data,
        )


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
                },
            },
            "qa": {
                "context": text_content,
                "questions": [
                    f"What is the status of issue {issue.key}?",
                    f"Who reported issue {issue.key}?",
                    f"What is the priority of this issue?",
                ],
            },
        }

        return cls(
            issue_key=issue.key,
            project=issue.project,
            metadata=metadata,
            text_content=text_content,
            tasks=tasks,
        )

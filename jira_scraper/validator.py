"""Response validation using Pydantic."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError, field_validator


class JiraFieldsValidator(BaseModel):
    """Validates Jira issue fields."""
    project: Dict[str, Any]
    summary: str
    status: Dict[str, Any]
    reporter: Dict[str, Any]
    created: str
    updated: str
    priority: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, Any]] = None
    labels: List[str] = []
    components: List[Dict[str, Any]] = []

    @field_validator('project')
    @classmethod
    def validate_project(cls, v):
        if 'key' not in v:
            raise ValueError('Project must have key')
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if 'name' not in v:
            raise ValueError('Status must have name')
        return v

    @field_validator('reporter')
    @classmethod
    def validate_reporter(cls, v):
        if 'displayName' not in v:
            raise ValueError('Reporter must have displayName')
        return v


class JiraIssueValidator(BaseModel):
    """Validates complete Jira issue response."""
    key: str
    id: str
    fields: JiraFieldsValidator


class JiraSearchValidator(BaseModel):
    """Validates Jira search response."""
    issues: List[Dict[str, Any]]
    total: Optional[int] = None

    def validate_issues(self) -> List[str]:
        """Validate all issues and return error messages."""
        errors = []
        for i, issue in enumerate(self.issues):
            try:
                JiraIssueValidator(**issue)
            except ValidationError as e:
                errors.append(f"Issue {i}: {str(e)}")
        return errors


def validate_issue(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate single issue. Returns (is_valid, errors)."""
    try:
        JiraIssueValidator(**data)
        return True, []
    except ValidationError as e:
        return False, [str(e)]


def validate_search_response(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate search response. Returns (is_valid, errors)."""
    try:
        validator = JiraSearchValidator(**data)
        issue_errors = validator.validate_issues()
        return len(issue_errors) == 0, issue_errors
    except ValidationError as e:
        return False, [str(e)]

"""Data transformation for LLM training."""

import json
from pathlib import Path
from typing import List

import aiofiles

from .models import JiraIssue, LLMTrainingRecord


class DataTransformer:
    """Transform Jira data into LLM training format."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def transform_issues(self, issues: List[JiraIssue]) -> None:
        """Transform issues and save as JSONL."""
        output_file = self.output_dir / "training_data.jsonl"

        async with aiofiles.open(output_file, "w") as f:
            for issue in issues:
                # Skip issues without meaningful content
                if not issue.description and not issue.comments:
                    continue

                try:
                    record = LLMTrainingRecord.from_jira_issue(issue)
                    line = json.dumps(record.model_dump(), ensure_ascii=False)
                    await f.write(line + "\n")
                except Exception as e:
                    print(f"Error transforming issue {issue.key}: {e}")

        print(f"Saved training data to {output_file}")

    async def save_raw_data(self, issues: List[JiraIssue]) -> None:
        """Save raw issue data for debugging."""
        output_file = self.output_dir / "raw_issues.json"

        data = [issue.model_dump() for issue in issues]

        async with aiofiles.open(output_file, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str, ensure_ascii=False))

        print(f"Saved raw data to {output_file}")

    def generate_stats(self, issues: List[JiraIssue]) -> dict:
        """Generate statistics about the scraped data."""
        if not issues:
            return {}

        projects = {}
        statuses = {}
        priorities = {}
        total_comments = 0

        for issue in issues:
            # Project stats
            projects[issue.project] = projects.get(issue.project, 0) + 1

            # Status stats
            statuses[issue.status] = statuses.get(issue.status, 0) + 1

            # Priority stats
            if issue.priority:
                priorities[issue.priority] = priorities.get(issue.priority, 0) + 1

            # Comment stats
            total_comments += len(issue.comments)

        return {
            "total_issues": len(issues),
            "projects": projects,
            "statuses": statuses,
            "priorities": priorities,
            "total_comments": total_comments,
            "avg_comments_per_issue": total_comments / len(issues) if issues else 0,
        }

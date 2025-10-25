"""Simplified Jira scraper using unified models."""

import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Set

from .http_client import JiraHttpClient
from .models import JiraIssue


class JiraScraper:

    def __init__(
        self,
        projects: List[str],
        output_dir: Path,
        max_concurrent: int = 5,
        rate_limit_delay: float = 1.0,
        max_issues_per_project: Optional[int] = None,
    ):
        self.projects = projects
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self.max_issues_per_project = max_issues_per_project

        # State management
        self.state_file = self.output_dir / "scraper_state.json"
        self.processed_issues: Set[str] = set()
        self.load_state()

        # HTTP client
        self.client = JiraHttpClient(rate_limit_delay=rate_limit_delay)

    def load_state(self) -> None:
        """Load scraper state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.processed_issues = set(state.get("processed_issues", []))
            except Exception:
                pass

    def save_state(self) -> None:
        """Save scraper state to disk."""
        state = {"processed_issues": list(self.processed_issues)}
        with open(self.state_file, "w") as f:
            json.dump(state, f)

    async def get_project_issues(self, project: str) -> AsyncGenerator[str, None]:
        """Get all issue keys for a project."""
        async for issue in self.client.search_issues(project, fields="key"):
            yield issue["key"]

    async def get_issue_details(self, issue_key: str) -> Optional[JiraIssue]:
        """Get detailed issue information with automatic validation."""
        if issue_key in self.processed_issues:
            return None

        try:
            data = await self.client.get_issue(issue_key)

            # Create and validate in one step using Pydantic
            issue = JiraIssue.from_api_response(data)
            self.processed_issues.add(issue_key)
            return issue

        except Exception as e:
            print(f"Error fetching/validating issue {issue_key}: {e}")
            return None

    async def scrape_project(self, project: str) -> List[JiraIssue]:
        """Scrape all issues from a project."""
        print(f"Scraping project: {project}")
        issues = []

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def fetch_issue(issue_key: str) -> Optional[JiraIssue]:
            async with semaphore:
                return await self.get_issue_details(issue_key)

        # Get all issue keys
        issue_keys = []
        async for issue_key in self.get_project_issues(project):
            issue_keys.append(issue_key)
            if (
                self.max_issues_per_project
                and len(issue_keys) >= self.max_issues_per_project
            ):
                break

        print(f"Found {len(issue_keys)} issues in {project}")

        # Fetch issues async
        tasks = [fetch_issue(key) for key in issue_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, JiraIssue):
                issues.append(result)
            elif isinstance(result, Exception):
                print(f"Error processing issue: {result}")

        self.save_state()
        return issues

    async def scrape_all_projects(self) -> List[JiraIssue]:
        """Scrape all configured projects."""
        all_issues = []

        for project in self.projects:
            try:
                issues = await self.scrape_project(project)
                all_issues.extend(issues)
                print(f"Scraped {len(issues)} issues from {project}")
            except Exception as e:
                print(f"Failed to scrape project {project}: {e}")

        return all_issues

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()
        self.save_state()

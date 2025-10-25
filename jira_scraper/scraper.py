"""Jira scraper implementation."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Set

from .models import JiraComment, JiraIssue
from .http_client import JiraHttpClient
from .validator import validate_issue


class JiraScraper:
    """Apache Jira scraper with fault tolerance and resumption."""
    
    def __init__(
        self,
        projects: List[str],
        output_dir: Path,
        max_concurrent: int = 5,
        rate_limit_delay: float = 1.0,
    ):
        self.projects = projects
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        
        # State management
        self.state_file = self.output_dir / "scraper_state.json"
        self.processed_issues: Set[str] = set()
        self.load_state()
        
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
        """Get detailed issue information with validation."""
        if issue_key in self.processed_issues:
            return None

        try:
            data = await self.client.get_issue(issue_key)

            # Validate response
            is_valid, errors = validate_issue(data)
            if not is_valid:
                print(f"Invalid issue {issue_key}: {errors}")
                return None
  
            issue = self._parse_issue(data)
            self.processed_issues.add(issue_key)
            return issue
            
        except Exception as e:
            print(f"Error fetching issue {issue_key}: {e}")
            return None
    
    def _parse_issue(self, data: dict) -> JiraIssue:
        """Parse Jira API response into JiraIssue model."""
        fields = data["fields"]
        
        # Parse comments
        comments = []
        if "comment" in fields and fields["comment"]:
            for comment_data in fields["comment"].get("comments", []):
                try:
                    comment = JiraComment(
                        id=comment_data["id"],
                        author=comment_data["author"]["displayName"],
                        body=comment_data["body"],
                        created=datetime.fromisoformat(
                            comment_data["created"].replace("Z", "+00:00")
                        ),
                        updated=datetime.fromisoformat(
                            comment_data["updated"].replace("Z", "+00:00")
                        ) if comment_data.get("updated") else None,
                    )
                    comments.append(comment)
                except Exception:
                    continue
        
        # Parse dates
        created = datetime.fromisoformat(fields["created"].replace("Z", "+00:00"))
        updated = datetime.fromisoformat(fields["updated"].replace("Z", "+00:00"))
        resolved = None
        if fields.get("resolutiondate"):
            resolved = datetime.fromisoformat(
                fields["resolutiondate"].replace("Z", "+00:00")
            )
        
        return JiraIssue(
            key=data["key"],
            id=data["id"],
            project=fields["project"]["key"],
            summary=fields["summary"],
            description=fields.get("description", ""),
            status=fields["status"]["name"],
            priority=fields["priority"]["name"] if fields.get("priority") else None,
            assignee=fields["assignee"]["displayName"] if fields.get("assignee") else None,
            reporter=fields["reporter"]["displayName"],
            created=created,
            updated=updated,
            resolved=resolved,
            labels=fields.get("labels", []),
            components=[c["name"] for c in fields.get("components", [])],
            comments=comments,
            raw_data=data,
        )
    
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
        
        print(f"Found {len(issue_keys)} issues in {project}")
        
        # Fetch issues concurrently
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

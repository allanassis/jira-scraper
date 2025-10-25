"""Jira scraper implementation."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Set

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .models import JiraComment, JiraIssue


class JiraScraper:
    """Apache Jira scraper with fault tolerance and resumption."""
    
    BASE_URL = "https://issues.apache.org/jira"
    
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
        self.rate_limit_delay = rate_limit_delay
        
        # State management
        self.state_file = self.output_dir / "scraper_state.json"
        self.processed_issues: Set[str] = set()
        self.load_state()
        
        # HTTP client with retries
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=max_concurrent),
        )
    
    def load_state(self) -> None:
        """Load scraper state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.processed_issues = set(state.get("processed_issues", []))
            except Exception:
                pass  # Start fresh if state is corrupted
    
    def save_state(self) -> None:
        """Save scraper state to disk."""
        state = {"processed_issues": list(self.processed_issues)}
        with open(self.state_file, "w") as f:
            json.dump(state, f)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request with retry logic."""
        await asyncio.sleep(self.rate_limit_delay)  # Rate limiting
        
        response = await self.client.get(url, params=params)
        
        if response.status_code == 429:
            # Rate limited - wait longer
            await asyncio.sleep(2)
            raise httpx.HTTPError("Rate limited")
        
        response.raise_for_status()
        return response.json()
    
    async def get_project_issues(self, project: str) -> AsyncGenerator[str, None]:
        """Get all issue keys for a project."""
        start_at = 0
        max_results = 50
        
        while True:
            url = f"{self.BASE_URL}/rest/api/2/search"
            params = {
                "jql": f"project = {project} ORDER BY created DESC",
                "startAt": start_at,
                "maxResults": max_results,
                "fields": "key",
            }
            
            try:
                data = await self._make_request(url, params)
                issues = data.get("issues", [])
                
                if not issues:
                    break
                
                for issue in issues:
                    yield issue["key"]
                
                # Check if we've got all issues
                if len(issues) < max_results:
                    break
                
                start_at += max_results
                
            except Exception as e:
                print(f"Error fetching issues for {project}: {e}")
                break
    
    async def get_issue_details(self, issue_key: str) -> Optional[JiraIssue]:
        """Get detailed issue information."""
        if issue_key in self.processed_issues:
            return None
        
        url = f"{self.BASE_URL}/rest/api/2/issue/{issue_key}"
        params = {
            "expand": "comments",
            "fields": "*all",
        }
        
        try:
            data = await self._make_request(url, params)
            issue = self._parse_issue(data)
            self.processed_issues.add(issue_key)
            return issue
            
        except Exception as e:
            print(f"Error fetching issue {issue_key}: {e}")
            return None
    
    def _parse_issue(self, data: Dict) -> JiraIssue:
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
                    continue  # Skip malformed comments
        
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
        
        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_issue(issue_key: str) -> Optional[JiraIssue]:
            async with semaphore:
                return await self.get_issue_details(issue_key)
        
        # Get all issue keys first
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
        
        # Save state periodically
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
        await self.client.aclose()
        self.save_state()

import asyncio
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class JiraHttpClient:
    """HTTP client for Jira API v2 with built-in error handling and rate limiting."""

    def __init__(
        self,
        base_url: str = "https://issues.apache.org/jira",
        rate_limit_delay: float = 1.0,
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.rate_limit_delay = rate_limit_delay

        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=10),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and rate limiting."""
        await asyncio.sleep(self.rate_limit_delay)

        url = f"{self.base_url}{endpoint}"
        response = await self.client.request(method, url, params=params, **kwargs)

        if response.status_code == 429:
            await asyncio.sleep(10)
            raise httpx.HTTPError("Rate limited")

        response.raise_for_status()
        return response.json()  # type: ignore

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """GET request."""
        return await self.request("GET", endpoint, params=params)

    async def search_issues(
        self,
        project: str,
        fields: str = "key",
        max_results: int = 50,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Paginated JQL search using API v2."""
        start_at = 0

        while True:
            params = {
                "jql": f"project = {project} ORDER BY created DESC",
                "startAt": start_at,
                "maxResults": max_results,
                "fields": fields,
            }

            data = await self.get("/rest/api/2/search", params)
            issues = data.get("issues", [])

            for issue in issues:
                yield issue

            if len(issues) < max_results:
                break

            start_at += max_results

    async def get_issue(
        self, issue_key: str, expand: str = "comments"
    ) -> Dict[str, Any]:
        """Get single issue details using API v2."""
        params = {
            "expand": expand,
            "fields": "*all",
        }
        return await self.get(f"/rest/api/2/issue/{issue_key}", params)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

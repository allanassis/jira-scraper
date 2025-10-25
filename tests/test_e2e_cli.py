"""End-to-end CLI test without mocks."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_e2e_real_api():
    """Test CLI end-to-end with real Jira API."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        # Run CLI with limit for quick test
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jira_scraper.cli",
                "--projects",
                "KAFKA",
                "--output-dir",
                str(output_dir),
                "--max-concurrent",
                "1",
                "--rate-limit",
                "2.0",
                "--limit",
                "3",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Verify CLI executed successfully
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "Scraping completed!" in result.stdout

        # Verify output files exist
        training_file = output_dir / "training_data.jsonl"
        raw_file = output_dir / "raw_issues.json"
        stats_file = output_dir / "stats.json"

        assert training_file.exists()
        assert raw_file.exists()
        assert stats_file.exists()

        # Verify files have content
        assert training_file.stat().st_size > 0
        assert raw_file.stat().st_size > 0

        # Verify stats content
        with open(stats_file) as f:
            stats = json.load(f)
        assert "projects" in stats
        assert "KAFKA" in stats["projects"]
        assert stats["projects"]["KAFKA"] <= 3  # Respects limit

        # Verify training data format
        with open(training_file) as f:
            first_line = f.readline().strip()
            record = json.loads(first_line)

        assert "issue_key" in record
        assert "project" in record
        assert "text_content" in record
        assert record["project"] == "KAFKA"

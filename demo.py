#!/usr/bin/env python3
"""Demo script to test the Jira scraper with a small dataset."""

import asyncio
import json
from pathlib import Path

from jira_scraper.scraper import JiraScraper
from jira_scraper.transformer import DataTransformer


async def demo():
    """Run a small demo of the scraper."""
    print("🚀 Starting Jira Scraper Demo")
    
    # Create output directory
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize scraper with conservative settings
    scraper = JiraScraper(
        projects=["STDCXX"],  # Just one project for demo
        output_dir=output_dir,
        max_concurrent=2,    # Be respectful
        rate_limit_delay=2.0,  # 2 second delay between requests
    )
    
    transformer = DataTransformer(output_dir)
    
    try:
        print("📡 Fetching first few issues from STDCXX project...")
        
        # Get just a few issues for demo
        issues = []
        issue_count = 0
        max_issues = 5  # Limit for demo
        
        async for issue_key in scraper.get_project_issues("STDCXX"):
            if issue_count >= max_issues:
                break
                
            print(f"  Fetching {issue_key}...")
            issue = await scraper.get_issue_details(issue_key)
            if issue:
                issues.append(issue)
                issue_count += 1
        
        print(f"✅ Successfully scraped {len(issues)} issues")
        
        # Transform and save data
        print("🔄 Transforming data...")
        await transformer.transform_issues(issues)
        await transformer.save_raw_data(issues)
        
        # Generate statistics
        stats = transformer.generate_stats(issues)
        stats_file = output_dir / "stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
        
        print("📊 Statistics:")
        print(f"  Total issues: {stats['total_issues']}")
        print(f"  Total comments: {stats['total_comments']}")
        print(f"  Avg comments per issue: {stats['avg_comments_per_issue']:.1f}")
        
        print(f"\n📁 Output saved to: {output_dir}")
        print("  - training_data.jsonl: LLM training data")
        print("  - raw_issues.json: Raw Jira data")
        print("  - stats.json: Statistics")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(demo())

"""Command line interface for Jira scraper."""

import asyncio
import json
from pathlib import Path

import click
from click.testing import CliRunner
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .scraper import JiraScraper
from .transformer import DataTransformer

console = Console()


@click.command()
@click.option(
    "--projects",
    "-p",
    required=True,
    multiple=True,
    default=[],# ["KAFKA", "SPARK", "HADOOP"],
    help="Jira projects to scrape",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default="output",
    help="Output directory for scraped data",
)
@click.option(
    "--max-concurrent",
    "-c",
    type=int,
    default=5,
    help="Maximum concurrent requests",
)
@click.option(
    "--rate-limit",
    "-r",
    type=float,
    default=1.0,
    help="Rate limit delay in seconds",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from previous scraping session",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Limit number of issues per project (for testing)",
)
def main(
    projects: tuple,
    output_dir: Path,
    max_concurrent: int,
    rate_limit: float,
    resume: bool,
    limit: int,
) -> None:
    """Scrape Apache Jira issues for LLM training data.
    \n
       Ex:  python -m jira_scraper.cli -p KAFKA -p SPARK -o output-data -l 10
    """
    console.print("[bold blue]Jira Scraper for LLM Training Data[/bold blue]")
    console.print(f"Projects: {', '.join(projects)}")
    console.print(f"Output directory: {output_dir}")
    console.print(f"Max concurrent requests: {max_concurrent}")
    console.print(f"Rate limit: {rate_limit}s")

    if not resume:
        # Clear previous state
        state_file = output_dir / "scraper_state.json"
        if state_file.exists():
            state_file.unlink()

    asyncio.run(scrape_data(projects, output_dir, max_concurrent, rate_limit, limit))


async def scrape_data(
    projects: tuple,
    output_dir: Path,
    max_concurrent: int,
    rate_limit: float,
    limit: int,
) -> None:
    """Main scraping logic."""
    scraper = JiraScraper(
        projects=list(projects),
        output_dir=output_dir,
        max_concurrent=max_concurrent,
        rate_limit_delay=rate_limit,
        max_issues_per_project=limit,
    )

    transformer = DataTransformer(output_dir)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scraping Jira issues...", total=None)

            # Scrape all projects
            issues = await scraper.scrape_all_projects()

            progress.update(task, description="Transforming data...")

            # Transform and save data
            await transformer.transform_issues(issues)
            await transformer.save_raw_data(issues)

            # Generate and save statistics
            stats = transformer.generate_stats(issues)
            stats_file = output_dir / "stats.json"
            with open(stats_file, "w") as f:
                json.dump(stats, f, indent=2)

            progress.update(task, description="Complete!")

        # Display results
        console.print(f"\n[bold green]Scraping completed![/bold green]")
        console.print(f"Total issues scraped: {len(issues)}")
        console.print(f"Output saved to: {output_dir}")

        # Display statistics
        if issues:
            console.print("\n[bold]Statistics:[/bold]")
            for project, count in stats["projects"].items():
                console.print(f"  {project}: {count} issues")
            console.print(f"  Total comments: {stats['total_comments']}")
            console.print(
                f"  Avg comments per issue: {stats['avg_comments_per_issue']:.1f}"
            )

    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Scraping interrupted. State saved for resumption.[/yellow]"
        )
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
    finally:
        await scraper.close()


if __name__ == "__main__":
    main()

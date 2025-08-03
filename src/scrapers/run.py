"""CLI runner for scrapers."""

import asyncio
import sys
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.core.logging import setup_logging, get_logger
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.github_scraper import GitHubScraper
from src.scrapers.forum_scraper import ForumScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.scrapers.source_manager import SourceManager
from src.services.model_service import ModelService

console = Console()
logger = get_logger(__name__)


async def run_single_scraper(scraper_name: str, limit: int = 100, max_chars: Optional[int] = None) -> dict:
    """Run a single scraper."""
    # Override LLM max chars if provided
    if max_chars is not None:
        from src.core.config import settings
        settings.llm_max_chars = max_chars
        logger.info(f"Using custom LLM character limit: {max_chars}")
    
    scrapers = {
        "reddit": RedditScraper(),
        "github": GitHubScraper(),
        "forum": ForumScraper(),
        "hackernews": HackerNewsScraper(),
    }
    
    if scraper_name not in scrapers:
        raise ValueError(f"Unknown scraper: {scraper_name}")
    
    scraper = scrapers[scraper_name]
    
    try:
        result = await scraper.scrape(limit=limit)
        
        # Process results and update model docs
        if result["status"] == "success":
            practices = result.get("practices", {})
            posts = result.get("posts", [])
            
            # Update relevant models
            await update_model_practices(practices, posts)
        
        return result
    finally:
        # Clean up
        if hasattr(scraper, "close"):
            await scraper.close()


async def run_all_scrapers(limit: int = 100, max_chars: Optional[int] = None) -> dict:
    """Run all scrapers concurrently."""
    scrapers = ["reddit", "github", "forum", "hackernews"]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running all scrapers...", total=len(scrapers))
        
        results = {}
        tasks = []
        
        for scraper_name in scrapers:
            task_coro = run_single_scraper(scraper_name, limit, max_chars)
            tasks.append((scraper_name, task_coro))
        
        # Run concurrently
        for scraper_name, task_coro in tasks:
            progress.update(task, description=f"Running {scraper_name} scraper...")
            try:
                result = await task_coro
                results[scraper_name] = result
                console.print(f"[green]✓[/green] {scraper_name}: {result['status']}")
            except Exception as e:
                results[scraper_name] = {"status": "error", "error": str(e)}
                console.print(f"[red]✗[/red] {scraper_name}: {e}")
            progress.advance(task)
    
    return results


async def update_model_practices(practices: dict, posts: list):
    """Update model documentation with new practices."""
    model_service = ModelService()
    
    # Extract model-specific practices
    models_data = practices.get("models", {})
    
    for model_id, model_practices in models_data.items():
        try:
            # Load existing practices
            existing = await model_service.get_model_practices(
                category="text",  # Would need to determine category
                model_id=model_id
            )
            
            if existing:
                # Merge new practices
                # This is simplified - in production, implement proper merging
                logger.info(f"Updated practices for {model_id}")
            else:
                # Create new model entry
                logger.info(f"Created new practices for {model_id}")
                
        except Exception as e:
            logger.error(f"Error updating {model_id}: {e}")


def display_summary(results: dict):
    """Display summary of scraping results."""
    table = Table(title="Scraping Summary")
    table.add_column("Source", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Posts", style="yellow")
    table.add_column("Practices", style="blue")
    
    total_posts = 0
    total_practices = 0
    
    for source, result in results.items():
        status = result.get("status", "unknown")
        posts = len(result.get("posts", []))
        practices = result.get("practices_extracted", 0)
        
        total_posts += posts
        total_practices += practices
        
        status_display = "[green]Success[/green]" if status == "success" else f"[red]{status}[/red]"
        table.add_row(source, status_display, str(posts), str(practices))
    
    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {total_posts} posts, {total_practices} practices extracted")


@click.command()
@click.argument("source", type=click.Choice(["reddit", "github", "forum", "hackernews", "all"]))
@click.option("--limit", "-l", default=100, help="Maximum posts to scrape")
@click.option("--update-models", "-u", is_flag=True, help="Update model documentation")
@click.option("--llm-max-chars", "-c", type=int, help="Maximum characters to send to LLM (overrides config)")
def main(source: str, limit: int, update_models: bool, llm_max_chars: Optional[int]):
    """Run scrapers to collect AI best practices."""
    setup_logging()
    
    console.print(f"[bold blue]SOTA Practices Scraper[/bold blue]")
    console.print(f"Source: {source}, Limit: {limit}")
    
    if llm_max_chars:
        console.print(f"[cyan]LLM character limit: {llm_max_chars}[/cyan]")
    
    if update_models:
        console.print("[yellow]Model updates enabled[/yellow]")
    
    try:
        if source == "all":
            results = asyncio.run(run_all_scrapers(limit, llm_max_chars))
            display_summary(results)
        else:
            result = asyncio.run(run_single_scraper(source, limit, llm_max_chars))
            console.print(f"\n[bold]Results for {source}:[/bold]")
            
            if result["status"] == "success":
                posts = result.get("posts", [])
                practices = result.get("practices", {})
                
                console.print(f"Posts scraped: {len(posts)}")
                console.print(f"Timestamp: {result.get('timestamp')}")
                
                # Show sample practices
                if practices:
                    console.print("\n[bold]Sample practices extracted:[/bold]")
                    for key, value in list(practices.items())[:3]:
                        if isinstance(value, list):
                            console.print(f"- {key}: {len(value)} items")
                        elif isinstance(value, dict):
                            console.print(f"- {key}: {len(value)} entries")
            else:
                console.print(f"[red]Error: {result.get('error')}[/red]")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Scraping interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Scraping failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
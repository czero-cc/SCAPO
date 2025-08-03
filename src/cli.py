"""Command-line interface for SOTA Practices."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from src.core.config import settings
from src.core.logging import setup_logging
from src.services.model_service import ModelService
from src.services.scraper_service import ScraperService

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """SOTA Practices CLI - Manage AI model best practices."""
    setup_logging()


@cli.group()
def models():
    """Manage model best practices."""
    pass


@models.command()
@click.option("--category", "-c", help="Filter by category")
def list(category: Optional[str] = None):
    """List all available models."""
    async def _list():
        service = ModelService()
        result = await service.list_models(category=category)
        
        table = Table(title="Available Models")
        table.add_column("Category", style="cyan")
        table.add_column("Models", style="green")
        
        for cat, models in result.items():
            table.add_row(cat, ", ".join(models))
        
        console.print(table)
    
    asyncio.run(_list())


@models.command()
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results")
def search(query: str, limit: int):
    """Search for models."""
    async def _search():
        service = ModelService()
        results = await service.search_models(query=query, limit=limit)
        
        if not results:
            console.print(f"[yellow]No models found for query: {query}[/yellow]")
            return
        
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("Model ID", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Match Type", style="yellow")
        
        for result in results:
            table.add_row(
                result["model_id"],
                result["category"],
                result["match_type"],
            )
        
        console.print(table)
    
    asyncio.run(_search())


@cli.group()
def scrape():
    """Run web scrapers."""
    pass


@scrape.command()
@click.argument("source", type=click.Choice(["reddit", "all"]))
@click.option("--target", "-t", help="Specific target (e.g., subreddit)")
@click.option("--limit", "-l", default=100, help="Maximum posts to scrape")
def run(source: str, target: Optional[str], limit: int):
    """Run a scraper."""
    async def _run():
        service = ScraperService()
        
        with console.status(f"[bold green]Running {source} scraper..."):
            if source == "all":
                results = await service.run_all_scrapers(limit=limit)
                for src, result in results.items():
                    if result["status"] == "success":
                        console.print(
                            f"[green]✓[/green] {src}: "
                            f"{result['posts_scraped']} posts, "
                            f"{result['practices_extracted']} practices"
                        )
                    else:
                        console.print(
                            f"[red]✗[/red] {src}: {result.get('error', 'Unknown error')}"
                        )
            else:
                result = await service.run_scraper(
                    source=source,
                    target=target,
                    limit=limit,
                )
                
                if result["status"] == "success":
                    console.print(
                        f"[green]Success![/green] Scraped {result['posts_scraped']} posts, "
                        f"extracted {result['practices_extracted']} practices"
                    )
                else:
                    console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")
    
    asyncio.run(_run())


@scrape.command()
def status():
    """Check scraper status."""
    async def _status():
        service = ScraperService()
        status = await service.get_status()
        
        table = Table(title="Scraper Status")
        table.add_column("Source", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Last Run", style="yellow")
        table.add_column("Total Posts", style="blue")
        
        for source, info in status["scrapers"].items():
            table.add_row(
                source,
                info["status"],
                str(info["last_run"]) if info["last_run"] else "Never",
                str(info["total_posts"]),
            )
        
        console.print(table)
        console.print(
            f"\nTotal scrapers: {status['total_scrapers']}, "
            f"Active: {status['active_scrapers']}"
        )
    
    asyncio.run(_status())


@cli.command()
def serve():
    """Start the API server."""
    import uvicorn
    
    console.print("[bold green]Starting SOTA Practices API server...[/bold green]")
    uvicorn.run(
        "src.api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
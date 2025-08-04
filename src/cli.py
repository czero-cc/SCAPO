"""CLI for SOTA Practices."""

import asyncio
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.logging import setup_logging, get_logger
from src.services.scraper_service import ScraperService
from src.services.data_service import DataService
from src.services.scheduler import SchedulerManager
from src.services.model_service import ModelService
from src.core.database import SessionLocal, engine, Base
from src.core.config import settings

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """SOTA Practices CLI - Manage AI/ML best practices scraping and processing."""
    setup_logging()


@cli.command()
@click.option("--drop", is_flag=True, help="Drop existing tables first")
def init_db(drop):
    """Initialize database tables."""
    if drop:
        console.print("[yellow]Dropping existing tables...[/yellow]")
        Base.metadata.drop_all(bind=engine)
    
    console.print("[blue]Creating database tables...[/blue]")
    Base.metadata.create_all(bind=engine)
    console.print("[green]✓[/green] Database initialized successfully")


@cli.group()
def scrape():
    """Run web scrapers."""
    pass


@scrape.command()
@click.option("--sources", "-s", multiple=True, 
              help="Sources to scrape (e.g., reddit:LocalLLaMA hackernews github:dair-ai/Prompt-Engineering-Guide)")
@click.option("--limit", "-l", default=10, help="Maximum posts per source")
@click.option("--llm-max-chars", "-c", type=int, help="Max characters for LLM processing")
def run(sources, limit, llm_max_chars):
    """Run intelligent scraper to collect AI/ML best practices.
    
    Examples:
        sota scrape run -s reddit:LocalLLaMA -s hackernews
        sota scrape run -s reddit:OpenAI -s reddit:StableDiffusion -l 5
        sota scrape run  # Uses default sources
    """
    async def _run():
        service = ScraperService()
        
        # Convert sources tuple to list, or use None for defaults
        sources_list = list(sources) if sources else None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running intelligent scraper...", total=None)
            
            result = await service.run_scrapers(
                sources=sources_list,
                max_posts_per_source=limit,
                llm_max_chars=llm_max_chars,
            )
            
            display_scraper_result(result)
            
            progress.stop()
    
    asyncio.run(_run())


@scrape.command()
def status():
    """Show scraper status and metrics."""
    async def _status():
        db = SessionLocal()
        data_service = DataService(db)
        scraper_service = ScraperService()
        
        # Get scraper status
        scraper_status = await scraper_service.get_status()
        
        # Get metrics
        metrics = await data_service.get_scraper_metrics(hours=24)
        
        # Display scraper status
        console.print("\n[bold]Scraper Status[/bold]")
        status_table = Table()
        status_table.add_column("Source", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Last Run", style="yellow")
        status_table.add_column("Total Posts", style="blue")
        
        for source, info in scraper_status["scrapers"].items():
            status_table.add_row(
                source,
                info["status"],
                str(info["last_run"]) if info["last_run"] else "Never",
                str(info["total_posts"]),
            )
        
        console.print(status_table)
        
        # Display scraper runs
        console.print("\n[bold]Activity (Last 24 Hours)[/bold]")
        table = Table()
        table.add_column("Scraper", style="cyan")
        table.add_column("Runs", style="yellow")
        table.add_column("Posts", style="green")
        table.add_column("Practices", style="blue")
        table.add_column("Avg Duration", style="magenta")
        table.add_column("Failure Rate", style="red")
        
        for run in metrics["scraper_runs"]:
            table.add_row(
                run["scraper"],
                str(run["runs"]),
                str(run["total_posts"]),
                str(run["total_practices"]),
                f"{run['avg_duration_seconds']:.1f}s",
                f"{run['failure_rate']*100:.1f}%",
            )
        
        console.print(table)
        
        db.close()
    
    asyncio.run(_status())


@cli.group()
def models():
    """Manage model best practices."""
    pass


@models.command()
@click.option("--category", "-c", help="Filter by category")
def list(category):
    """List all available models."""
    async def _list():
        service = ModelService()
        all_models = await service.list_models(category=category)
        
        console.print("\n[bold]Available Models[/bold]")
        
        for cat, model_list in all_models.items():
            if model_list:
                console.print(f"\n[cyan]{cat.upper()}[/cyan]")
                for model in model_list:
                    # Get practice info
                    practices = await service.get_model_practices(cat, model)
                    if practices:
                        stats = f"({len(practices.prompt_examples)} prompts, "
                        stats += f"{len(practices.parameters)} params, "
                        stats += f"{len(practices.tips)} tips)"
                        console.print(f"  • {model} {stats}")
                    else:
                        console.print(f"  • {model}")
    
    asyncio.run(_list())


@models.command()
@click.argument("model_id")
@click.option("--category", "-c", default="text", help="Model category")
def info(model_id, category):
    """Show detailed info for a specific model."""
    async def _info():
        service = ModelService()
        practices = await service.get_model_practices(category, model_id)
        
        if not practices:
            console.print(f"[red]Model {model_id} not found[/red]")
            return
        
        console.print(f"\n[bold]{practices.model_name}[/bold]")
        console.print(f"Category: {practices.category.value}")
        console.print(f"Last Updated: {practices.last_updated.strftime('%Y-%m-%d')}")
        
        # Show statistics
        console.print("\n[bold]Content Statistics:[/bold]")
        console.print(f"  • Prompt Examples: {len(practices.prompt_examples)}")
        console.print(f"  • Parameters: {len(practices.parameters)}")
        console.print(f"  • Tips: {len(practices.tips)}")
        console.print(f"  • Pitfalls: {len(practices.pitfalls)}")
        console.print(f"  • Sources: {len(practices.sources)}")
        
        # Show sample content
        if practices.prompt_examples:
            console.print("\n[bold]Sample Prompt:[/bold]")
            example = practices.prompt_examples[0]
            console.print(f"Title: {example.title}")
            console.print(f"```\n{example.prompt[:200]}...\n```")
        
        if practices.parameters:
            console.print("\n[bold]Key Parameters:[/bold]")
            for param in practices.parameters[:5]:
                console.print(f"  • {param.name}: {param.recommended_value}")
    
    asyncio.run(_info())


@models.command()
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results")
def search(query, limit):
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


@cli.command()
@click.option("--worker", "-w", is_flag=True, help="Start Celery worker")
@click.option("--beat", "-b", is_flag=True, help="Start Celery beat scheduler")
@click.option("--both", is_flag=True, help="Start both worker and beat")
def scheduler(worker, beat, both):
    """Manage the scraping scheduler."""
    if both or (not worker and not beat):
        # Start both
        console.print("[blue]Starting scheduler services...[/blue]")
        manager = SchedulerManager()
        manager.start()
        console.print("[green]✓[/green] Scheduler services started")
        console.print("\nPress Ctrl+C to stop")
        
        try:
            import signal
            signal.pause()
        except KeyboardInterrupt:
            manager.stop()
    elif worker:
        console.print("[blue]Starting Celery worker...[/blue]")
        import subprocess
        subprocess.run([
            sys.executable, "-m", "celery",
            "-A", "src.services.scheduler", "worker",
            "--loglevel=info", "--concurrency=2"
        ])
    elif beat:
        console.print("[blue]Starting Celery beat...[/blue]")
        import subprocess
        subprocess.run([
            sys.executable, "-m", "celery",
            "-A", "src.services.scheduler", "beat",
            "--loglevel=info"
        ])


@cli.command()
@click.option("--limit", "-l", default=50, help="Number of posts to process")
def process_pending(limit):
    """Process unprocessed posts through LLM."""
    async def _process():
        from src.services.scheduler import _process_pending_posts
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing pending posts...", total=None)
            
            result = await _process_pending_posts()
            
            progress.stop()
            
        console.print(f"\n[green]✓[/green] Processed {result['processed']} posts")
        console.print(f"[blue]→[/blue] Extracted {result['practices_extracted']} practices")
        if result['errors'] > 0:
            console.print(f"[red]✗[/red] {result['errors']} errors")
    
    asyncio.run(_process())


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


@cli.command()
def setup_playwright():
    """Install Playwright browsers."""
    import subprocess
    
    console.print("[blue]Setting up Playwright browsers...[/blue]")
    
    result = subprocess.run(
        [sys.executable, "setup_playwright.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        console.print("[green]✓[/green] Playwright setup complete")
    else:
        console.print("[red]✗[/red] Playwright setup failed")
        console.print(result.stderr)


def display_scraper_result(result: dict):
    """Display results from intelligent scraper."""
    if result["status"] == "success":
        console.print(f"\n[green]✓[/green] Intelligent scraper completed successfully")
        console.print(f"  Sources processed: {', '.join(result['sources_processed'])}")
        console.print(f"  Posts scraped: {result.get('posts_scraped', 0)}")
        console.print(f"  Practices extracted: {result.get('practices_extracted', 0)}")
        console.print(f"  Processing time: {result.get('processing_time', 0):.1f}s")
        
        if result.get('models_found'):
            console.print(f"\n  Models found ({len(result['models_found'])}):")
            for model in result['models_found'][:10]:  # Show first 10
                console.print(f"    - {model}")
            if len(result['models_found']) > 10:
                console.print(f"    ... and {len(result['models_found']) - 10} more")
    else:
        console.print(f"\n[red]✗[/red] Intelligent scraper failed")
        console.print(f"  Error: {result.get('error', 'Unknown error')}")


def display_single_result(source: str, result: dict):
    """Display results from a single scraper."""
    if result["status"] == "success":
        console.print(f"\n[green]✓[/green] {source} scraper completed successfully")
        console.print(f"  Posts scraped: {result.get('posts_scraped', 0)}")
        console.print(f"  Practices extracted: {result.get('practices_extracted', 0)}")
        
        if "practice_update" in result:
            update = result["practice_update"]
            console.print(f"  Models updated: {update['models_updated']}")
            console.print(f"  Practices added: {update['practices_added']}")
            console.print(f"  Duplicates skipped: {update['practices_skipped']}")
        
        if "save_stats" in result:
            stats = result["save_stats"]
            console.print(f"  Posts saved: {stats['saved']}")
            console.print(f"  Duplicates: {stats['duplicates']}")
    else:
        console.print(f"\n[red]✗[/red] {source} scraper failed")
        console.print(f"  Error: {result.get('error', 'Unknown error')}")


def display_all_results(results: dict):
    """Display results from all scrapers."""
    table = Table(title="Scraping Results")
    table.add_column("Source", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Posts", style="yellow")
    table.add_column("Practices", style="blue")
    
    for source, result in results.items():
        status = "[green]Success[/green]" if result["status"] == "success" else "[red]Failed[/red]"
        posts = result.get("posts_scraped", 0)
        practices = result.get("practices_extracted", 0)
        table.add_row(source, status, str(posts), str(practices))
    
    console.print(table)


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
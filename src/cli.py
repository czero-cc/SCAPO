"""CLI for SCAPO (Stay Calm and Prompt On)."""

import asyncio
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.logging import setup_logging, get_logger
from src.services.scraper_service import ScraperService
from src.core.config import settings

console = Console()

# Setup logging before CLI initialization
setup_logging()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """SCAPO CLI - Manage AI/ML best practices scraping and processing."""
    pass


@cli.command()
def init():
    """Initialize SCAPO environment."""
    console.print("[blue]Checking SCAPO setup...[/blue]")
    
    # Check if .env exists
    import os
    if not os.path.exists(".env"):
        console.print("[yellow]No .env file found. Creating from .env.example...[/yellow]")
        import shutil
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            console.print("[green]✓[/green] Created .env file")
            console.print("[yellow]→[/yellow] Please edit .env to configure your LLM provider")
        else:
            console.print("[red]✗[/red] .env.example not found")
            return
    
    # Check models directory
    if not os.path.exists("models"):
        os.makedirs("models")
        console.print("[green]✓[/green] Created models directory")
    
    console.print("[green]✓[/green] SCAPO is ready to use!")


@cli.group()
def scrape():
    """Run web scrapers."""
    pass


@scrape.command(name="run")
@click.option("--sources", "-s", multiple=True, 
              help="Sources to scrape (e.g., reddit:LocalLLaMA hackernews github:dair-ai/Prompt-Engineering-Guide)")
@click.option("--limit", "-l", default=10, help="Maximum posts per source")
@click.option("--llm-max-chars", "-c", type=int, help="Max characters for LLM processing")
def run_scraper(sources, limit, llm_max_chars):
    """Run intelligent scraper to collect AI/ML best practices.
    
    Examples:
        scapo scrape run -s reddit:LocalLLaMA -s hackernews
        scapo scrape run -s reddit:OpenAI -s reddit:StableDiffusion -l 5
        scapo scrape run  # Uses default sources
    
    Tip: Adjust SCRAPING_DELAY_SECONDS in .env to control scraping speed.
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


@scrape.command(name="status")
def scrape_status():
    """Show scraper status."""
    async def _status():
        scraper_service = ScraperService()
        
        # Get scraper status
        scraper_status = await scraper_service.get_status()
        
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
        
        # Check for recent results
        import os
        import json
        from datetime import datetime
        
        # Find recent pipeline results
        result_files = [f for f in os.listdir(".") if f.startswith("pipeline_test_results_") and f.endswith(".json")]
        if result_files:
            # Sort by modification time
            result_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = result_files[0]
            
            console.print(f"\n[bold]Latest Pipeline Results[/bold] ({latest_file})")
            with open(latest_file, 'r') as f:
                results = json.load(f)
                console.print(f"  Total posts scraped: {results.get('total_posts_scraped', 0)}")
                console.print(f"  Posts processed: {results.get('total_posts_processed', 0)}")
                console.print(f"  Practices extracted: {results.get('total_practices_extracted', 0)}")
                console.print(f"  Models found: {len(results.get('unique_models', []))}")
    
    asyncio.run(_status())


@cli.group()
def models():
    """Manage model best practices."""
    pass


@models.command(name="list")
@click.option("--category", "-c", help="Filter by category")
def list_models(category):
    """List all available models."""
    import os
    import json
    
    console.print("\n[bold]Available Models[/bold]")
    
    models_dir = "models"
    if not os.path.exists(models_dir):
        console.print("[yellow]No models directory found. Run 'sota scrape run' first.[/yellow]")
        return
    
    categories = ["text", "image", "video", "audio", "multimodal"] if not category else [category]
    
    for cat in categories:
        cat_dir = os.path.join(models_dir, cat)
        if os.path.exists(cat_dir):
            model_list = [d for d in os.listdir(cat_dir) if os.path.isdir(os.path.join(cat_dir, d))]
            if model_list:
                console.print(f"\n[cyan]{cat.upper()}[/cyan]")
                for model in sorted(model_list):
                    model_path = os.path.join(cat_dir, model)
                    # Count files
                    files = os.listdir(model_path)
                    prompts = len([f for f in files if f == "prompting.md"])
                    params = len([f for f in files if f == "parameters.json"])
                    tips = len([f for f in files if f == "tips.md"])
                    stats = f"({prompts} prompts, {params} params, {tips} tips)"
                    console.print(f"  • {model} {stats}")


@models.command(name="info")
@click.argument("model_id")
@click.option("--category", "-c", default="text", help="Model category")
def model_info(model_id, category):
    """Show detailed info for a specific model."""
    import os
    import json
    
    model_path = os.path.join("models", category, model_id)
    if not os.path.exists(model_path):
        console.print(f"[red]Model {model_id} not found in {category} category[/red]")
        return
    
    console.print(f"\n[bold]{model_id}[/bold]")
    console.print(f"Category: {category}")
    
    # Show files
    console.print("\n[bold]Available Content:[/bold]")
    files = os.listdir(model_path)
    for file in sorted(files):
        file_path = os.path.join(model_path, file)
        size = os.path.getsize(file_path)
        console.print(f"  • {file} ({size:,} bytes)")
    
    # Show sample content
    prompting_file = os.path.join(model_path, "prompting.md")
    if os.path.exists(prompting_file):
        console.print("\n[bold]Sample Prompting Content:[/bold]")
        with open(prompting_file, 'r', encoding='utf-8') as f:
            content = f.read()
            preview = content[:300] + "..." if len(content) > 300 else content
            console.print(preview)
    
    params_file = os.path.join(model_path, "parameters.json")
    if os.path.exists(params_file):
        console.print("\n[bold]Parameters:[/bold]")
        with open(params_file, 'r', encoding='utf-8') as f:
            params = json.load(f)
            if isinstance(params, list) and len(params) > 0:
                for param in params[:3]:  # Show first 3
                    if isinstance(param, dict):
                        desc = param.get('description', 'No description')
                        console.print(f"  • {desc[:100]}...")


@models.command(name="search")
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results")
def search_models(query, limit):
    """Search for models."""
    import os
    
    console.print(f"\n[bold]Searching for '{query}'...[/bold]")
    
    results = []
    models_dir = "models"
    if not os.path.exists(models_dir):
        console.print("[yellow]No models directory found. Run 'sota scrape run' first.[/yellow]")
        return
    
    # Search through all categories and models
    for category in ["text", "image", "video", "audio", "multimodal"]:
        cat_dir = os.path.join(models_dir, category)
        if os.path.exists(cat_dir):
            for model in os.listdir(cat_dir):
                if query.lower() in model.lower():
                    results.append({"model": model, "category": category})
                    if len(results) >= limit:
                        break
    
    if not results:
        console.print(f"[yellow]No models found for query: {query}[/yellow]")
        return
    
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Model", style="cyan")
    table.add_column("Category", style="green")
    
    for result in results:
        table.add_row(result["model"], result["category"])
    
    console.print(table)


@cli.command()
def schedule():
    """Run periodic scraping based on SCRAPING_INTERVAL_HOURS setting."""
    async def _schedule():
        service = ScraperService()
        
        console.print(f"[blue]Starting scheduled scraping (every {settings.scraping_interval_hours} hours)...[/blue]")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
        
        try:
            await service.schedule_periodic_scraping()
        except KeyboardInterrupt:
            console.print("\n[yellow]Scheduled scraping stopped[/yellow]")
    
    asyncio.run(_schedule())


@cli.command()
def sources():
    """List available scraping sources."""
    async def _sources():
        service = ScraperService()
        sources = await service.list_sources()
        
        console.print("\n[bold]Available Sources[/bold]")
        
        for category, source_list in sources.items():
            if source_list:
                console.print(f"\n[cyan]{category.upper()}[/cyan]")
                for source in source_list:
                    console.print(f"  • {source}")
        
        console.print("\n[yellow]Usage:[/yellow]")
        console.print("  scapo scrape run -s reddit:LocalLLaMA -s hackernews")
        console.print("  scapo scrape run --sources reddit:OpenAI --limit 5")
    
    asyncio.run(_sources())


@cli.command()
def clean():
    """Clean up temporary files and logs."""
    import os
    import glob
    
    console.print("[blue]Cleaning up temporary files...[/blue]")
    
    # Clean up result JSON files
    result_files = glob.glob("pipeline_test_results_*.json")
    for f in result_files:
        os.remove(f)
        console.print(f"  • Removed {f}")
    
    # Clean up log files
    log_files = glob.glob("intelligent_scraper_*.log") + glob.glob("intelligent_scraper_*.json")
    for f in log_files:
        os.remove(f)
        console.print(f"  • Removed {f}")
    
    # Clean up egg-info
    egg_info = glob.glob("src/*.egg-info")
    for d in egg_info:
        import shutil
        shutil.rmtree(d)
        console.print(f"  • Removed {d}")
    
    console.print("[green]✓[/green] Cleanup complete")


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
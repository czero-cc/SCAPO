#!/usr/bin/env python
"""System test script to verify SOTA Practices is working correctly."""

import asyncio
import httpx
from rich.console import Console
from rich.table import Table

from src.services.model_service import ModelService
from src.scrapers.github_scraper import GitHubScraper
from src.scrapers.source_manager import SourceManager

console = Console()


async def test_model_service():
    """Test model service functionality."""
    console.print("\n[bold blue]Testing Model Service[/bold blue]")
    
    service = ModelService()
    models = await service.list_models()
    
    table = Table(title="Available Models")
    table.add_column("Category", style="cyan")
    table.add_column("Models", style="green")
    
    for category, model_list in models.items():
        if model_list:
            table.add_row(category, ", ".join(model_list))
    
    console.print(table)
    
    # Test loading a specific model
    gpt4 = await service.get_model_practices("text", "gpt-4")
    if gpt4:
        console.print("\n[green]✓[/green] Successfully loaded GPT-4 practices")
        console.print(f"  - Parameters: {len(gpt4.parameters)}")
        console.print(f"  - Examples: {len(gpt4.prompt_examples)}")
    else:
        console.print("[red]✗[/red] Failed to load GPT-4")


async def test_scrapers():
    """Test scraper functionality."""
    console.print("\n[bold blue]Testing Scrapers[/bold blue]")
    
    # Test GitHub scraper
    scraper = GitHubScraper()
    try:
        posts = await scraper.fetch_posts(limit=2)
        console.print(f"\n[green]✓[/green] GitHub scraper: Fetched {len(posts)} posts")
        if posts:
            console.print(f"  - First post: {posts[0].title}")
            console.print(f"  - Relevance: {posts[0].relevance_score:.2f}")
    except Exception as e:
        console.print(f"[red]✗[/red] GitHub scraper error: {e}")
    finally:
        await scraper.close()


def test_source_manager():
    """Test source manager."""
    console.print("\n[bold blue]Testing Source Manager[/bold blue]")
    
    manager = SourceManager()
    summary = manager.get_all_sources_summary()
    
    table = Table(title="Configured Sources")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="yellow")
    
    for source_type, count in summary.items():
        if source_type != "total":
            table.add_row(source_type, str(count))
    
    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold]{summary['total']}[/bold]")
    
    console.print(table)


async def test_api_endpoints():
    """Test API endpoints."""
    console.print("\n[bold blue]Testing API Endpoints[/bold blue]")
    
    base_url = "http://localhost:8000"
    headers = {"X-API-Key": "test_api_key_123"}
    
    async with httpx.AsyncClient() as client:
        # Test root endpoint
        try:
            response = await client.get(base_url)
            if response.status_code == 200:
                console.print("[green]✓[/green] Root endpoint accessible")
            else:
                console.print(f"[red]✗[/red] Root endpoint returned {response.status_code}")
        except Exception as e:
            console.print(f"[yellow]![/yellow] API server not running: {e}")
            console.print("  Run 'make dev' to start the API server")
            return
        
        # Test health endpoint
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                console.print("[green]✓[/green] Health check passed")
        except:
            pass
        
        # Test models endpoint
        try:
            response = await client.get(f"{base_url}/api/v1/models/", headers=headers)
            if response.status_code == 200:
                console.print("[green]✓[/green] Models endpoint working")
            elif response.status_code == 403:
                console.print("[yellow]![/yellow] API requires authentication")
        except:
            pass


async def main():
    """Run all tests."""
    console.print("[bold green]SOTA Practices System Test[/bold green]")
    console.print("=" * 50)
    
    # Test components
    await test_model_service()
    test_source_manager()
    await test_scrapers()
    await test_api_endpoints()
    
    console.print("\n[bold green]System test complete![/bold green]")
    console.print("\nTo start using the system:")
    console.print("1. Start API server: [cyan]make dev[/cyan]")
    console.print("2. Run scrapers: [cyan]python -m src.scrapers.run all[/cyan]")
    console.print("3. Use CLI: [cyan]sota --help[/cyan]")


if __name__ == "__main__":
    asyncio.run(main())
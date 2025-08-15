"""CLI for SCAPO (Stay Calm and Prompt On)."""

import warnings
# Suppress pydantic V2 migration warnings from third-party libraries (specifically litellm)
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=".*Valid config keys have changed in V2.*",
    module="pydantic._internal._config"
)

import asyncio
import sys
import click
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.columns import Columns
from rich.syntax import Syntax
from rich.tree import Tree
from rich import box
import time
from typing import Optional

from src.core.logging import setup_logging, get_logger
from src.services.scraper_service import ScraperService
from src.core.config import settings

console = Console()

# Setup logging before CLI initialization
setup_logging()
logger = get_logger(__name__)

# ASCII Art Banner
SCAPO_BANNER = r"""
[bold cyan]
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      ███████╗ ██████╗ █████╗ ██████╗  ██████╗             ║
║      ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔═══██╗            ║
║      ███████╗██║     ███████║██████╔╝██║   ██║            ║
║      ╚════██║██║     ██╔══██║██╔═══╝ ██║   ██║            ║
║      ███████║╚██████╗██║  ██║██║     ╚██████╔╝            ║
║      ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝      ╚═════╝             ║
║                                                           ║
║                  [bold white]Stay Calm and Prompt On[/bold white]                  ║
║          [dim]AI Model Best Practices Knowledge Base[/dim]           ║
╚═══════════════════════════════════════════════════════════╝
[/bold cyan]
"""

def show_banner():
    """Display the SCAPO banner."""
    console.print(SCAPO_BANNER)
    console.print()

def create_status_panel(title: str, content: str, style: str = "cyan"):
    """Create a styled panel for status displays."""
    return Panel(
        content,
        title=f"[bold {style}]{title}[/bold {style}]",
        border_style=style,
        box=box.ROUNDED,
        padding=(1, 2)
    )

def format_source_identifier(source: str) -> str:
    """Format source identifier with icon."""
    icons = {
        "reddit": "🔴",
        # "hackernews": "🔶",  # Not yet implemented
        "github": "🐙",
        "discourse": "💬",
        "huggingface": "🤗",
    }
    
    for key, icon in icons.items():
        if key in source.lower():
            return f"{icon} {source}"
    return f"📌 {source}"


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """SCAPO CLI - Community-driven AI/ML Best Practices."""
    if ctx.invoked_subcommand is None:
        show_banner()
        console.print("[yellow]Tip:[/yellow] Use 'scapo --help' to see available commands\n")


@cli.command()
def init():
    """Initialize SCAPO environment with interactive setup."""
    show_banner()
    
    # Initialize environment without fake delay
    
    # Check if .env exists
    import os
    env_exists = os.path.exists(".env")
    
    if not env_exists:
        console.print(Panel(
            "[yellow]⚠  No configuration file found[/yellow]\n\n"
            "Let's set up your environment!",
            title="[bold]First Time Setup[/bold]",
            border_style="yellow"
        ))
        
        import shutil
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            console.print("\n[green]✓[/green] Created configuration file from template")
            
            # Interactive LLM setup
            console.print("\n[bold]Configure Your LLM Provider[/bold]")
            console.print("SCAPO uses LLMs to analyze scraped content\n")
            
            providers = ["OpenAI", "Anthropic", "Local (Ollama)", "OpenRouter", "Skip for now"]
            for i, provider in enumerate(providers, 1):
                console.print(f"  [{i}] {provider}")
            
            choice = Prompt.ask("\nSelect your provider", choices=["1", "2", "3", "4", "5"], default="5")
            
            if choice != "5":
                provider_names = {
                    "1": "OpenAI",
                    "2": "Anthropic",
                    "3": "Ollama",
                    "4": "OpenRouter"
                }
                console.print(f"\n[cyan]Selected: {provider_names[choice]}[/cyan]")
                console.print("[dim]Edit .env file to add your API keys[/dim]")
        else:
            console.print("[red]✗[/red] Configuration template not found")
            return
    
    # Check models directory
    if not os.path.exists("models"):
        os.makedirs("models")
        console.print("[green]✓[/green] Created models directory")
    
    # Success panel
    console.print("\n")
    console.print(Panel(
        "[green]✓[/green] SCAPO is ready!\n\n"
        "[bold]Next steps:[/bold]\n"
        "1. Edit [cyan].env[/cyan] to configure your LLM provider\n"
        "2. Run [cyan]scapo scrape run[/cyan] to collect best practices\n"
        "3. Use [cyan]scapo models list[/cyan] to browse available models",
        title="[bold green]Setup Complete[/bold green]",
        border_style="green"
    ))


@cli.group()
def scrape():
    """Run web scrapers."""
    pass


@scrape.command(name="run")
@click.option("--sources", "-s", multiple=True, 
              help="Sources to scrape (e.g., reddit:LocalLLaMA)")
@click.option("--limit", "-l", default=10, help="Maximum posts per source")
@click.option("--interactive", "-i", is_flag=True, help="Interactive source selection")
def run_scraper(sources, limit, interactive):
    """Run intelligent scraper with enhanced UI."""
    show_banner()
    
    async def _run():
        service = ScraperService()
        
        # Interactive mode
        if interactive and not sources:
            available_sources = await service.list_sources()
            
            console.print(Panel(
                "Select sources to scrape:",
                title="[bold]Interactive Mode[/bold]",
                border_style="cyan"
            ))
            
            all_sources = []
            for category, source_list in available_sources.items():
                for source in source_list:
                    all_sources.append(source)
            
            selected = []
            for i, source in enumerate(all_sources, 1):
                console.print(f"  [{i}] {format_source_identifier(source)}")
            
            console.print(f"\n  [0] All sources")
            console.print(f"  [Enter] Use defaults")
            
            choices = Prompt.ask("\nSelect sources (comma-separated)", default="")
            
            if choices:
                if "0" in choices:
                    sources_list = None  # Use all
                else:
                    indices = [int(x.strip()) - 1 for x in choices.split(",") if x.strip().isdigit()]
                    sources_list = [all_sources[i] for i in indices if 0 <= i < len(all_sources)]
            else:
                sources_list = None
        else:
            sources_list = list(sources) if sources else None
        
        # Display scraping plan
        if sources_list:
            source_text = "\n".join([f"  • {format_source_identifier(s)}" for s in sources_list])
        else:
            source_text = "  • All configured sources"
        
        console.print(Panel(
            f"[bold]Scraping Plan[/bold]\n\n"
            f"Sources:\n{source_text}\n\n"
            f"Post limit: [cyan]{limit}[/cyan] per source",
            border_style="blue"
        ))
        
        if not Confirm.ask("\nProceed with scraping?", default=True):
            console.print("[yellow]Scraping cancelled[/yellow]")
            return
        
        # Run scraper with real progress tracking
        num_sources = len(sources_list) if sources_list else 5  # Default has 5 sources
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Track total posts expected across all sources
            total_posts_expected = num_sources * limit
            task = progress.add_task(
                f"Processing {num_sources} source{'s' if num_sources > 1 else ''} (up to {total_posts_expected} posts)...", 
                total=total_posts_expected
            )
            
            # Process sources one by one for real progress
            all_results = {
                "status": "success",
                "posts_scraped": 0,
                "models_found": set(),
                "best_practices": 0,
                "practices_extracted": 0,
                "processing_time": 0,
                "sources_processed": []
            }
            
            start_time = datetime.utcnow()
            
            if sources_list:
                total_posts_processed = 0
                
                # Create progress callback
                async def report_progress(source_name, posts_done, total_posts):
                    nonlocal total_posts_processed
                    current_progress = total_posts_processed + posts_done
                    progress.update(task, completed=current_progress, 
                                  description=f"Processing {format_source_identifier(f'reddit:{source_name}')} [{posts_done}/{total_posts} posts]...")
                
                for idx, source in enumerate(sources_list):
                    progress.update(task, description=f"Starting {format_source_identifier(source)}...")
                    
                    # Run scraper for single source with progress callback
                    result = await service.run_scrapers(
                        sources=[source],
                        max_posts_per_source=limit,
                        progress_callback=report_progress
                    )
                    
                    # Aggregate results
                    posts_found = result.get("posts_scraped", 0)
                    all_results["posts_scraped"] += posts_found
                    all_results["models_found"].update(result.get("models_found", []))
                    all_results["best_practices"] += result.get("best_practices", 0)
                    all_results["practices_extracted"] += result.get("best_practices", 0)  # Same as best_practices
                    all_results["sources_processed"].append(source)
                    
                    # Update total posts processed
                    total_posts_processed += min(posts_found, limit)
            else:
                # Use default sources
                result = await service.run_scrapers(
                    sources=None,
                    max_posts_per_source=limit,
                )
                # Ensure result has all required fields
                all_results = result
                if "status" not in all_results:
                    all_results["status"] = "success"
                if "practices_extracted" not in all_results:
                    all_results["practices_extracted"] = all_results.get("best_practices", 0)
                progress.update(task, completed=total_posts_expected)
            
            end_time = datetime.utcnow()
            all_results["processing_time"] = (end_time - start_time).total_seconds()
            
            # Convert set to list for display
            if isinstance(all_results.get("models_found"), set):
                all_results["models_found"] = list(all_results["models_found"])
            
        display_scraper_result_enhanced(all_results)
    
    asyncio.run(_run())


@scrape.command(name="discover")
@click.option("--update", is_flag=True, help="Update service list from sources")
@click.option("--show-all", is_flag=True, help="Show all discovered services")
def discover_services(update, show_all):
    """Discover AI services from GitHub Awesome lists and other sources."""
    show_banner()
    
    async def _discover():
        from src.scrapers.service_discovery import ServiceDiscoveryPipeline, GitHubAwesomeListSource
        from pathlib import Path
        import json
        
        if update:
            with console.status("[bold blue]Discovering AI services from sources...[/bold blue]", spinner="dots"):
                pipeline = ServiceDiscoveryPipeline()
                pipeline.add_source(GitHubAwesomeListSource())
                registry = await pipeline.run()
                
            console.print(f"[green]✓[/green] Discovered [cyan]{len(registry.get_all_services())}[/cyan] AI services")
        
        # Load and display services
        services_path = Path("data/cache/services.json")
        if services_path.exists():
            with open(services_path) as f:
                data = json.load(f)
                services = data.get('services', {})
            
            # Group by category
            by_category = {}
            for service in services.values():
                cat = service['category']
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(service['display_name'])
            
            # Display summary
            table = Table(title="Discovered AI Services", box=box.ROUNDED)
            table.add_column("Category", style="cyan")
            table.add_column("Count", style="green")
            table.add_column("Examples", style="yellow")
            
            for cat in sorted(by_category.keys()):
                services_list = by_category[cat]
                examples = ", ".join(services_list[:3])
                if len(services_list) > 3:
                    examples += f" ... (+{len(services_list)-3})"
                table.add_row(cat, str(len(services_list)), examples)
            
            console.print(table)
            
            if show_all:
                console.print("\n[bold]All Services:[/bold]")
                for cat in sorted(by_category.keys()):
                    console.print(f"\n[cyan]{cat.upper()}:[/cyan]")
                    for service in sorted(by_category[cat]):
                        console.print(f"  • {service}")
        else:
            console.print("[yellow]No services discovered yet. Run with --update flag.[/yellow]")
    
    asyncio.run(_discover())


@scrape.command(name="targeted")
@click.option("--service", "-s", help="Target specific service")
@click.option("--category", "-c", help="Target services by category (video, audio, etc)")
@click.option("--limit", "-l", default=20, help="Max posts per search")
@click.option("--batch-size", "-b", default=50, help="Posts per LLM batch")
@click.option("--dry-run", is_flag=True, help="Show queries without running")
@click.option("--all", "run_all", is_flag=True, help="Run all generated queries")
@click.option("--max-queries", "-m", default=10, help="Maximum queries to run (default: 10)")
@click.option("--parallel", "-p", default=3, help="Number of parallel scraping tasks")
def targeted_scrape(service, category, limit, batch_size, dry_run, run_all, max_queries, parallel):
    """Run targeted searches for specific AI services."""
    show_banner()
    
    async def _targeted():
        from src.scrapers.targeted_search_generator import TargetedSearchGenerator
        from src.scrapers.intelligent_browser_scraper import IntelligentBrowserScraper
        from src.services.batch_llm_processor import BatchLLMProcessor
        from src.services.llm_processor import LLMProcessorFactory
        from pathlib import Path
        import json
        import asyncio
        from datetime import datetime
        
        # Access outer scope variables
        nonlocal service, category, limit, batch_size, dry_run, run_all, max_queries, parallel
        
        # Generate targeted searches
        generator = TargetedSearchGenerator()
        
        # If a specific service is requested, generate queries directly for it
        if service and not category:
            # Just generate queries for the requested service - don't generate for all services first
            console.print(f"[cyan]Generating queries for {service}...[/cyan]")
            queries = generator.generate_queries_for_service(service, max_queries=max_queries)
            
            if not queries:
                console.print(f"[red]Could not generate queries for service: {service}[/red]")
                return
        else:
            # Generate queries based on category or all services
            all_queries = generator.generate_queries(
                max_queries=100 if run_all else max_queries,
                category_filter=category if category else None
            )
            queries = all_queries
        
        if not queries:
            console.print("[yellow]No matching queries found[/yellow]")
            return
        
        # Limit queries if not running all
        if not run_all and len(queries) > max_queries:
            queries = queries[:max_queries]
        
        console.print(f"[cyan]Generated {len(queries)} targeted searches[/cyan]")
        
        if dry_run:
            # Show queries without running
            table = Table(title="Targeted Search Queries", box=box.ROUNDED)
            table.add_column("#", style="dim")
            table.add_column("Service", style="cyan")
            table.add_column("Pattern", style="green")
            table.add_column("Priority", style="yellow")
            
            for i, q in enumerate(queries[:30], 1):  # Show first 30
                table.add_row(str(i), q['service'], q['pattern_type'], q['priority'])
            
            console.print(table)
            if len(queries) > 30:
                console.print(f"[dim]... and {len(queries)-30} more queries[/dim]")
            return
        
        # Confirm before running many queries
        if len(queries) > 20:
            from rich.prompt import Confirm as RichConfirm
            if not RichConfirm.ask(f"\n[yellow]Run {len(queries)} search queries?[/yellow]", default=False):
                console.print("[red]Cancelled[/red]")
                return
        
        # Parallel scraping function
        async def process_query(query, scraper, batch_processor, llm, semaphore):
            async with semaphore:
                try:
                    posts = await scraper.scrape(query['query_url'], max_posts=limit)
                    
                    if posts:
                        # Batch process with LLM
                        batches = batch_processor.batch_posts_by_tokens(posts, query['service'])
                        
                        results = []
                        for batch in batches:
                            result = await batch_processor.process_batch(batch, query['service'], llm)
                            results.append(result)
                        
                        return {
                            'query': query,
                            'posts_found': len(posts),
                            'results': results
                        }
                    else:
                        return {
                            'query': query,
                            'posts_found': 0,
                            'results': []
                        }
                except Exception as e:
                    logger.error(f"Failed to process {query['service']}: {e}")
                    return {
                        'query': query,
                        'error': str(e),
                        'results': []
                    }
        
        # Initialize processors
        scraper = IntelligentBrowserScraper()
        batch_processor = BatchLLMProcessor(settings.openrouter_model if settings.llm_provider == "openrouter" else "gpt-3.5-turbo")
        llm = LLMProcessorFactory.create_processor()
        
        # Semaphore for parallel control
        semaphore = asyncio.Semaphore(parallel)
        
        # Run with progress tracking
        all_results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Running {len(queries)} targeted searches...", total=len(queries))
            
            # Process in batches for better progress tracking
            batch_size = parallel * 2
            for i in range(0, len(queries), batch_size):
                batch_queries = queries[i:i+batch_size]
                
                # Run batch of queries in parallel
                tasks = [
                    process_query(q, scraper, batch_processor, llm, semaphore)
                    for q in batch_queries
                ]
                
                batch_results = await asyncio.gather(*tasks)
                all_results.extend(batch_results)
                
                # Update progress
                progress.update(task, advance=len(batch_queries))
                
                # Update description with current service
                if batch_results:
                    current_service = batch_results[-1]['query']['service']
                    progress.update(task, description=f"Processing: {current_service}")
        
        # Aggregate results
        successful_queries = [r for r in all_results if r.get('posts_found', 0) > 0]
        failed_queries = [r for r in all_results if 'error' in r]
        
        # Flatten all LLM results
        all_llm_results = []
        for r in all_results:
            all_llm_results.extend(r.get('results', []))
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f"data/intermediate/targeted_results_{timestamp}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'queries_run': len(queries),
                'successful_queries': len(successful_queries),
                'failed_queries': len(failed_queries),
                'total_posts_scraped': sum(r.get('posts_found', 0) for r in all_results),
                'results': all_llm_results,
                'query_details': all_results
            }, f, indent=2)
        
        # Calculate statistics
        total_problems = sum(len(r.get('problems', [])) for r in all_llm_results)
        total_tips = sum(len(r.get('tips', [])) for r in all_llm_results)
        total_cost_info = sum(len(r.get('cost_info', [])) for r in all_llm_results)
        total_posts = sum(r.get('posts_found', 0) for r in all_results)
        
        # Display detailed summary
        console.print("\n")
        console.print(Panel(
            f"[bold green]🎯 Targeted Scraping Complete![/bold green]\n\n"
            f"[bold]Query Statistics:[/bold]\n"
            f"  Total queries: [cyan]{len(queries)}[/cyan]\n"
            f"  Successful: [green]{len(successful_queries)}[/green]\n"
            f"  Failed: [red]{len(failed_queries)}[/red]\n\n"
            f"[bold]Content Found:[/bold]\n"
            f"  Posts scraped: [cyan]{total_posts}[/cyan]\n"
            f"  Problems identified: [cyan]{total_problems}[/cyan]\n"
            f"  Tips found: [cyan]{total_tips}[/cyan]\n"
            f"  Cost info extracted: [cyan]{total_cost_info}[/cyan]\n\n"
            f"[bold]Output:[/bold]\n"
            f"  Results saved to: [yellow]{output_file}[/yellow]",
            border_style="green",
            title="Results Summary"
        ))
        
        # Generate model entries
        from src.services.model_entry_generator import ModelEntryGenerator
        generator = ModelEntryGenerator()
        entries_created = generator.process_extraction_results(output_file)
        
        if entries_created > 0:
            console.print(f"\n[green]✓[/green] Generated [cyan]{entries_created}[/cyan] model entries in the models/ folder")
        else:
            console.print("\n[yellow]No model entries generated (insufficient data)[/yellow]")
        
        # Show top services with findings
        if successful_queries:
            console.print("\n[bold]Top Services with Findings:[/bold]")
            service_stats = {}
            for r in successful_queries:
                service = r['query']['service']
                if service not in service_stats:
                    service_stats[service] = 0
                service_stats[service] += r.get('posts_found', 0)
            
            top_services = sorted(service_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            for service, count in top_services:
                console.print(f"  • {service}: [cyan]{count}[/cyan] posts")
        
        await scraper.close()
        await llm.close()
    
    asyncio.run(_targeted())


@scrape.command(name="batch")
@click.option("--category", "-c", help="Target services by category (video, audio, etc)")
@click.option("--limit", "-l", default=15, help="Max posts per search (default: 15)")
@click.option("--max-services", "-m", default=3, help="Maximum number of services to process (default: 3)")
@click.option("--priority", "-p", type=click.Choice(['ultra', 'critical', 'high', 'all']), default='ultra', help="Service priority level")
def batch_scrape(category, limit, max_services, priority):
    """Batch process multiple high-priority services."""
    show_banner()
    
    async def _batch():
        from src.scrapers.targeted_search_generator import TargetedSearchGenerator
        from src.scrapers.intelligent_browser_scraper import IntelligentBrowserScraper
        from src.services.batch_llm_processor import BatchLLMProcessor
        from src.services.llm_processor import LLMProcessorFactory
        from src.services.model_entry_generator import ModelEntryGenerator
        from src.services.service_alias_manager import ServiceAliasManager
        from pathlib import Path
        import json
        import asyncio
        from datetime import datetime
        
        # Initialize components
        generator = TargetedSearchGenerator()
        alias_manager = ServiceAliasManager()
        
        # Generate queries for multiple services
        all_queries = generator.generate_queries(
            max_queries=max_services * 5,  # 5 query types per service
            category_filter=category
        )
        
        # Filter by priority if specified
        if priority != 'all':
            all_queries = [q for q in all_queries if q.get('priority') == priority]
        
        # Group queries by service
        queries_by_service = {}
        for query in all_queries:
            service = query['service']
            if service not in queries_by_service:
                queries_by_service[service] = []
            queries_by_service[service].append(query)
        
        # Limit to max_services
        services_to_process = list(queries_by_service.keys())[:max_services]
        
        console.print(f"[cyan]Processing {len(services_to_process)} services:[/cyan]")
        for service in services_to_process:
            console.print(f"  • {service} ({len(queries_by_service[service])} queries)")
        
        if not Confirm.ask(f"\n[yellow]Process {len(services_to_process)} services?[/yellow]", default=True):
            console.print("[red]Cancelled[/red]")
            return
        
        # Initialize processors
        scraper = IntelligentBrowserScraper()
        batch_processor = BatchLLMProcessor(settings.openrouter_model if settings.llm_provider == "openrouter" else "gpt-3.5-turbo")
        llm = LLMProcessorFactory.create_processor()
        
        all_results = []
        
        # Process each service
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            total_queries = sum(len(queries_by_service[s]) for s in services_to_process)
            task = progress.add_task(f"Processing {len(services_to_process)} services...", total=total_queries)
            
            for service in services_to_process:
                service_queries = queries_by_service[service]
                progress.update(task, description=f"Processing {service}...")
                
                for query in service_queries:
                    try:
                        posts = await scraper.scrape(query['query_url'], max_posts=limit)
                        
                        if posts:
                            # Batch process with LLM
                            batches = batch_processor.batch_posts_by_tokens(posts, service)
                            
                            for batch in batches:
                                result = await batch_processor.process_batch(batch, service, llm)
                                all_results.append(result)
                        
                        progress.update(task, advance=1)
                        await asyncio.sleep(1)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"Failed to process {service}: {e}")
                        progress.update(task, advance=1)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f"data/intermediate/batch_results_{timestamp}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'services_processed': services_to_process,
                'total_queries': sum(len(queries_by_service[s]) for s in services_to_process),
                'results': all_results
            }, f, indent=2)
        
        # Generate model entries
        generator = ModelEntryGenerator()
        entries_created = generator.process_extraction_results(output_file)
        
        # Display summary
        console.print("\n")
        console.print(Panel(
            f"[bold green]🎯 Batch Processing Complete![/bold green]\n\n"
            f"[bold]Services Processed:[/bold] [cyan]{len(services_to_process)}[/cyan]\n"
            f"[bold]Total Queries:[/bold] [cyan]{sum(len(queries_by_service[s]) for s in services_to_process)}[/cyan]\n"
            f"[bold]Model Entries Created:[/bold] [cyan]{entries_created}[/cyan]\n\n"
            f"[bold]Results saved to:[/bold] [yellow]{output_file}[/yellow]",
            border_style="green",
            title="Batch Results"
        ))
        
        await scraper.close()
        await llm.close()
    
    asyncio.run(_batch())


@scrape.command(name="all")
@click.option('-l', '--limit', default=20, help='Max posts per search (default: 20)')
@click.option('-c', '--category', help='Filter by category (video, audio, code, etc)')
@click.option('-p', '--priority', 
              type=click.Choice(['ultra', 'critical', 'high', 'all']),
              default='ultra',
              help='Service priority level')
@click.option('--dry-run', is_flag=True, help='Show what would be processed without running')
@click.option('--delay', default=5, help='Delay in seconds between services (default: 5)')
def scrape_all(limit: int, category: str, priority: str, dry_run: bool, delay: int):
    """Process all priority services one by one."""
    show_banner()
    
    from src.scrapers.targeted_search_generator import TargetedSearchGenerator
    from src.scrapers.intelligent_browser_scraper import IntelligentBrowserScraper
    from src.services.batch_llm_processor import BatchLLMProcessor
    from src.services.llm_processor import LLMProcessorFactory
    from src.services.model_entry_generator import ModelEntryGenerator
    from src.services.service_alias_manager import ServiceAliasManager
    import asyncio
    import time
    from pathlib import Path
    import json
    
    # Initialize components
    generator = TargetedSearchGenerator()
    alias_manager = ServiceAliasManager()
    
    # Get all priority services
    priority_services = list(generator.priority_services)
    
    # Filter discovered services that match priority services
    filtered_services = {}
    for service_key, service_data in generator.services.items():
        display_name = service_data['display_name'].lower()
        if any(priority in display_name for priority in priority_services):
            # Apply category filter if specified
            if category and service_data['category'] != category:
                continue
            # Mark with ultra priority for our priority services
            service_data['priority'] = 'ultra'
            filtered_services[service_key] = service_data
    
    # Apply priority filter
    if priority != 'all':
        filtered_services = {k: v for k, v in filtered_services.items() 
                            if v.get('priority') == priority}
    
    services_to_process = list(filtered_services.values())
    
    console.print(f"[cyan]Found {len(services_to_process)} services to process[/cyan]")
    
    if dry_run:
        console.print("\n[yellow]DRY RUN - Services that would be processed:[/yellow]")
        for i, service in enumerate(services_to_process, 1):
            console.print(f"  {i}. {service['display_name']} ({service['category']})")
        console.print(f"\n[dim]Total: {len(services_to_process)} services × 5 queries × {limit} posts = {len(services_to_process) * 5 * limit} posts[/dim]")
        return
    
    if not Confirm.ask(f"\n[yellow]Process {len(services_to_process)} services individually?[/yellow]", default=True):
        console.print("[red]Cancelled[/red]")
        return
    
    # Process each service one by one
    successful = 0
    failed = 0
    
    for i, service_data in enumerate(services_to_process, 1):
        service_name = service_data['display_name']
        
        console.print(f"\n[cyan][{i}/{len(services_to_process)}] Processing {service_name}...[/cyan]")
        
        try:
            # Run targeted scraper for this service
            from subprocess import run, PIPE
            result = run(
                ['uv', 'run', 'scapo', 'scrape', 'targeted', 
                 '--service', service_name, 
                 '--limit', str(limit),
                 '--max-queries', '5'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                successful += 1
                console.print(f"  ✅ {service_name} completed")
            else:
                failed += 1
                console.print(f"  ❌ {service_name} failed: {result.stderr[:100]}")
        
        except Exception as e:
            failed += 1
            console.print(f"  ❌ {service_name} error: {str(e)[:100]}")
        
        # Delay between services (except for the last one)
        if i < len(services_to_process):
            console.print(f"  [dim]Waiting {delay} seconds before next service...[/dim]")
            time.sleep(delay)
    
    # Summary
    console.print(f"\n[green]✨ Processing complete![/green]")
    console.print(f"  Successful: {successful}")
    console.print(f"  Failed: {failed}")
    console.print(f"  Total: {len(services_to_process)}")


@scrape.command(name="status")
def scrape_status():
    """Show detailed scraper status with visual elements."""
    show_banner()
    
    async def _status():
        scraper_service = ScraperService()
        
        with console.status("[bold blue]Fetching scraper status...[/bold blue]", spinner="dots"):
            scraper_status = await scraper_service.get_status()
        
        # Create status cards
        cards = []
        for source, info in scraper_status["scrapers"].items():
            status_icon = "🟢" if info["status"] == "active" else "🔴"
            last_run = str(info["last_run"])[:16] if info["last_run"] else "Never"
            
            card_content = f"{status_icon} [bold]{source}[/bold]\n"
            card_content += f"Posts: [cyan]{info['total_posts']}[/cyan]\n"
            card_content += f"Last: [dim]{last_run}[/dim]"
            
            cards.append(Panel(
                card_content,
                width=20,
                height=6,
                border_style="green" if info["status"] == "active" else "red"
            ))
        
        # Display in columns
        console.print("\n[bold]Scraper Status Dashboard[/bold]\n")
        if cards:
            console.print(Columns(cards[:4]))
            if len(cards) > 4:
                console.print(Columns(cards[4:8]))
        
        # Recent results summary
        import os
        import json
        from datetime import datetime
        
        result_files = [f for f in os.listdir(".") if f.startswith("pipeline_test_results_") and f.endswith(".json")]
        if result_files:
            result_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = result_files[0]
            
            with open(latest_file, 'r') as f:
                results = json.load(f)
            
            # Create summary panel
            summary = f"""
[bold]Latest Pipeline Results[/bold]
            
📊 Posts scraped: [cyan]{results.get('total_posts_scraped', 0)}[/cyan]
🔄 Posts processed: [cyan]{results.get('total_posts_processed', 0)}[/cyan]
✨ Practices extracted: [cyan]{results.get('total_practices_extracted', 0)}[/cyan]
🤖 Models discovered: [cyan]{len(results.get('unique_models', []))}[/cyan]

[dim]From: {latest_file}[/dim]
"""
            console.print(Panel(
                summary.strip(),
                title="[bold]Performance Metrics[/bold]",
                border_style="blue",
                width=50
            ))
    
    asyncio.run(_status())


@cli.group()
def models():
    """Manage model best practices."""
    pass


@models.command(name="list")
@click.option("--category", "-c", help="Filter by category")
@click.option("--tree", "-t", is_flag=True, help="Display as tree")
@click.option("--cards", is_flag=True, help="Display as card view (limited to 8 per category)")
def list_models(category, tree, cards):
    """List models with enhanced display."""
    import os
    import json
    
    show_banner()
    
    models_dir = "models"
    if not os.path.exists(models_dir):
        console.print(Panel(
            "[yellow]No models found![/yellow]\n\n"
            "Run [cyan]scapo scrape run[/cyan] to collect best practices",
            border_style="yellow"
        ))
        return
    
    # Get all existing categories from the models directory
    all_categories = []
    if os.path.exists(models_dir):
        all_categories = [d for d in os.listdir(models_dir) 
                         if os.path.isdir(os.path.join(models_dir, d))]
    
    # Use specified category or all found categories
    categories = all_categories if not category else [category]
    
    if tree:
        # Tree view
        tree_view = Tree("[bold]📚 SCAPO Model Library[/bold]")
        
        for cat in categories:
            cat_dir = os.path.join(models_dir, cat)
            if os.path.exists(cat_dir):
                cat_node = tree_view.add(f"[cyan]{cat}[/cyan]")
                
                model_list = [d for d in os.listdir(cat_dir) if os.path.isdir(os.path.join(cat_dir, d))]
                for model in sorted(model_list):
                    model_path = os.path.join(cat_dir, model)
                    files = os.listdir(model_path)
                    file_count = len([f for f in files if f.endswith(('.md', '.json'))])
                    
                    model_node = cat_node.add(f"[green]{model}[/green] [dim]({file_count} files)[/dim]")
        
        console.print(tree_view)
    elif cards:
        # Card view (original behavior)
        total_models = 0
        for cat in categories:
            cat_dir = os.path.join(models_dir, cat)
            if os.path.exists(cat_dir):
                model_list = [d for d in os.listdir(cat_dir) if os.path.isdir(os.path.join(cat_dir, d))]
                if model_list:
                    total_models += len(model_list)
                    
                    # Category header with emoji mapping
                    emoji_map = {
                        'text': '🔤',
                        'image': '🎨',
                        'video': '🎬',
                        'audio': '🔊',
                        'multimodal': '🌐',
                        'code': '💻'
                    }
                    emoji = emoji_map.get(cat, '📁')  # Default emoji for unknown categories
                    console.print(f"\n[bold cyan]{emoji} {cat.upper()}[/bold cyan]")
                    
                    # Model cards
                    cards_list = []
                    for model in sorted(model_list)[:8]:  # Show max 8 per category
                        model_path = os.path.join(cat_dir, model)
                        files = os.listdir(model_path)
                        
                        card_text = f"[bold]{model}[/bold]\n"
                        if "prompting.md" in files:
                            card_text += "📝 "
                        if "parameters.json" in files:
                            card_text += "⚙️ "
                        if "tips.md" in files:
                            card_text += "💡"
                        
                        cards_list.append(card_text)
                    
                    # Display in columns
                    if len(cards_list) > 4:
                        console.print(Columns(cards_list[:4], padding=(0, 2)))
                        console.print(Columns(cards_list[4:], padding=(0, 2)))
                    else:
                        console.print(Columns(cards_list, padding=(0, 2)))
                    
                    if len(model_list) > 8:
                        console.print(f"[dim]... and {len(model_list) - 8} more[/dim]")
        
        # Summary
        console.print(f"\n[bold]Total models: [cyan]{total_models}[/cyan][/bold]")
    else:
        # Simple list view - one model per line (default behavior)
        total_models = 0
        for cat in categories:
            cat_dir = os.path.join(models_dir, cat)
            if os.path.exists(cat_dir):
                model_list = [d for d in os.listdir(cat_dir) if os.path.isdir(os.path.join(cat_dir, d))]
                if model_list:
                    total_models += len(model_list)
                    
                    # Category header with emoji mapping
                    emoji_map = {
                        'text': '🔤',
                        'image': '🎨',
                        'video': '🎬',
                        'audio': '🔊',
                        'multimodal': '🌐',
                        'code': '💻'
                    }
                    emoji = emoji_map.get(cat, '📁')  # Default emoji for unknown categories
                    console.print(f"\n[bold cyan]{emoji} {cat.upper()}[/bold cyan]")
                    
                    # List all models one per line
                    for model in sorted(model_list):
                        model_path = os.path.join(cat_dir, model)
                        files = os.listdir(model_path)
                        
                        # Build indicators string
                        indicators = []
                        if "prompting.md" in files:
                            indicators.append("📝")
                        if "parameters.json" in files:
                            indicators.append("⚙️")
                        if "tips.md" in files:
                            indicators.append("💡")
                        if "pitfalls.md" in files:
                            indicators.append("⚠️")
                        
                        indicators_str = " ".join(indicators) if indicators else ""
                        console.print(f"  • [bold]{model}[/bold] {indicators_str}")
        
        # Summary
        console.print(f"\n[bold]Total models: [cyan]{total_models}[/cyan][/bold]")


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
    
    # Search through all categories and models dynamically
    categories = [d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))]
    for category in categories:
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
def tui():
    """Launch interactive TUI for exploring model content."""
    try:
        from .tui import run_tui
        run_tui()
    except ImportError as e:
        console.print(f"[red]Error: Could not import TUI module: {e}[/red]")
        console.print("[yellow]Make sure textual is installed: uv pip install textual[/yellow]")
    except Exception as e:
        console.print(f"[red]Error launching TUI: {e}[/red]")


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
        console.print("  scapo scrape run -s reddit:LocalLLaMA -s reddit:OpenAI")
        console.print("  scapo scrape run --sources reddit:OpenAI --limit 5")
    
    asyncio.run(_sources())


@cli.command()
def clean():
    """Clean temporary files with confirmation."""
    show_banner()
    
    import os
    import glob
    
    # Find files to clean
    files_to_clean = []
    files_to_clean.extend(glob.glob("pipeline_test_results_*.json"))
    files_to_clean.extend(glob.glob("intelligent_scraper_*.log"))
    files_to_clean.extend(glob.glob("intelligent_scraper_*.json"))
    files_to_clean.extend(glob.glob("src/*.egg-info"))
    
    if not files_to_clean:
        console.print(Panel(
            "[green]✓[/green] No temporary files to clean",
            border_style="green"
        ))
        return
    
    # Show files to be cleaned
    console.print(Panel(
        f"[bold]Files to be removed:[/bold]\n\n" +
        "\n".join([f"  • {f}" for f in files_to_clean]),
        title="[bold]Cleanup Preview[/bold]",
        border_style="yellow"
    ))
    
    if Confirm.ask("\nProceed with cleanup?", default=True):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Cleaning files...", total=len(files_to_clean))
            
            for f in files_to_clean:
                if os.path.isdir(f):
                    import shutil
                    shutil.rmtree(f)
                else:
                    os.remove(f)
                progress.update(task, advance=1)
        
        console.print("\n[green]✓[/green] Cleanup complete!")
    else:
        console.print("[yellow]Cleanup cancelled[/yellow]")


@cli.command()
def setup_playwright():
    """Setup Playwright with enhanced UI."""
    show_banner()
    
    import subprocess
    
    console.print(Panel(
        "[bold]Playwright Setup[/bold]\n\n"
        "This will install browser engines for:\n"
        "  • Chromium\n"
        "  • Firefox\n"
        "  • WebKit\n\n"
        "Required for scraping JavaScript-heavy sites",
        border_style="blue"
    ))
    
    if not Confirm.ask("\nProceed with installation?", default=True):
        console.print("[yellow]Installation cancelled[/yellow]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Installing Playwright browsers...", total=None)
        
        result = subprocess.run(
            [sys.executable, "setup_playwright.py"],
            capture_output=True,
            text=True
        )
        
        progress.stop()
    
    if result.returncode == 0:
        console.print(Panel(
            "[green]✓[/green] Playwright setup complete!\n\n"
            "Browser engines are ready for:\n"
            "  • Enhanced forum scraping\n"
            "  • JavaScript-heavy websites\n"
            "  • Dynamic content loading",
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[red]✗[/red] Playwright setup failed\n\n"
            f"Error: {result.stderr}",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))


@cli.command()
@click.option("--format", "-f", type=click.Choice(["json", "markdown", "yaml"]), default="json", 
              help="Export format")
@click.option("--output", "-o", type=click.Path(), 
              help="Output file path (default: scapo_export_<timestamp>.<format>)")
@click.option("--category", "-c", help="Filter by category (text, image, video, audio, multimodal)")
@click.option("--model", "-m", help="Export specific model only")
def export(format, output, category, model):
    """Export SCAPO best practices data."""
    import json
    import yaml
    from datetime import datetime
    import os
    
    console.print(f"[blue]Exporting SCAPO data in {format} format...[/blue]")
    
    # Collect data
    export_data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "version": "0.1.0",
            "total_models": 0,
            "categories": {}
        },
        "models": {}
    }
    
    models_dir = "models"
    if not os.path.exists(models_dir):
        console.print("[red]No models directory found. Run 'scapo scrape run' first.[/red]")
        return
    
    # Filter categories if specified
    categories = ["text", "image", "video", "audio", "multimodal"]
    if category:
        if category not in categories:
            console.print(f"[red]Invalid category: {category}[/red]")
            return
        categories = [category]
    
    # Collect model data
    for cat in categories:
        cat_dir = os.path.join(models_dir, cat)
        if not os.path.exists(cat_dir):
            continue
            
        export_data["models"][cat] = {}
        model_count = 0
        
        model_dirs = os.listdir(cat_dir)
        if model:
            # Filter specific model
            if model in model_dirs:
                model_dirs = [model]
            else:
                continue
        
        for model_name in model_dirs:
            model_path = os.path.join(cat_dir, model_name)
            if not os.path.isdir(model_path):
                continue
                
            model_data = {
                "path": f"{cat}/{model_name}",
                "files": {}
            }
            
            # Read all files in model directory
            for file_name in os.listdir(model_path):
                file_path = os.path.join(model_path, file_name)
                
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            if file_name.endswith('.json'):
                                model_data["files"][file_name] = json.load(f)
                            else:
                                model_data["files"][file_name] = f.read()
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not read {file_path}: {e}[/yellow]")
                elif os.path.isdir(file_path):
                    # Handle subdirectories like examples/
                    subdir_data = {}
                    for subfile in os.listdir(file_path):
                        subfile_path = os.path.join(file_path, subfile)
                        if os.path.isfile(subfile_path):
                            try:
                                with open(subfile_path, 'r', encoding='utf-8') as f:
                                    if subfile.endswith('.json'):
                                        subdir_data[subfile] = json.load(f)
                                    else:
                                        subdir_data[subfile] = f.read()
                            except Exception as e:
                                console.print(f"[yellow]Warning: Could not read {subfile_path}: {e}[/yellow]")
                    if subdir_data:
                        model_data["files"][file_name] = subdir_data
            
            export_data["models"][cat][model_name] = model_data
            model_count += 1
        
        if model_count > 0:
            export_data["metadata"]["categories"][cat] = model_count
            export_data["metadata"]["total_models"] += model_count
    
    # Generate output filename if not specified
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"scapo_export_{timestamp}.{format}"
    
    # Export based on format
    try:
        if format == "json":
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        elif format == "yaml":
            with open(output, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
        
        elif format == "markdown":
            with open(output, 'w', encoding='utf-8') as f:
                f.write("# SCAPO Export\n\n")
                f.write(f"**Exported at:** {export_data['metadata']['exported_at']}\n")
                f.write(f"**Total models:** {export_data['metadata']['total_models']}\n\n")
                
                for cat, models in export_data["models"].items():
                    f.write(f"## {cat.upper()}\n\n")
                    for model_name, model_data in models.items():
                        f.write(f"### {model_name}\n\n")
                        f.write(f"**Path:** `{model_data['path']}`\n\n")
                        
                        # Write file contents
                        for file_name, content in model_data["files"].items():
                            f.write(f"#### {file_name}\n\n")
                            if isinstance(content, dict):
                                f.write("```json\n")
                                f.write(json.dumps(content, indent=2))
                                f.write("\n```\n\n")
                            else:
                                f.write(content)
                                f.write("\n\n")
        
        console.print(f"[green]✓[/green] Export complete: {output}")
        console.print(f"  Total models: {export_data['metadata']['total_models']}")
        for cat, count in export_data['metadata']['categories'].items():
            console.print(f"  {cat}: {count} models")
            
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/red]")


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

def display_scraper_result_enhanced(result: dict):
    """Display scraper results with enhanced formatting."""
    if result["status"] == "success":
        # Success panel
        stats = f"""
[green]✓[/green] Scraping completed successfully!

📊 [bold]Statistics:[/bold]
   Sources: [cyan]{len(result['sources_processed'])}[/cyan]
   Posts: [cyan]{result.get('posts_scraped', 0)}[/cyan]
   Practices: [cyan]{result.get('practices_extracted', 0)}[/cyan]
   Time: [cyan]{result.get('processing_time', 0):.1f}s[/cyan]
"""
        
        console.print(Panel(
            stats.strip(),
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
        
        # Models discovered
        if result.get('models_found'):
            model_tree = Tree("[bold]🤖 Models Discovered[/bold]")
            for model in result['models_found'][:15]:
                model_tree.add(f"[cyan]{model}[/cyan]")
            if len(result['models_found']) > 15:
                model_tree.add(f"[dim]... and {len(result['models_found']) - 15} more[/dim]")
            
            console.print(model_tree)
    else:
        # Error panel
        console.print(Panel(
            f"[red]✗[/red] Scraping failed\n\n"
            f"Error: {result.get('error', 'Unknown error')}",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))


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
        console.print("\n[yellow]👋 Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
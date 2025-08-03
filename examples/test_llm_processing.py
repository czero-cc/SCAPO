#!/usr/bin/env python
"""Demo script showing how LLM processing cleans up raw scraped content."""

import asyncio
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.llm_processor import LLMProcessorFactory, ProcessedPractice

console = Console()


# Sample raw content (typical Reddit post)
SAMPLE_REDDIT_POST = """
Title: Finally got GPT-4 to stop hallucinating! Here's what worked

Hey guys, been struggling with GPT-4 making stuff up, especially with technical docs. After lots of trial and error, here's what actually works:

1. **Temperature = 0** - This is KEY! I was using 0.7 before and getting random nonsense
2. Use this system prompt: "You are a technical assistant. If you don't know something, say 'I don't have that information' instead of guessing."
3. Always include this in your prompt: "Base your answer only on the provided context. Do not add information from your training data."
4. I found that top_p = 0.1 also helps reduce creativity when you don't want it

Some parameters that work for me:
- temperature: 0
- top_p: 0.1
- frequency_penalty: 0.0
- presence_penalty: 0.0
- max_tokens: 1000 (keep it reasonable)

EDIT: Wow this blew up! Thanks for the awards!
EDIT 2: Some people asking about the prompts, I use them for analyzing legal documents at work
EDIT 3: RIP my inbox lol

TL;DR: Turn temperature to 0 and be explicit about not making stuff up
"""

SAMPLE_GITHUB_CONTENT = """
## Prompt Engineering Best Practices

### 1. Clarity is Key
- Be specific about what you want
- Avoid ambiguous instructions
- Use clear delimiters

### 2. Context Matters
```python
# Good example
prompt = '''
Context: You are analyzing customer feedback for a SaaS product.
Task: Categorize the following feedback as: bug, feature request, or praise
Feedback: "The export function keeps timing out after 30 seconds"
'''

# Bad example
prompt = "What's wrong with this: export timeout"
```

### 3. Temperature Settings
| Use Case | Temperature | Top-p |
|----------|-------------|--------|
| Code generation | 0.0-0.2 | 0.1 |
| Creative writing | 0.7-1.0 | 0.9 |
| Factual Q&A | 0.0-0.3 | 0.5 |

### Check out my course!
Get 50% off my prompt engineering course with code PROMPT50!
Limited time offer! Includes 10 hours of content!
"""


async def test_local_llm():
    """Test local LLM processing (Ollama)."""
    console.print("\n[bold blue]Testing Local LLM Processing (Ollama)[/bold blue]")
    
    processor = LLMProcessorFactory.create_processor(
        provider="local",
        base_url="http://localhost:11434",
        model="llama3",  # or whatever model you have
        api_type="ollama"
    )
    
    try:
        # Process Reddit content
        console.print("\n[yellow]Processing Reddit post...[/yellow]")
        practices = await processor.process_content(SAMPLE_REDDIT_POST, "reddit")
        
        if practices:
            display_practices(practices, "Reddit Post Results")
        else:
            console.print("[red]No practices extracted from Reddit post[/red]")
        
        # Process GitHub content
        console.print("\n[yellow]Processing GitHub content...[/yellow]")
        practices = await processor.process_content(SAMPLE_GITHUB_CONTENT, "github")
        
        if practices:
            display_practices(practices, "GitHub Content Results")
        else:
            console.print("[red]No practices extracted from GitHub content[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Make sure Ollama is running and the model is pulled:[/yellow]")
        console.print("1. Start Ollama: ollama serve")
        console.print("2. Pull model: ollama pull llama3")
    finally:
        await processor.close()


async def test_openrouter():
    """Test OpenRouter processing (requires API key)."""
    console.print("\n[bold blue]Testing OpenRouter Processing[/bold blue]")
    
    # Check for API key
    import os
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]OPENROUTER_API_KEY not set in environment[/red]")
        console.print("Get your API key from https://openrouter.ai/")
        return
    
    processor = LLMProcessorFactory.create_processor(
        provider="openrouter",
        api_key=api_key,
        model="anthropic/claude-3-haiku"  # Fast and cheap
    )
    
    try:
        # Process Reddit content
        console.print("\n[yellow]Processing Reddit post...[/yellow]")
        practices = await processor.process_content(SAMPLE_REDDIT_POST, "reddit")
        
        if practices:
            display_practices(practices, "Reddit Post Results (OpenRouter)")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        await processor.close()


def display_practices(practices: list[ProcessedPractice], title: str):
    """Display extracted practices in a nice table."""
    table = Table(title=title)
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Content", style="white", width=50)
    table.add_column("Confidence", style="green", width=10)
    table.add_column("Models", style="yellow", width=20)
    
    for practice in practices:
        table.add_row(
            practice.practice_type,
            practice.content[:100] + "..." if len(practice.content) > 100 else practice.content,
            f"{practice.confidence:.2f}",
            ", ".join(practice.applicable_models) if practice.applicable_models else "general"
        )
        
        # Show parameters if any
        if practice.extracted_parameters:
            params_str = json.dumps(practice.extracted_parameters, indent=2)
            table.add_row("", f"[dim]Parameters: {params_str}[/dim]", "", "")
    
    console.print(table)
    
    # Show warnings if any
    for practice in practices:
        if practice.warnings:
            console.print(f"[yellow]⚠️  Warnings: {', '.join(practice.warnings)}[/yellow]")


async def show_raw_vs_processed():
    """Show comparison of raw vs processed content."""
    console.print(Panel.fit(
        "[bold]Raw Scraped Content vs LLM-Processed Output[/bold]\n\n"
        "This demo shows how noisy community content is cleaned and structured",
        title="LLM Processing Demo"
    ))
    
    # Show raw content
    console.print("\n[bold red]RAW CONTENT (noisy, unstructured):[/bold red]")
    console.print(Panel(SAMPLE_REDDIT_POST[:500] + "...", title="Raw Reddit Post"))
    
    # Expected processed output
    console.print("\n[bold green]PROCESSED OUTPUT (clean, structured):[/bold green]")
    example_output = """
{
  "practice_type": "parameter",
  "content": "Set temperature to 0 for factual tasks to prevent hallucination",
  "confidence": 0.9,
  "applicable_models": ["gpt-4", "gpt-3.5-turbo"],
  "extracted_parameters": {"temperature": 0, "top_p": 0.1},
  "source_quality": "high"
}

{
  "practice_type": "prompting",
  "content": "Include explicit instructions to not guess: 'If you don't know something, say I don't have that information'",
  "confidence": 0.85,
  "applicable_models": ["gpt-4", "claude", "llama"],
  "source_quality": "high"
}
"""
    console.print(Panel(example_output, title="Structured Output"))


async def main():
    """Run the demo."""
    await show_raw_vs_processed()
    
    # Test local LLM if available
    console.print("\n" + "="*60 + "\n")
    choice = console.input("Test with [bold]local[/bold] LLM (Ollama) or [bold]cloud[/bold] (OpenRouter)? [local/cloud/skip]: ")
    
    if choice.lower() == "local":
        await test_local_llm()
    elif choice.lower() == "cloud":
        await test_openrouter()
    else:
        console.print("[yellow]Skipping LLM tests[/yellow]")
    
    console.print("\n[bold green]Demo complete![/bold green]")
    console.print("\nKey benefits of LLM processing:")
    console.print("- Removes noise (edits, thanks, off-topic)")
    console.print("- Extracts specific parameters with values")
    console.print("- Assigns confidence scores")
    console.print("- Identifies which models the practice applies to")
    console.print("- Structures data for easy querying")


if __name__ == "__main__":
    asyncio.run(main()
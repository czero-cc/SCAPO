#!/usr/bin/env python
"""Setup script for Playwright browser installation."""

import subprocess
import sys
from rich.console import Console

console = Console()


def install_playwright_browsers():
    """Install Playwright browsers."""
    console.print("[bold blue]Setting up Playwright browsers...[/bold blue]")
    
    try:
        # Install Playwright browsers
        console.print("Installing Chromium, Firefox, and WebKit...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print("[green]✓[/green] Playwright browsers installed successfully")
            console.print(result.stdout)
        else:
            console.print("[red]✗[/red] Failed to install Playwright browsers")
            console.print(result.stderr)
            return False
            
        # Install system dependencies (if needed)
        console.print("\nInstalling system dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install-deps"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print("[green]✓[/green] System dependencies installed")
        else:
            console.print("[yellow]⚠[/yellow] Some system dependencies might be missing")
            console.print("You may need to run: playwright install-deps")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
    
    return True


def verify_installation():
    """Verify Playwright installation."""
    console.print("\n[bold blue]Verifying Playwright installation...[/bold blue]")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Test Chromium
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://example.com")
            title = page.title()
            browser.close()
            
            if title == "Example Domain":
                console.print("[green]✓[/green] Playwright is working correctly")
                return True
            else:
                console.print("[red]✗[/red] Playwright test failed")
                return False
                
    except Exception as e:
        console.print(f"[red]✗[/red] Playwright verification failed: {e}")
        return False


def main():
    """Main setup function."""
    console.print("[bold green]Playwright Setup for SCAPO[/bold green]")
    console.print("=" * 50)
    
    # Install browsers
    if not install_playwright_browsers():
        console.print("\n[red]Setup failed![/red]")
        console.print("Please install Playwright manually:")
        console.print("  pip install playwright")
        console.print("  playwright install")
        return 1
    
    # Verify installation
    if verify_installation():
        console.print("\n[bold green]Setup complete![/bold green]")
        console.print("\nPlaywright is ready for use with:")
        console.print("- Enhanced forum scraping")
        console.print("- JavaScript-heavy websites")
        console.print("- Dynamic content loading")
        console.print("- API interception")
        return 0
    else:
        console.print("\n[yellow]Setup completed but verification failed[/yellow]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
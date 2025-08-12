#!/usr/bin/env python
"""
Git Update Helper - Creates meaningful commits for SCAPO updates
"""
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.update_manager import UpdateManager


def get_changed_services():
    """Get list of services that have changed files"""
    result = subprocess.run(
        ["git", "status", "--porcelain", "models/"],
        capture_output=True,
        text=True
    )
    
    changed_files = result.stdout.strip().split('\n') if result.stdout else []
    services = set()
    
    for line in changed_files:
        if line and 'models/' in line:
            # Extract service name from path like "models/audio/eleven-labs/..."
            parts = line.split('/')
            if len(parts) >= 3:
                category = parts[1]
                service = parts[2]
                services.add(f"{category}/{service}")
    
    return list(services)


def generate_commit_message():
    """Generate a detailed commit message for the update"""
    manager = UpdateManager()
    changed = get_changed_services()
    
    if not changed:
        return "docs: Update service documentation"
    
    # Get update summary from manager
    summary = manager.generate_update_summary()
    
    # Build detailed message
    if len(changed) == 1:
        title = f"docs: Update {changed[0]} documentation"
    elif len(changed) <= 3:
        title = f"docs: Update {', '.join(changed)} documentation"
    else:
        title = f"docs: Update {len(changed)} service documentations"
    
    body_lines = [
        "",
        "Updated services:",
    ]
    
    for service in changed[:10]:  # List up to 10 services
        body_lines.append(f"- {service}")
    
    if len(changed) > 10:
        body_lines.append(f"- ... and {len(changed) - 10} more")
    
    body_lines.extend([
        "",
        "Update source: Reddit community discussions",
        f"Extraction date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "This update includes:",
        "- Specific pricing and tier information",
        "- Technical tips and parameter settings",
        "- Common issues and workarounds",
        "- Cost optimization strategies"
    ])
    
    return title + '\n'.join(body_lines)


def main():
    """Main function to handle git updates"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Git helper for SCAPO updates")
    parser.add_argument("--message", "-m", action="store_true", 
                       help="Generate commit message")
    parser.add_argument("--status", "-s", action="store_true",
                       help="Show what will be committed")
    parser.add_argument("--commit", "-c", action="store_true",
                       help="Create the commit")
    
    args = parser.parse_args()
    
    if args.status or not any([args.message, args.commit]):
        # Show status
        changed = get_changed_services()
        if changed:
            print(f"Services with changes: {len(changed)}")
            for service in changed:
                print(f"  - {service}")
        else:
            print("No changes to commit")
    
    if args.message:
        # Generate and show message
        message = generate_commit_message()
        print(message)
    
    if args.commit:
        # Stage and commit
        changed = get_changed_services()
        if not changed:
            print("No changes to commit")
            return
        
        # Stage model files
        subprocess.run(["git", "add", "models/"])
        
        # Generate message
        message = generate_commit_message()
        
        # Create commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ Committed {len(changed)} service updates")
        else:
            print(f"✗ Commit failed: {result.stderr}")


if __name__ == "__main__":
    main()
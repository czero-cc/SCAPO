"""SCAPO Text User Interface for exploring model content."""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import (
    Header, Footer, Tree, Static, Markdown, DataTable, 
    Button, Input, Label, Select
)
from textual.binding import Binding
from textual import work
import rich.markdown
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax


class ModelExplorer(App):
    """Interactive TUI for exploring SCAPO model content."""
    
    CSS = """
    #main {
        height: 1fr;
        layout: horizontal;
    }

    #sidebar {
        width: 40%;
        border-right: solid green;
        padding: 1;
    }

    #content {
        width: 60%;
        padding: 1;
    }

    #model-tree {
        height: 1fr;
    }

    #welcome {
        height: 1fr;
        text-align: center;
        color: cyan;
        border: solid blue;
        padding: 1;
    }

    #content-viewer {
        height: 1fr;
        border: solid green;
        padding: 1;
        overflow-y: auto;
    }

    #json-table {
        height: 1fr;
        border: solid yellow;
        padding: 1;
    }

    /* Hide elements by default */
    #content-viewer {
        display: none;
    }

    #json-table {
        display: none;
    }

    /* Tree styling */
    Tree {
        background: $surface;
    }

    TreeNode {
        color: $text;
    }

    TreeNode:hover {
        background: $accent;
    }

    TreeNode.selected {
        background: $accent;
        color: $text;
    }

    /* Markdown styling */
    Markdown {
        background: $surface;
        color: $text;
    }

    /* DataTable styling */
    DataTable {
        background: $surface;
        color: $text;
    }

    /* Header and Footer */
    Header {
        background: $accent;
        color: $text;
        text-align: center;
    }

    Footer {
        background: $accent;
        color: $text;
        text-align: center;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "help", "Help"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "search", "Search"),
    ]
    
    def __init__(self):
        super().__init__()
        self.models_dir = Path("models")
        self.current_model_path: Optional[Path] = None
        self.current_file_path: Optional[Path] = None
        self.search_term = ""
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        
        with Container(id="main"):
            with Horizontal(id="sidebar"):
                yield Tree("📚 SCAPO Models", id="model-tree")
                
            with Vertical(id="content"):
                yield Static("Select a model from the tree to view its content", id="welcome")
                yield Markdown(id="content-viewer")
                yield DataTable(id="json-table")
                
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up the app when it starts."""
        self.title = "SCAPO Model Explorer"
        self.sub_title = "Interactive Model Content Browser"
        self.load_model_tree()
    
    def load_model_tree(self) -> None:
        """Load the model directory structure into the tree."""
        tree = self.query_one("#model-tree", Tree)
        tree.clear()
        
        if not self.models_dir.exists():
            tree.add("❌ No models directory found")
            return
        
        # Add categories
        for category in ["text", "image", "video", "audio", "multimodal"]:
            cat_path = self.models_dir / category
            if cat_path.exists():
                cat_node = tree.root.add(f"📁 {category.upper()}")
                cat_node.data = {"type": "category", "path": cat_path}
                
                # Add models in this category
                for model_dir in sorted(cat_path.iterdir()):
                    if model_dir.is_dir():
                        model_node = cat_node.add(f"🤖 {model_dir.name}")
                        model_node.data = {"type": "model", "path": model_dir}
                        
                        # Add files in this model
                        for file_path in sorted(model_dir.iterdir()):
                            if file_path.is_file():
                                icon = self.get_file_icon(file_path.name)
                                file_node = model_node.add(f"{icon} {file_path.name}")
                                file_node.data = {"type": "file", "path": file_path}
        
        tree.root.expand()
    
    def get_file_icon(self, filename: str) -> str:
        """Get appropriate icon for file type."""
        if filename.endswith('.md'):
            return "📝"
        elif filename.endswith('.json'):
            return "⚙️"
        elif filename.endswith('.yaml') or filename.endswith('.yml'):
            return "📋"
        else:
            return "📄"
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node = event.node
        if not node.data:
            return
        
        data = node.data
        if data["type"] == "file":
            self.load_file_content(data["path"])
        elif data["type"] == "model":
            self.show_model_info(data["path"])
    
    def load_file_content(self, file_path: Path) -> None:
        """Load and display file content."""
        self.current_file_path = file_path
        
        try:
            if file_path.suffix == '.json':
                self.display_json_content(file_path)
            elif file_path.suffix == '.md':
                self.display_markdown_content(file_path)
            else:
                self.display_text_content(file_path)
        except Exception as e:
            self.show_error(f"Error loading file: {e}")
    
    def display_json_content(self, file_path: Path) -> None:
        """Display JSON content in a table."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Hide markdown viewer and show table
            self.query_one("#content-viewer").display = False
            table = self.query_one("#json-table")
            table.display = True
            table.clear(columns=True)
            
            if isinstance(data, list) and len(data) > 0:
                # Display as table
                if isinstance(data[0], dict):
                    columns = list(data[0].keys())
                    table.add_columns(*columns)
                    for item in data:
                        row = [str(item.get(col, "")) for col in columns]
                        table.add_row(*row)
                else:
                    table.add_columns("Value")
                    for item in data:
                        table.add_row(str(item))
            elif isinstance(data, dict):
                # Display key-value pairs
                table.add_columns("Key", "Value")
                for key, value in data.items():
                    table.add_row(str(key), str(value))
            else:
                table.add_columns("Content")
                table.add_row(str(data))
                
        except Exception as e:
            self.show_error(f"Error parsing JSON: {e}")
    
    def display_markdown_content(self, file_path: Path) -> None:
        """Display markdown content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Hide table and show markdown viewer
            self.query_one("#json-table").display = False
            viewer = self.query_one("#content-viewer")
            viewer.display = True
            viewer.update(content)
            
        except Exception as e:
            self.show_error(f"Error loading markdown: {e}")
    
    def display_text_content(self, file_path: Path) -> None:
        """Display plain text content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Hide table and show markdown viewer (for syntax highlighting)
            self.query_one("#json-table").display = False
            viewer = self.query_one("#content-viewer")
            viewer.display = True
            viewer.update(f"```\n{content}\n```")
            
        except Exception as e:
            self.show_error(f"Error loading file: {e}")
    
    def show_model_info(self, model_path: Path) -> None:
        """Show information about a model."""
        self.current_model_path = model_path
        
        # Hide table and show markdown viewer
        self.query_one("#json-table").display = False
        viewer = self.query_one("#content-viewer")
        viewer.display = True
        
        info = f"""# {model_path.name}

## Model Information

**Path:** `{model_path}`

## Available Files

"""
        
        for file_path in sorted(model_path.iterdir()):
            if file_path.is_file():
                size = file_path.stat().st_size
                icon = self.get_file_icon(file_path.name)
                info += f"- {icon} **{file_path.name}** ({size:,} bytes)\n"
        
        viewer.update(info)
    
    def show_error(self, message: str) -> None:
        """Show error message."""
        self.query_one("#json-table").display = False
        viewer = self.query_one("#content-viewer")
        viewer.display = True
        viewer.update(f"# Error\n\n{message}")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()
    
    def action_help(self) -> None:
        """Show help."""
        help_text = """# SCAPO Model Explorer Help

## Navigation
- Use arrow keys to navigate the tree
- Press Enter to select a file or model
- Press 'q' to quit
- Press 'r' to refresh the model tree

## File Types
- 📝 Markdown files (.md) - Best practices and guides
- ⚙️ JSON files (.json) - Parameters and metadata
- 📋 YAML files (.yml/.yaml) - Configuration files
- 📄 Other files - Raw content

## Features
- Interactive tree navigation
- Markdown rendering
- JSON table view
- File size information
- Search functionality (coming soon)
"""
        self.query_one("#json-table").display = False
        viewer = self.query_one("#content-viewer")
        viewer.display = True
        viewer.update(help_text)
    
    def action_refresh(self) -> None:
        """Refresh the model tree."""
        self.load_model_tree()
    
    def action_search(self) -> None:
        """Search functionality (placeholder)."""
        # TODO: Implement search
        self.show_error("Search functionality coming soon!")


def run_tui():
    """Run the SCAPO TUI."""
    app = ModelExplorer()
    app.run()


if __name__ == "__main__":
    run_tui() 
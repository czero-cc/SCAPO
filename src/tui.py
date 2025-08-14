"""SCAPO Text User Interface for exploring model content."""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
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
        border-right: solid cyan;
        padding: 1;
    }

    #content {
        width: 60%;
        padding: 1;
        layout: vertical;
    }

    #model-tree {
        height: 1fr;
        overflow-y: scroll;
        overflow-x: scroll;
    }

    #welcome {
        height: auto;
        min-height: 6;
        border: solid cyan;
        padding: 1;
        overflow-y: auto;
        background: $surface;
        color: $text;
    }

    #content-viewer {
        height: 1fr;
        border: solid cyan;
        padding: 1;
        overflow-y: scroll;
        overflow-x: scroll;
        background: $surface;
        color: $text;
    }

    #json-table {
        height: 1fr;
        border: solid cyan;
        padding: 1;
        overflow-y: scroll;
        overflow-x: scroll;
        background: $surface;
        color: $text;
        scrollbar-gutter: stable;
        scrollbar-size: 1 1;
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
        color: $text;
    }

    TreeNode {
        color: $text;
    }

    TreeNode:hover {
        background: cyan;
        color: black;
    }

    TreeNode.selected {
        background: cyan;
        color: black;
    }

    /* Markdown styling */
    VerticalScroll#content-viewer, Markdown {
        background: $surface;
        color: $text;
        overflow-y: scroll;
        overflow-x: scroll;
        scrollbar-gutter: stable;
        scrollbar-size: 1 1;
    }

    /* Focus styling is unified below for both content boxes */

    /* DataTable styling */
    DataTable {
        background: $surface;
        color: $text;
        overflow-y: scroll;
        overflow-x: scroll;
        scrollbar-gutter: stable;
        scrollbar-size: 1 1;
    }

    /* Scrollbar styling */
    ScrollBar {
        background: cyan;
        color: black;
    }

    /* Focus highlight for content boxes (same style for Markdown and JSON) */
    #content-viewer:focus, #json-table:focus {
        background: $boost;
        border: solid cyan;
        color: $text;
    }

    ScrollBar.vertical {
        background: cyan;
        color: black;
    }

    ScrollBar.horizontal {
        background: cyan;
        color: black;
    }

    /* Header and Footer */
    Header {
        background: cyan;
        color: black;
        text-align: center;
        text-style: bold;
    }

    #footer {
        background: cyan;
        color: black;
        text-align: center;
        text-style: bold;
        height: 1;
        padding: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "help", "Help"),
        Binding("space", "toggle_expand", "Toggle Expand"),
        Binding("c", "copy_content", "Copy Content"),
        Binding("o", "open_location", "Open Location"),
    ]
    
    def __init__(self):
        super().__init__()
        self.models_dir = Path("models")
        self.current_model_path: Optional[Path] = None
        self.current_file_path: Optional[Path] = None
    
    def get_welcome_message(self, focus: str = "tree") -> str:
        """Generate welcome message with command recap."""
        focus_status = "Tree" if focus == "tree" else "Content"
        
        return f"""SCAPO Model Explorer

Status: Ready | Focus: {focus_status} | Viewer: Active

Navigation: ↑/↓ Navigate | Enter Select | Space Expand | Tab Cycle | q Quit | h Help

Select a model from the tree to view content."""
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        
        with Container(id="main"):
            with Horizontal(id="sidebar"):
                yield Tree("📚 Models", id="model-tree")
                
            with Vertical(id="content"):
                yield Static(self.get_welcome_message("tree"), id="welcome")
                with VerticalScroll(id="content-viewer"):
                    yield Markdown(id="md-view")
                yield DataTable(id="json-table")
                
        yield Static("q Quit  h Help  space Toggle Expand  c Copy Content  o Open Location", id="footer", classes="scapo-footer")
    
    def on_mount(self) -> None:
        """Set up the app when it starts."""
        self.title = "SCAPO"
        self.sub_title = "Stay Calm and Prompt On - Model Explorer"
        self.load_model_tree()
        
        # Ensure content viewer container exists
        _ = self.query_one("#content-viewer", VerticalScroll)
        
        # Focus the tree for better navigation
        tree = self.query_one("#model-tree", Tree)
        tree.focus()
    
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
            
            # Hide welcome after first selection
            self.query_one("#welcome").display = False

            # Hide markdown viewer and show table
            self.query_one("#content-viewer").display = False
            table = self.query_one("#json-table")
            table.display = True
            table.clear(columns=True)
            
            # Add a header row with file info and open location button
            table.add_columns("File Info")
            table.add_row(f"📄 {file_path.name} | Press 'o' to open location in Finder")
            
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
            
            # Hide welcome after first selection
            self.query_one("#welcome").display = False

            # Hide table and show markdown viewer
            self.query_one("#json-table").display = False
            viewer = self.query_one("#content-viewer")
            viewer.display = True
            
            # Add file info header
            header = f"# 📄 {file_path.name}\n\n*Press 'o' to open location in Finder*\n\n---\n\n"
            md = self.query_one("#md-view", Markdown)
            md.update(header + content)
            
        except Exception as e:
            self.show_error(f"Error loading markdown: {e}")
    
    def display_text_content(self, file_path: Path) -> None:
        """Display plain text content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Hide welcome after first selection
            self.query_one("#welcome").display = False

            # Hide table and show markdown viewer (for syntax highlighting)
            self.query_one("#json-table").display = False
            viewer = self.query_one("#content-viewer")
            viewer.display = True
            
            # Add file info header
            header = f"# 📄 {file_path.name}\n\n*Press 'o' to open location in Finder*\n\n---\n\n"
            md = self.query_one("#md-view", Markdown)
            md.update(header + f"```\n{content}\n```")
            
        except Exception as e:
            self.show_error(f"Error loading file: {e}")
    
    def show_model_info(self, model_path: Path) -> None:
        """Show information about a model."""
        self.current_model_path = model_path
        
        # Hide welcome after first selection
        self.query_one("#welcome").display = False

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
        
        md = self.query_one("#md-view", Markdown)
        md.update(info)
    
    def show_error(self, message: str) -> None:
        """Show error message."""
        # Hide welcome after first selection
        self.query_one("#welcome").display = False
        self.query_one("#json-table").display = False
        viewer = self.query_one("#content-viewer")
        viewer.display = True
        md = self.query_one("#md-view", Markdown)
        md.update(f"# Error\n\n{message}")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()
    
    def action_help(self) -> None:
        """Show help."""
        help_text = """# SCAPO Model Explorer Help

## Navigation
- ↑/↓ - Navigate through the tree
- Enter - Select a file or model
- Space - Expand/collapse tree nodes
- q - Quit the TUI
- h - Show this help
- c - Copy current content to clipboard
- o - Open file/model location in Finder

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
- Copy content to clipboard
"""
        # Hide welcome after first selection
        self.query_one("#welcome").display = False
        self.query_one("#json-table").display = False
        viewer = self.query_one("#content-viewer")
        viewer.display = True
        md = self.query_one("#md-view", Markdown)
        md.update(help_text)
    

    

    
    def action_toggle_expand(self) -> None:
        """Toggle expansion of the currently selected tree node."""
        tree = self.query_one("#model-tree", Tree)
        if tree.cursor_node:
            if tree.cursor_node.is_expanded:
                tree.cursor_node.collapse()
            else:
                tree.cursor_node.expand()
    
    def action_copy_content(self) -> None:
        """Copy current content to clipboard."""
        try:
            import pyperclip
            
            # Determine what content to copy
            if self.current_file_path:
                # Copy file content
                with open(self.current_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add file info header
                copy_text = f"# {self.current_file_path.name}\n\n{content}"
                
                pyperclip.copy(copy_text)
                self.notify(f"Copied {self.current_file_path.name} to clipboard", severity="information")
                
            elif self.current_model_path:
                # Copy model info
                info = f"Model: {self.current_model_path.name}\nPath: {self.current_model_path}\n\nFiles:\n"
                
                for file_path in sorted(self.current_model_path.iterdir()):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        icon = self.get_file_icon(file_path.name)
                        info += f"- {icon} {file_path.name} ({size:,} bytes)\n"
                
                pyperclip.copy(info)
                self.notify(f"Copied {self.current_model_path.name} info to clipboard", severity="information")
                
            else:
                # Copy welcome message
                welcome_text = self.get_welcome_message("tree")
                pyperclip.copy(welcome_text)
                self.notify("Copied welcome message to clipboard", severity="information")
                
        except ImportError:
            self.notify("Copy functionality requires pyperclip. Install with: pip install pyperclip", severity="warning")
        except Exception as e:
            self.notify(f"Copy failed: {e}", severity="error")

    def action_open_location(self) -> None:
        """Open the current file or model location in Finder."""
        try:
            import subprocess
            import platform
            
            if self.current_file_path:
                # Open file location
                path = self.current_file_path.parent
                self._open_in_finder(path)
                self.notify(f"Opened location of {self.current_file_path.name}", severity="information")
                
            elif self.current_model_path:
                # Open model location
                self._open_in_finder(self.current_model_path)
                self.notify(f"Opened location of {self.current_model_path.name}", severity="information")
                
            else:
                # Open models directory
                self._open_in_finder(self.models_dir)
                self.notify("Opened models directory", severity="information")
                
        except Exception as e:
            self.notify(f"Failed to open location: {e}", severity="error")
    
    def _open_in_finder(self, path: Path) -> None:
        """Open a path in the system file manager."""
        import subprocess
        import platform
        
        system = platform.system()
        
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(path)])
        elif system == "Windows":
            subprocess.run(["explorer", str(path)])
        elif system == "Linux":
            subprocess.run(["xdg-open", str(path)])
        else:
            raise OSError(f"Unsupported operating system: {system}")


def run_tui():
    """Run the SCAPO TUI."""
    app = ModelExplorer()
    app.run()


if __name__ == "__main__":
    run_tui() 
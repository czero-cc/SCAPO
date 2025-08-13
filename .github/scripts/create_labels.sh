#!/bin/bash

# Script to create GitHub labels for Dependabot
# Run this script with GitHub CLI (gh) installed and authenticated

echo "Creating GitHub labels for Dependabot..."

# Create labels with appropriate colors
gh label create dependencies --description "Dependency updates" --color "0366d6" 2>/dev/null || echo "Label 'dependencies' already exists"
gh label create javascript --description "JavaScript related changes" --color "f7df1e" 2>/dev/null || echo "Label 'javascript' already exists"
gh label create mcp --description "MCP server related" --color "008672" 2>/dev/null || echo "Label 'mcp' already exists"
gh label create python --description "Python related changes" --color "3776ab" 2>/dev/null || echo "Label 'python' already exists"
gh label create ci --description "Continuous Integration" --color "e11d21" 2>/dev/null || echo "Label 'ci' already exists"

echo "Label creation complete!"
echo ""
echo "Current labels:"
gh label list | grep -E "dependencies|javascript|mcp|python|ci"
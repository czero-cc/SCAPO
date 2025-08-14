Output ../assets/3.gif

Require bash
Require uv

Set Shell bash
Set Width 1200
Set Height 650
Set FontFamily "Monaco"
Set FontSize 18
Set LetterSpacing 0
Set LineHeight 1.2
Set Padding 5
Set Margin 10
Set MarginFill "#008B8B"
Set WindowBar Colorful
Set BorderRadius 12
Set Framerate 60
Set PlaybackSpeed 1
Set TypingSpeed 30 ms
Set CursorBlink false
Set Theme "Catppuccin Frappe"
Set WaitTimeout 120 s

# hidden: go to right folder
Hide
Type "cd .."
Enter
Type "clear"
Enter
Show

# Discover services from GitHub Awesome lists
Type "uv run scapo scrape discover --update"
Sleep 1s
Enter
Sleep 3s

# Step 2: Extract optimization tips for services
Type "uv run scapo scrape targeted --service "HeyGen" --limit 20"
Sleep 1s
Enter
Sleep 5s
Type "uv run scapo scrape targeted --service "Midjourney" --limit 20"
Sleep 1s
Enter
Sleep 5s

# Or batch process multiple services
Type "uv run scapo scrape batch --category video --limit 15"
Sleep 1s
Enter
Sleep 1s
Type "y"
Sleep 1s
Enter
Sleep 5s

# Process ALL priority services one by one (i.e. all services with 'ultra' tag, see targted_search_generator.py)
Type "uv run scapo scrape all --priority ultra --limit 20"
Sleep 1s
Enter
Sleep 1s
Type "y"
Sleep 1s
Enter
Wait
Sleep 5s


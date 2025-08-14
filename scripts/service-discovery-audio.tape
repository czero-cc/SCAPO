Output ../assets/service-discovery-audio.gif

Require bash
Require uv

Set Shell bash
Set Width 1200
Set Height 650
Set FontFamily "Monaco"
Set FontSize 14
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
Set WaitTimeout 160 s

# hidden: go to right folder
Hide
Type "cd .."
Enter
Type "clear"
Enter
Show

# Discover services from GitHub Awesome lists
Type "uv run scapo scrape discover --update"
Sleep 1 s
Enter
Sleep 3 s
Hide
Type "clear"
Enter
Show


# Extract optimization tips for specific services
Type "uv run scapo scrape targeted --service 'Eleven Labs' --limit 2"
Sleep 1 s
Enter
Sleep 3 s
Hide
Type "clear"
Enter
Show

# Batch process multiple priority services
Type "uv run scapo scrape batch --max-services 1 --category audio"
Sleep 1 s
Enter
Sleep 1 s
Type "y"
Enter
Wait
Sleep 5s


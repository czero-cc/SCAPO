Output ../assets/promo_scapo.gif

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
Set Margin 40
Set MarginFill "#008B8B"
Set WindowBar Colorful
Set BorderRadius 12
Set Framerate 60
Set PlaybackSpeed 1.0
Set TypingSpeed 30 ms
Set CursorBlink false
Set Theme "CyberPunk2077"
Set WaitTimeout 120 s

# hidden: go to right folder
Hide
Type "cd .."
Enter
Type "clear"
Enter
Type "uv run scapo"
Enter
Show

# Scene 1: Show available sources
Type "uv run scapo sources"
Enter
Wait
Sleep 800 ms

# Scene 2: Run a Reddit scrape (auto-confirm)
Type "yes | uv run scapo scrape run --sources reddit:LocalLLaMA --limit 10"
Enter
Sleep 2 s
Wait
Sleep 800 ms

# Scene 3: List produced models (text)
Type "uv run scapo models list -c text "
Enter
Wait
Sleep 800 ms

# Scene 4: Launch TUI (briefly) and quit
Type "uv run scapo tui"
Enter
Sleep 1500 ms
Type "q"
Enter
Sleep 600 ms

# End pause
Sleep 1 s


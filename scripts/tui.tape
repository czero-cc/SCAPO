Output ../assets/tui.gif

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
# Launch TUI (briefly) and quit
Sleep 2s
Type "uv run scapo tui"
Enter
Sleep 2s
Down 4
Sleep 1s
Enter
Sleep 1s
Down 4
Sleep 1s
Enter
Sleep 1s
Down 5
Enter
Sleep  2s
Type "q"
Sleep 600 ms

# End pause
Sleep 1 s


Output ../assets/tui.gif

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

# Launch TUI (briefly) and quit
Type "uv run scapo tui"
Sleep 2s
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
Sleep 1s
Enter
Tab
Sleep 2s
Down 15
Sleep 4
Type "q"



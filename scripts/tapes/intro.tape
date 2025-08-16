Output ../../assets/intro.gif

Require bash
Require uv

Set Shell bash
Set Width 1200
Set Height 700
Set FontFamily "Monaco"
Set FontSize 20
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
Type "cd ../../"
Enter
Type "clear"
Enter
Show

Type "uv run scapo"
Sleep 1s
Enter
Sleep 5s

# End pause
Sleep 1 s


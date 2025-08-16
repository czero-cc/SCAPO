Output ../../assets/scrape-batch.gif

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
Set WaitTimeout 1000 s

# hidden: go to right folder
Hide
Type "cd ../../"
Enter
Type "clear"
Enter
Show

# Batch process multiple priority services
Type "uv run scapo scrape batch --category audio --batch-size 10 --limit 1"
Sleep 1 s
Enter
Sleep 1 s
Type "y"
Enter
Wait
Sleep 3s


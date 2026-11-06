Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\user\jarvis"
WshShell.Run """C:\Users\user\jarvis\.venv312\Scripts\pythonw.exe"" ""C:\Users\user\jarvis\friday_reel_hud.py""", 0, False

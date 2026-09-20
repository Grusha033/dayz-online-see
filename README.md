**DayzOnlineSee**

Terminal-based (TUI) tool to check DayZ server online via the Valve A2S protocol.

It displays live player counts, renders daily online history charts, and auto-refreshes data.

Requirements
Python 3.10+
python-a2s (installed automatically)
windows-curses (Windows only, installed automatically)

**Quick Start**
------------------------------
Clone the repository:
\ngit clone https://github.com/Grusha033/DayzOnlineSee.git
\ncd DayzOnlineSee
------------------------------

------------------------------
Linux
\nchmod +x linux-run.sh
\n./linux-run.sh
------------------------------

------------------------------
Windows
\nRun:
\nwindows-run.bat
------------------------------

Launchers automatically set up .venv and install missing dependencies.

**Data Storage**
history.json - Saved server list
settings.json - Auto-refresh state
stats.json - Compressed daily online history (RLE format)

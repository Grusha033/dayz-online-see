# DayzOnlineSee

Terminal-based (TUI) tool to check DayZ server online via the Valve A2S protocol.  
It displays live player counts, renders daily online history charts, and auto-refreshes data.

## Requirements

- Python 3.10+
- `python-a2s` (installed automatically)
- `windows-curses` (Windows only, installed automatically)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/Grusha033/dayz-online-see.git
   cd DayzOnlineSee
   ```

2. Run on **Linux**:
   ```bash
   chmod +x linux-run.sh
   ./linux-run.sh
   ```

3. Run on **Windows**:
   ```cmd
   windows-run.bat
   ```

> Launchers automatically set up `.venv` and install missing dependencies.

## Data Storage

- `history.json` - Saved server list
- `settings.json` - Auto-refresh state
- `stats.json` - Compressed daily online history (RLE format)

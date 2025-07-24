# Screenshot Organizer

A Python GUI application that automatically organizes screenshots into session-based folders for audit and assessment work.

## Features
- Monitors screenshot folder in real-time
- Automatically moves screenshots into uniquely named session folders
- Dark mode GUI
- Works best on Windows

## Installation
Install the required dependency:
```bash
pip install watchdog
```

## Usage
To start the GUI application:
```bash
python screenshot_organizer.py
```

1. **Configure Options**  
   - **Screenshot Folder**: where your OS saves screenshots (default: `Pictures/Screenshots` on Windows)  
   - **Output Folder**: destination folder for organized sessions  
   - **Year, Project, Audit Type, Starting Index**

2. **Start**: Click **Start Session** and take screenshots.  
3. **New Session**: Click **New Session** to create the next evidence folder.  
4. **Stop**: Click **Stop Watching** to stop monitoring.

What to expect

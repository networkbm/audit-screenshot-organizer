# Screenshot Organizer

A Python GUI tool that helps organize screenshots into clean, session based folders. Built for audit, assessment, and evidence collection work.

---

## Features

- Automatically organizes screenshots into session folders  
- Real-time screenshot monitoring (manual mode)  
- Floating mini toolbar for quick screenshots (region or full screen)  
- Playwright support for automated website screenshots  
- Dark mode GUI  
- Draggable, always-on-top toolbar


## Installation

Install the required dependencies:

```bash
pip install watchdog playwright
pip install pillow
```
## Usage

```bash
python3 screenshot_organizer.py
```

## Quick Start

1. **Configure Options**
   - **Screenshot Folder**  
     Where your OS saves screenshots  
     (Default: `Pictures/Screenshots` on Windows)

   - **Output Folder**  
     Destination folder where session folders are created

   - **Session Info**  
     Year, Project, Audit Type, and Starting Index

2. **Start Session**
   Click **Start Session** to create a new session folder.

3. **Choose How You Want to Capture**
   - **Manual Mode (Watch Folder)**  
     Take screenshots normally using your OS shortcuts (or the Mini Toolbar).  
     The app will automatically move them into the active session folder.

   - **Playwright Mode (Website Capture)**  
     Switch to **Playwright mode**, enter a **URL**, optionally add an **element selector**, then click **Capture Now**.  
     Screenshots will be saved into the active session folder.

4. **Mini Toolbar (Optional)**
   Click **Show Mini Toolbar** to open a small toolbar you can drag anywhere.  
   Use **Region** or **Full Screen** to capture quickly without the main UI.

5. **New Session**
   Click **New Session** to create the next evidence folder.

6. **Stop Watching**
   Click **Stop Watching** to stop monitoring the screenshot folder (Manual mode).


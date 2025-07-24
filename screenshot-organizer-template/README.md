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

---

## Example Demo

Once you initiate the script, the following GUI will appear:

![Screenshot of GUI](screenshots/gui-example.png)

You can customize:
- **Year**
- **Project**
- **Audit Type**
- **Start Index (Identifier)**
- **Screenshot Folder**
- **Output Folder**

### Running a Session
Once you start a session, the customized index appears corresponding to the project.  
If successful, you will see a **"Started Watching"** message:

![Session Started](screenshots/session-started.png)

Here is an example of a successful folder creation:

![Folder Created](screenshots/folder-creation.png)

Screenshots are saved using the default naming convention:

![Screenshot Files](screenshots/screenshot-files.png)

### Starting a New Session
If you start a new session, a new folder will be created automatically:

![New Session Folder](screenshots/new-session.png)

### Stopping the Session
Once you are done taking screenshots, click the **"Stop Watching"** button.  
You will receive a confirmation message:

![Stop Watching Confirmation](screenshots/stop-watching.png)

---

## License
MIT License

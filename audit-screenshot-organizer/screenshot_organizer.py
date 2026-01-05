import os
import platform
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import threading
import time
import queue
import re

from PIL import ImageGrab

DEFAULT_WINDOWS_SCREENSHOT = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
DEFAULT_SCREENSHOT_FOLDER = DEFAULT_WINDOWS_SCREENSHOT

BG = "#14161A"
PANEL = "#1B1E24"
ENTRY_BG = "#242833"
ENTRY_FG = "#E7EAF0"
TEXT = "#E7EAF0"
MUTED = "#AAB1C1"
LOG_BG = "#0F1115"
LOG_FG = "#D7DBE6"

BTN_BG = "#2A2F3A"
BTN_HOVER = "#353B49"
BTN_ACTIVE = "#3F4656"

TOOLBAR_BG = "#0E1117"
TOOLBAR_BORDER = "#2A2E38"
TOOLBAR_TEXT = "#E7EAF0"
TOOLBAR_MUTED = "#C7CCDA"
TOOLBAR_BTN_BG = "#242A36"
TOOLBAR_BTN_HOVER = "#2E3646"
TOOLBAR_BTN_ACTIVE = "#3A4458"


def ensure_unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        p = f"{base} ({i}){ext}"
        if not os.path.exists(p):
            return p
        i += 1


def open_folder(path):
    if platform.system() == "Darwin":
        subprocess.run(["open", path], check=False)
    elif platform.system() == "Windows":
        os.startfile(path)
    else:
        subprocess.run(["xdg-open", path], check=False)


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".png"):
            self.app.file_queue.put(event.src_path)


class MiniToolbar:
    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.geometry("600x64+200+120")
        self.win.configure(bg=TOOLBAR_BG)
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.overrideredirect(True)

        self._x = 0
        self._y = 0

        outer = tk.Frame(self.win, bg=TOOLBAR_BG, highlightthickness=1, highlightbackground=TOOLBAR_BORDER)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        bar = tk.Frame(outer, bg=TOOLBAR_BG)
        bar.pack(fill="both", expand=True, padx=8, pady=8)

        self.status = tk.StringVar(value="Ready")
        tk.Label(bar, textvariable=self.status, bg=TOOLBAR_BG, fg=TOOLBAR_MUTED).pack(side="right", padx=(10, 0))

        def mkbtn(label, cmd):
            w = tk.Label(bar, text=label, bg=TOOLBAR_BTN_BG, fg=TOOLBAR_TEXT, padx=12, pady=7)

            def enter(_): w.configure(bg=TOOLBAR_BTN_HOVER)
            def leave(_): w.configure(bg=TOOLBAR_BTN_BG)
            def down(_): w.configure(bg=TOOLBAR_BTN_ACTIVE)
            def up(e):
                w.configure(bg=TOOLBAR_BTN_HOVER)
                if 0 <= e.x <= w.winfo_width() and 0 <= e.y <= w.winfo_height():
                    cmd()

            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
            w.bind("<ButtonPress-1>", down)
            w.bind("<ButtonRelease-1>", up)
            return w

        mkbtn("Region", self.capture_region).pack(side="left", padx=(0, 8))
        mkbtn("Full Screen", self.capture_full).pack(side="left", padx=(0, 8))
        mkbtn("New Session", self.app.new_session).pack(side="left", padx=(0, 8))
        mkbtn("Open Folder", self.open_current_folder).pack(side="left", padx=(0, 8))
        mkbtn("Hide", self.hide).pack(side="left")

        for w in (self.win, outer):
            w.bind("<ButtonPress-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)

    def start_move(self, e):
        self._x = e.x_root - self.win.winfo_x()
        self._y = e.y_root - self.win.winfo_y()

    def do_move(self, e):
        self.win.geometry(f"+{e.x_root - self._x}+{e.y_root - self._y}")

    def show(self):
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        self.win.withdraw()

    def open_current_folder(self):
        self.app.ensure_session()
        open_folder(self.app.active_session_folder)

    def capture_full(self):
        self.app.ensure_session()
        out = ensure_unique_path(os.path.join(self.app.active_session_folder, f"{self.app.timestamp()}_full.png"))
        self.status.set("Capturing…")

        def work():
            try:
                if platform.system() == "Darwin":
                    subprocess.run(["screencapture", "-x", out], check=False)
                else:
                    ImageGrab.grab().save(out)
                self.app.ui_log(f"Saved: {os.path.basename(out)}")
                self.status.set("Saved")
            except Exception as e:
                self.app.ui_log(f"Capture error: {e}")
                self.status.set("Failed")

        threading.Thread(target=work, daemon=True).start()

    def capture_region(self):
        self.app.ensure_session()
        out = ensure_unique_path(os.path.join(self.app.active_session_folder, f"{self.app.timestamp()}_region.png"))
        self.status.set("Select region…")
        self.hide()

        def grab():
            try:
                if platform.system() == "Darwin":
                    subprocess.run(["screencapture", "-i", "-x", out], check=False)
                else:
                    img = ImageGrab.grab()
                    img.save(out)
                self.app.ui_log(f"Saved: {os.path.basename(out)}")
                self.status.set("Saved")
            except Exception as e:
                self.app.ui_log(f"Capture error: {e}")
                self.status.set("Failed")
            finally:
                self.show()

        threading.Thread(target=grab, daemon=True).start()


class ScreenshotOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screenshot Organizer")
        self.root.geometry("760x560")
        self.root.configure(bg=BG)

        self.year = tk.StringVar(value=str(datetime.now().year))
        self.project = tk.StringVar(value="CSP")
        self.audit_type = tk.StringVar(value="Annual")
        self.session_number = tk.IntVar(value=1)

        self.screenshot_folder = tk.StringVar(value=DEFAULT_SCREENSHOT_FOLDER)
        self.output_base_folder = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Documents", "Evidence"))

        self.active_session_folder = ""
        self.running = False
        self.toolbar = None

        self.file_queue = queue.Queue()
        self.log_queue = queue.Queue()

        threading.Thread(target=self.process_queue, daemon=True).start()

        self.build_ui()
        self.root.after(100, self.pump_logs)

    def build_ui(self):
        ttk.Style().theme_use("clam")

        f = tk.Frame(self.root, bg=BG)
        f.pack(fill="both", expand=True, padx=14, pady=14)

        def row(label, var):
            tk.Label(f, text=label, bg=BG, fg=TEXT).pack(anchor="w")
            tk.Entry(f, textvariable=var, bg=ENTRY_BG, fg=ENTRY_FG).pack(fill="x", pady=4)

        row("Year", self.year)
        row("Project", self.project)
        row("Audit Type", self.audit_type)
        row("Start Index", self.session_number)
        row("Screenshot Folder", self.screenshot_folder)
        row("Output Folder", self.output_base_folder)

        tk.Button(f, text="Start Session", command=self.start_session).pack(pady=6)
        tk.Button(f, text="New Session", command=self.new_session).pack(pady=6)
        tk.Button(f, text="Show Mini Toolbar", command=self.toggle_toolbar).pack(pady=6)

        self.log = tk.Text(f, bg=LOG_BG, fg=LOG_FG, height=10)
        self.log.pack(fill="both", expand=True, pady=10)

    def toggle_toolbar(self):
        if not self.toolbar:
            self.toolbar = MiniToolbar(self)
        self.toolbar.show()

    def ensure_session(self):
        if not self.active_session_folder:
            self.create_session_folder()

    def start_session(self):
        self.create_session_folder()
        self.running = True

    def new_session(self):
        self.session_number.set(self.session_number.get() + 1)
        self.create_session_folder()

    def create_session_folder(self):
        name = f"{self.year.get()}-{self.project.get()}-{self.audit_type.get()}-{str(self.session_number.get()).zfill(3)}"
        self.active_session_folder = os.path.join(self.output_base_folder.get(), name)
        os.makedirs(self.active_session_folder, exist_ok=True)
        self.ui_log(f"Session folder: {self.active_session_folder}")

    def process_queue(self):
        while True:
            path = self.file_queue.get()
            try:
                if self.active_session_folder and os.path.exists(path):
                    dest = ensure_unique_path(os.path.join(self.active_session_folder, os.path.basename(path)))
                    shutil.move(path, dest)
                    self.ui_log(f"Moved: {os.path.basename(dest)}")
            finally:
                self.file_queue.task_done()

    def ui_log(self, msg):
        self.log_queue.put(msg)

    def pump_logs(self):
        try:
            while True:
                self.log.insert("end", self.log_queue.get_nowait() + "\n")
                self.log.see("end")
        except queue.Empty:
            pass
        self.root.after(100, self.pump_logs)

    def timestamp(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    root = tk.Tk()
    ScreenshotOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

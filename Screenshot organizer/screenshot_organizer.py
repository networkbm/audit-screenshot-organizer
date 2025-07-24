import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import threading
import time
import queue

# Default Windows screenshot folder
DEFAULT_WINDOWS_SCREENSHOT = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
DEFAULT_SCREENSHOT_FOLDER = DEFAULT_WINDOWS_SCREENSHOT

class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            # Only handle PNG files (typical Windows screenshots)
            if filename.lower().endswith(".png"):
                self.app.file_queue.put(event.src_path)

class ScreenshotOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screenshot Organizer")
        self.root.geometry("650x450")
        self.root.configure(bg="#2b2b2b")

        self.year = tk.StringVar(value=str(datetime.now().year))
        self.project = tk.StringVar(value="CSP")
        self.audit_type = tk.StringVar(value="Annual")
        self.session_number = tk.IntVar(value=1)

        self.screenshot_folder = tk.StringVar(value=DEFAULT_SCREENSHOT_FOLDER)
        self.output_base_folder = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Documents", "Evidence"))

        self.active_session_folder = ""
        self.observer = None
        self.running = False

        self.file_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.worker_thread.start()

        self.build_gui()

    def build_gui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#2b2b2b", foreground="white")
        style.configure("TButton", background="#3c3f41", foreground="white", padding=6)
        style.configure("TEntry", fieldbackground="#3c3f41", foreground="white")

        frame = tk.Frame(self.root, bg="#2b2b2b")
        frame.pack(pady=10)

        ttk.Label(frame, text="Year:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.year).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Project:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.project).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Audit Type:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.audit_type).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Start Index:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.session_number).grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Screenshot Folder (Source):").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.screenshot_folder, width=40).grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self.select_screenshot_folder).grid(row=4, column=2, padx=5)

        ttk.Label(frame, text="Output Folder (Destination):").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.output_base_folder, width=40).grid(row=5, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self.select_output_folder).grid(row=5, column=2, padx=5)

        button_frame = tk.Frame(self.root, bg="#2b2b2b")
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Start Session", command=self.start_session).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="New Session", command=self.new_session).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Stop Watching", command=self.stop_watching).grid(row=0, column=2, padx=5)

        # Show current session label
        self.current_session_label = tk.Label(self.root, text="Current Session: None", bg="#2b2b2b", fg="white", font=("Arial", 12))
        self.current_session_label.pack(pady=5)

        self.log = tk.Text(self.root, bg="#1e1e1e", fg="white", wrap="word", height=10)
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

    def log_message(self, message):
        self.log.insert(tk.END, f"{message}\n")
        self.log.see(tk.END)

    def select_screenshot_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.screenshot_folder.set(folder)

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_base_folder.set(folder)

    def start_session(self):
        if self.running:
            messagebox.showinfo("Info", "Session already running!")
            return
        self.create_session_folder()
        self.start_watching()

    def new_session(self):
        if not self.running:
            messagebox.showinfo("Info", "Start a session first.")
            return
        self.session_number.set(self.session_number.get() + 1)
        self.create_session_folder()
        self.log_message(f"Started new session: {self.active_session_folder}")

    def create_session_folder(self):
        session_index = str(self.session_number.get()).zfill(3)
        folder_name = f"{self.year.get()}-{self.project.get()}-{self.audit_type.get()}-{session_index}"
        self.active_session_folder = os.path.join(self.output_base_folder.get(), folder_name)
        os.makedirs(self.active_session_folder, exist_ok=True)
        self.current_session_label.config(text=f"Current Session: {folder_name}")
        self.log_message(f"Session folder created: {self.active_session_folder}")

    def start_watching(self):
        event_handler = ScreenshotHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.screenshot_folder.get(), recursive=False)
        self.observer.start()
        self.running = True
        self.log_message(f"Started watching: {self.screenshot_folder.get()}")

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.running = False
        self.log_message("Stopped watching.")

    def process_queue(self):
        while True:
            src_path = self.file_queue.get()
            if src_path:
                self.move_screenshot(src_path)
            self.file_queue.task_done()

    def move_screenshot(self, src_path):
        try:
            time.sleep(0.3)  # short delay for file completion
            if not os.path.exists(src_path):
                return
            filename = os.path.basename(src_path)
            dest_path = os.path.join(self.active_session_folder, filename)
            shutil.move(src_path, dest_path)
            self.log_message(f"Moved: {filename} → {self.active_session_folder}")
        except Exception as e:
            self.log_message(f"Error moving file: {e}")

def main():
    root = tk.Tk()
    app = ScreenshotOrganizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()




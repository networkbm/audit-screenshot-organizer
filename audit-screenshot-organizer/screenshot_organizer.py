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


def ensure_unique_path(dest_path: str) -> str:
    if not os.path.exists(dest_path):
        return dest_path
    base, ext = os.path.splitext(dest_path)
    i = 1
    while True:
        candidate = f"{base} ({i}){ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


def open_folder(path: str):
    if not path or not os.path.isdir(path):
        return
    sysname = platform.system()
    if sysname == "Darwin":
        subprocess.run(["open", path], check=False)
    elif sysname == "Windows":
        os.startfile(path)
    else:
        subprocess.run(["xdg-open", path], check=False)


def can_use_imagegrab() -> bool:
    try:
        from PIL import ImageGrab
        return True
    except Exception:
        return False


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if event.is_directory:
            return
        filename = os.path.basename(event.src_path).lower()
        if filename.endswith(".png"):
            self.app.file_queue.put(event.src_path)


class MiniToolbar:
    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.geometry("600x64+220+120")
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
        status_label = tk.Label(bar, textvariable=self.status, bg=TOOLBAR_BG, fg=TOOLBAR_MUTED, font=("Arial", 10))
        status_label.pack(side="right", padx=(10, 0))

        def mkbtn(label, cmd):
            w = tk.Label(
                bar,
                text=label,
                bg=TOOLBAR_BTN_BG,
                fg=TOOLBAR_TEXT,
                padx=12,
                pady=7,
                font=("Arial", 11),
            )

            def enter(_):
                w.configure(bg=TOOLBAR_BTN_HOVER)

            def leave(_):
                w.configure(bg=TOOLBAR_BTN_BG)

            def down(_):
                w.configure(bg=TOOLBAR_BTN_ACTIVE)

            def up(e):
                w.configure(bg=TOOLBAR_BTN_HOVER)
                x, y = e.x, e.y
                if 0 <= x <= w.winfo_width() and 0 <= y <= w.winfo_height():
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

        for w in (self.win, outer, status_label):
            w.bind("<ButtonPress-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)

        self.win.bind("<Escape>", lambda e: self.hide())

    def start_move(self, e):
        self._x = e.x_root - self.win.winfo_x()
        self._y = e.y_root - self.win.winfo_y()

    def do_move(self, e):
        x = e.x_root - self._x
        y = e.y_root - self._y
        self.win.geometry(f"+{x}+{y}")

    def show(self):
        self.win.deiconify()
        self.win.lift()
        self.app.on_toolbar_visibility_changed(True)

    def hide(self):
        self.win.withdraw()
        self.app.on_toolbar_visibility_changed(False)

    def is_visible(self):
        try:
            return str(self.win.state()) != "withdrawn"
        except Exception:
            return False

    def set_status(self, s: str):
        self.status.set(s)

    def open_current_folder(self):
        self.app.ensure_session()
        open_folder(self.app.active_session_folder)

    def _run_screencapture(self, args, out_path):
        try:
            res = subprocess.run(args, capture_output=True, text=True)
            ok = os.path.exists(out_path) and os.path.getsize(out_path) > 0 and res.returncode == 0
            if ok:
                self.app.ui_log(f"Saved: {os.path.basename(out_path)}")
                self.app.root.after(0, lambda: self.set_status("Saved"))
                return

            stderr = (res.stderr or "").strip()
            if os.path.exists(out_path) and os.path.getsize(out_path) == 0:
                try:
                    os.remove(out_path)
                except Exception:
                    pass

            if stderr:
                self.app.ui_log(f"Capture failed: {stderr}")
            else:
                self.app.ui_log("Capture failed.")
            self.app.root.after(0, lambda: self.set_status("Failed"))
        except Exception as e:
            self.app.ui_log(f"Capture error: {e}")
            self.app.root.after(0, lambda: self.set_status("Failed"))

    def capture_region(self):
        self.app.ensure_session()
        out_path = ensure_unique_path(os.path.join(self.app.active_session_folder, f"{self.app.timestamp()}_region.png"))

        if platform.system() == "Darwin":
            self.set_status("Select region…")
            threading.Thread(
                target=self._run_screencapture,
                args=(["screencapture", "-i", "-x", out_path], out_path),
                daemon=True,
            ).start()
            return

        if not can_use_imagegrab():
            self.app.ui_log("Region capture requires Pillow. Install with: pip install pillow")
            self.set_status("Failed")
            return

        self.set_status("Select region…")
        self.hide()
        self.app.root.after(120, lambda: self._windows_region_overlay(out_path))

    def _windows_region_overlay(self, out_path):
        overlay = tk.Toplevel(self.app.root)
        overlay.attributes("-topmost", True)
        overlay.overrideredirect(True)
        try:
            overlay.attributes("-alpha", 0.18)
        except Exception:
            pass
        overlay.configure(bg="black")

        sw = overlay.winfo_screenwidth()
        sh = overlay.winfo_screenheight()
        overlay.geometry(f"{sw}x{sh}+0+0")

        canvas = tk.Canvas(overlay, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        state = {"x0": 0, "y0": 0, "rect": None}

        def down(e):
            state["x0"], state["y0"] = e.x, e.y
            if state["rect"]:
                canvas.delete(state["rect"])
            state["rect"] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="white", width=2)

        def move(e):
            if not state["rect"]:
                return
            canvas.coords(state["rect"], state["x0"], state["y0"], e.x, e.y)

        def cancel():
            try:
                overlay.destroy()
            except Exception:
                pass
            self.set_status("Ready")
            self.show()

        def up(e):
            x1, y1 = e.x, e.y
            x0, y0 = state["x0"], state["y0"]
            left = min(x0, x1)
            top = min(y0, y1)
            right = max(x0, x1)
            bottom = max(y0, y1)

            overlay.destroy()

            if right - left < 5 or bottom - top < 5:
                self.app.ui_log("Region capture cancelled.")
                self.set_status("Ready")
                self.show()
                return

            def do_grab():
                try:
                    from PIL import ImageGrab
                    img = ImageGrab.grab(bbox=(left, top, right, bottom))
                    img.save(out_path, "PNG")
                    ok = os.path.exists(out_path) and os.path.getsize(out_path) > 0
                    if ok:
                        self.app.ui_log(f"Saved: {os.path.basename(out_path)}")
                        self.app.root.after(0, lambda: self.set_status("Saved"))
                    else:
                        self.app.ui_log("Capture failed.")
                        self.app.root.after(0, lambda: self.set_status("Failed"))
                except Exception as ex:
                    self.app.ui_log(f"Capture error: {ex}")
                    self.app.root.after(0, lambda: self.set_status("Failed"))
                finally:
                    self.app.root.after(0, self.show)

            threading.Thread(target=do_grab, daemon=True).start()

        overlay.bind("<Escape>", lambda _e: cancel())
        canvas.bind("<ButtonPress-1>", down)
        canvas.bind("<B1-Motion>", move)
        canvas.bind("<ButtonRelease-1>", up)

    def capture_full(self):
        self.app.ensure_session()
        out_path = ensure_unique_path(os.path.join(self.app.active_session_folder, f"{self.app.timestamp()}_full.png"))

        if platform.system() == "Darwin":
            self.set_status("Capturing…")
            threading.Thread(
                target=self._run_screencapture,
                args=(["screencapture", "-x", out_path], out_path),
                daemon=True,
            ).start()
            return

        if not can_use_imagegrab():
            self.app.ui_log("Full screen capture requires Pillow. Install with: pip install pillow")
            self.set_status("Failed")
            return

        self.set_status("Capturing…")

        def do_full():
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(out_path, "PNG")
                ok = os.path.exists(out_path) and os.path.getsize(out_path) > 0
                if ok:
                    self.app.ui_log(f"Saved: {os.path.basename(out_path)}")
                    self.app.root.after(0, lambda: self.set_status("Saved"))
                else:
                    self.app.ui_log("Capture failed.")
                    self.app.root.after(0, lambda: self.set_status("Failed"))
            except Exception as ex:
                self.app.ui_log(f"Full capture error: {ex}")
                self.app.root.after(0, lambda: self.set_status("Failed"))

        threading.Thread(target=do_full, daemon=True).start()


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

        self.mode = tk.StringVar(value="manual")
        self.pw_url = tk.StringVar(value="https://example.com")
        self.pw_fullpage = tk.BooleanVar(value=True)
        self.pw_selector = tk.StringVar(value="")

        self.active_session_folder = ""
        self.observer = None
        self.running = False
        self.toolbar = None
        self.toolbar_visible = False

        self.file_queue = queue.Queue()
        self.ui_log_queue = queue.Queue()

        threading.Thread(target=self.process_queue, daemon=True).start()

        self.setup_style()
        self.build_scrollable_root()
        self.build_gui(self.content)

        self.root.after(60, self.pump_ui_logs)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)

        style.configure("TLabel", background=PANEL, foreground=TEXT)
        style.configure("Root.TLabel", background=BG, foreground=TEXT)
        style.configure("MutedRoot.TLabel", background=BG, foreground=MUTED)

        style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=ENTRY_FG, insertcolor=ENTRY_FG)

        style.configure("TButton", background=BTN_BG, foreground=TEXT, padding=8, borderwidth=0)
        style.map(
            "TButton",
            background=[("active", BTN_HOVER), ("pressed", BTN_ACTIVE)],
            foreground=[("active", TEXT), ("pressed", TEXT)],
        )

        style.configure("TRadiobutton", background=BG, foreground=TEXT)
        style.map("TRadiobutton", foreground=[("active", TEXT)])

        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.map("TCheckbutton", foreground=[("active", TEXT)])

    def build_scrollable_root(self):
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.canvas, bg=BG)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        def on_configure(_):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def on_canvas_configure(event):
            self.canvas.itemconfig(self.window_id, width=event.width)

        self.content.bind("<Configure>", on_configure)
        self.canvas.bind("<Configure>", on_canvas_configure)

        self._wheel_bound = False

        def bind_wheel(_):
            if self._wheel_bound:
                return
            self._wheel_bound = True
            sysname = platform.system()
            if sysname == "Linux":
                self.canvas.bind_all("<Button-4>", self._on_linux_wheel_up)
                self.canvas.bind_all("<Button-5>", self._on_linux_wheel_down)
            else:
                self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        def unbind_wheel(_):
            if not self._wheel_bound:
                return
            self._wheel_bound = False
            sysname = platform.system()
            if sysname == "Linux":
                self.canvas.unbind_all("<Button-4>")
                self.canvas.unbind_all("<Button-5>")
            else:
                self.canvas.unbind_all("<MouseWheel>")

        self.canvas.bind("<Enter>", bind_wheel)
        self.canvas.bind("<Leave>", unbind_wheel)

    def _at_top(self):
        first, _ = self.canvas.yview()
        return first <= 0.0

    def _at_bottom(self):
        _, last = self.canvas.yview()
        return last >= 1.0

    def _scroll_units(self, units: int):
        if units < 0 and self._at_top():
            return
        if units > 0 and self._at_bottom():
            return
        self.canvas.yview_scroll(units, "units")

    def _on_mousewheel(self, event):
        sysname = platform.system()
        if sysname == "Darwin":
            if event.delta == 0:
                return
            units = 1 if event.delta < 0 else -1
            self._scroll_units(units)
        else:
            if event.delta == 0:
                return
            units = int(-1 * (event.delta / 120))
            if units == 0:
                units = 1 if event.delta < 0 else -1
            self._scroll_units(units)

    def _on_linux_wheel_up(self, _):
        self._scroll_units(-1)

    def _on_linux_wheel_down(self, _):
        self._scroll_units(1)

    def build_gui(self, outer):
        top_panel = ttk.Frame(outer, style="Panel.TFrame")
        top_panel.pack(fill="x", pady=(14, 12), padx=14)

        def add_row(r, label, var, col):
            ttk.Label(top_panel, text=label, style="TLabel").grid(row=r, column=col, sticky="w", padx=10, pady=8)
            e = ttk.Entry(top_panel, textvariable=var)
            e.grid(row=r, column=col + 1, sticky="w", padx=10, pady=8)
            return e

        add_row(0, "Year:", self.year, 0)
        add_row(0, "Project:", self.project, 2)
        add_row(1, "Audit Type:", self.audit_type, 0)
        add_row(1, "Start Index:", self.session_number, 2)

        ttk.Label(top_panel, text="Screenshot Folder (Source):", style="TLabel").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(top_panel, textvariable=self.screenshot_folder, width=46).grid(row=2, column=1, sticky="w", padx=10, pady=8, columnspan=2)
        ttk.Button(top_panel, text="Browse", command=self.select_screenshot_folder).grid(row=2, column=3, sticky="w", padx=10, pady=8)

        ttk.Label(top_panel, text="Output Folder (Destination):", style="TLabel").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(top_panel, textvariable=self.output_base_folder, width=46).grid(row=3, column=1, sticky="w", padx=10, pady=8, columnspan=2)
        ttk.Button(top_panel, text="Browse", command=self.select_output_folder).grid(row=3, column=3, sticky="w", padx=10, pady=8)

        mode_frame = tk.Frame(outer, bg=BG)
        mode_frame.pack(fill="x", pady=(0, 8), padx=14)

        ttk.Label(mode_frame, text="Mode:", style="Root.TLabel").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Manual (Watch folder)", variable=self.mode, value="manual", command=self.on_mode_change).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(mode_frame, text="Playwright (Website capture)", variable=self.mode, value="playwright", command=self.on_mode_change).pack(side="left", padx=(0, 14))

        self.pw_frame = tk.Frame(outer, bg=BG)
        ttk.Label(self.pw_frame, text="URL:", style="Root.TLabel").grid(row=0, column=0, sticky="w", padx=0, pady=6)
        ttk.Entry(self.pw_frame, textvariable=self.pw_url, width=58).grid(row=0, column=1, sticky="w", padx=10, pady=6)
        ttk.Button(self.pw_frame, text="Capture Now", command=self.capture_now).grid(row=0, column=2, sticky="w", padx=10, pady=6)
        ttk.Checkbutton(self.pw_frame, text="Full page", variable=self.pw_fullpage).grid(row=1, column=1, sticky="w", padx=10, pady=4)
        ttk.Label(self.pw_frame, text="Element selector (optional):", style="Root.TLabel").grid(row=2, column=0, sticky="w", padx=0, pady=6)
        ttk.Entry(self.pw_frame, textvariable=self.pw_selector, width=34).grid(row=2, column=1, sticky="w", padx=10, pady=6)

        button_frame = tk.Frame(outer, bg=BG)
        button_frame.pack(fill="x", pady=(8, 10), padx=14)

        ttk.Button(button_frame, text="Start Session", command=self.start_session).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="New Session", command=self.new_session).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Stop Watching", command=self.stop_watching).pack(side="left", padx=(0, 10))

        self.toggle_toolbar_btn = ttk.Button(button_frame, text="Show Mini Toolbar", command=self.toggle_toolbar)
        self.toggle_toolbar_btn.pack(side="left", padx=(0, 10))

        ttk.Button(button_frame, text="Open Session Folder", command=self.open_session_folder).pack(side="left")

        self.current_session_label = tk.Label(outer, text="Current Session: None", bg=BG, fg=MUTED, font=("Arial", 12))
        self.current_session_label.pack(pady=(0, 10), anchor="w", padx=14)

        self.log = tk.Text(
            outer,
            bg=LOG_BG,
            fg=LOG_FG,
            wrap="word",
            height=10,
            bd=0,
            highlightthickness=1,
            highlightbackground="#232733",
            insertbackground=TEXT,
        )
        self.log.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.on_mode_change()

    def on_mode_change(self):
        self.pw_frame.pack_forget()
        if self.mode.get() == "playwright":
            if self.running:
                self.stop_watching()
            self.pw_frame.pack(fill="x", pady=(0, 6), padx=14)

    def on_toolbar_visibility_changed(self, visible: bool):
        self.toolbar_visible = visible
        if hasattr(self, "toggle_toolbar_btn"):
            self.toggle_toolbar_btn.config(text="Hide Mini Toolbar" if visible else "Show Mini Toolbar")

    def toggle_toolbar(self):
        if not self.toolbar:
            self.toolbar = MiniToolbar(self)
        if self.toolbar.is_visible():
            self.toolbar.hide()
        else:
            self.toolbar.show()

    def ui_log(self, message: str):
        self.ui_log_queue.put(message)

    def pump_ui_logs(self):
        drained = 0
        try:
            while drained < 50:
                msg = self.ui_log_queue.get_nowait()
                self.log.insert(tk.END, f"{msg}\n")
                self.log.see(tk.END)
                drained += 1
        except queue.Empty:
            pass
        self.root.after(60, self.pump_ui_logs)

    def select_screenshot_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.screenshot_folder.set(folder)

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_base_folder.set(folder)

    def ensure_session(self):
        if not self.active_session_folder:
            self.create_session_folder()

    def start_session(self):
        if self.mode.get() == "manual" and self.running:
            messagebox.showinfo("Info", "Session already running!")
            return
        self.create_session_folder()
        if self.mode.get() == "manual":
            self.start_watching()
        else:
            self.ui_log("Playwright mode ready. Click 'Capture Now' when you want screenshots.")

    def new_session(self):
        self.session_number.set(self.session_number.get() + 1)
        self.create_session_folder()
        self.ui_log(f"Started new session: {self.active_session_folder}")

    def create_session_folder(self):
        session_index = str(self.session_number.get()).zfill(3)
        folder_name = f"{self.year.get()}-{self.project.get()}-{self.audit_type.get()}-{session_index}"
        self.active_session_folder = os.path.join(self.output_base_folder.get(), folder_name)
        os.makedirs(self.active_session_folder, exist_ok=True)
        self.current_session_label.config(text=f"Current Session: {folder_name}")
        self.ui_log(f"Session folder created: {self.active_session_folder}")

    def start_watching(self):
        watch_path = self.screenshot_folder.get()
        if not os.path.isdir(watch_path):
            messagebox.showerror("Error", f"Source folder not found:\n{watch_path}")
            return
        event_handler = ScreenshotHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, watch_path, recursive=False)
        self.observer.start()
        self.running = True
        self.ui_log(f"Started watching: {watch_path}")

    def stop_watching(self):
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=3)
            except Exception:
                pass
            self.observer = None
        if self.running:
            self.ui_log("Stopped watching.")
        self.running = False

    def process_queue(self):
        while True:
            src_path = self.file_queue.get()
            try:
                if src_path:
                    self.move_screenshot_with_retries(src_path)
            finally:
                self.file_queue.task_done()

    def move_screenshot_with_retries(self, src_path: str, retries: int = 12, delay: float = 0.25):
        for _ in range(retries):
            if not os.path.exists(src_path):
                return
            if not self.active_session_folder:
                self.ui_log("No active session. Start a session first.")
                return

            filename = os.path.basename(src_path)
            dest_path = ensure_unique_path(os.path.join(self.active_session_folder, filename))

            try:
                shutil.move(src_path, dest_path)
                self.ui_log(f"Moved: {os.path.basename(dest_path)} → {self.active_session_folder}")
                return
            except PermissionError:
                time.sleep(delay)
            except Exception as e:
                self.ui_log(f"Error moving file: {e}")
                return

        self.ui_log(f"Skipped (file still locked): {os.path.basename(src_path)}")

    def timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def safe_name(self, s: str) -> str:
        s = s.strip()
        s = re.sub(r"[^\w\-\.]+", "_", s)
        return s[:80] if len(s) > 80 else s

    def capture_now(self):
        self.ensure_session()
        threading.Thread(target=self.run_playwright_capture, daemon=True).start()

    def run_playwright_capture(self):
        try:
            from playwright.sync_api import sync_playwright

            url = self.pw_url.get().strip()
            if not url:
                self.ui_log("Playwright: URL is empty.")
                return

            fullpage = bool(self.pw_fullpage.get())
            selector = self.pw_selector.get().strip()

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)

                if fullpage:
                    fp_path = ensure_unique_path(os.path.join(self.active_session_folder, f"{self.timestamp()}_fullpage.png"))
                    page.screenshot(path=fp_path, full_page=True)
                    self.ui_log(f"Saved: {os.path.basename(fp_path)}")

                if selector:
                    el_path = ensure_unique_path(
                        os.path.join(self.active_session_folder, f"{self.timestamp()}_element_{self.safe_name(selector)}.png")
                    )
                    page.locator(selector).first.screenshot(path=el_path)
                    self.ui_log(f"Saved: {os.path.basename(el_path)}")

                browser.close()

        except Exception as e:
            self.ui_log(f"Playwright error: {e}")

    def open_session_folder(self):
        self.ensure_session()
        open_folder(self.active_session_folder)

    def on_close(self):
        if self.running:
            self.stop_watching()
        self.root.destroy()


def main():
    root = tk.Tk()
    ScreenshotOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

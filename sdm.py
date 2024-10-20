import os
import threading
import requests
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar  # Calendar widget for date selection
from time import sleep, time, strftime
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import pyperclip  # Clipboard handling
import re  # For URL validation
import sched  # For scheduling downloads
import logging  # For logging download activities

# Constants
CHUNK_SIZE = 1024 * 1024  # 1 MB default
NUM_THREADS = 8  # Default number of threads
DEFAULT_RETRY_INTERVAL = 30  # Retry interval in seconds
DEFAULT_SPEED_LIMIT = 0  # No speed limit by default

# Scheduler
scheduler = sched.scheduler(time, sleep)

# Initialize logging
logging.basicConfig(filename='download_manager.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

# Bandwidth usage
current_bandwidth = 0  # Bandwidth usage in MB/s

# Validate the URL
def is_valid_url(url):
    regex = re.compile(
        r'^(http|https)://'  # http:// or https://
        r'([A-Za-z0-9.-]+)'  # domain name
        r'(\.[A-Za-z]{2,})'  # top-level domain
        r'(:\d+)?(/.*)?$'  # optional port and path
    )
    return re.match(regex, url) is not None

class DownloadTask:
    def __init__(self, url, dest_folder, filename=None, retries=3):
        self.url = url
        self.dest_folder = dest_folder
        self.filename = filename or os.path.basename(url)
        self.file_path = os.path.join(dest_folder, self.filename)
        self.total_size = 0
        self.downloaded_size = 0
        self.is_paused = False
        self.is_cancelled = False
        self.is_completed = False
        self.speed = 0  # Download speed in MB/s
        self.time_left = "Calculating..."  # Time left for download
        self.retry_count = 0
        self.max_retries = retries
        self.file_handle = None
        self.start_time = 0
        self.download_speed_limit = DEFAULT_SPEED_LIMIT
        self.scheduler_time = None  # Time for scheduled downloads
        self.threads = []  # Initialize an empty list to track threads

    def start(self):
        """Starts the download."""
        try:
            logging.info(f"Starting download for {self.filename}")

            if not is_valid_url(self.url):
                raise ValueError(f"Invalid URL: {self.url}")

            # Get file size
            response = requests.head(self.url)
            self.total_size = int(response.headers.get('content-length', 0))

            # Open file in binary mode for writing
            self.file_handle = open(self.file_path, 'wb')

            self.start_time = time()  # Track when the download starts

            # Download using multiple threads (chunked download)
            with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
                futures = []
                chunk_size = self.total_size // NUM_THREADS  # Divide into chunks

                for i in range(NUM_THREADS):
                    start = i * chunk_size
                    end = start + chunk_size if i < NUM_THREADS - 1 else self.total_size
                    futures.append(executor.submit(self.download_chunk, start, end))

                for future in futures:
                    future.result()  # Wait for all threads to finish

            if self.downloaded_size >= self.total_size:
                self.is_completed = True
                update_gui(self, status="Completed")
                logging.info(f"Download completed for {self.filename}")
                check_if_all_downloads_completed()  # Check if we should close the app

        except Exception as e:
            logging.error(f"Error downloading {self.filename}: {e}")
            self.retry_or_fail()

        finally:
            if self.file_handle:
                self.file_handle.close()  # Ensure file handle is closed

    def download_chunk(self, start, end):
        """Download a chunk of the file."""
        headers = {'Range': f'bytes={start}-{end - 1}'}

        with requests.get(self.url, headers=headers, stream=True) as response:
            self.file_handle.seek(start)
            for chunk in response.iter_content(CHUNK_SIZE):
                if self.is_cancelled:
                    return  # Exit if canceled
                while self.is_paused:
                    sleep(1)  # Sleep while paused
                self.file_handle.write(chunk)
                self.downloaded_size += len(chunk)
                elapsed_time = time() - self.start_time
                self.speed = self.downloaded_size / (elapsed_time * 1024 * 1024)  # Speed in MB/s
                if self.download_speed_limit > 0:
                    self.speed = min(self.speed, self.download_speed_limit)
                self.time_left = self.calculate_time_left()
                update_gui(self, status="Downloading")

    def retry_or_fail(self):
        """Retry the download or fail after max retries."""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            logging.info(f"Retrying download for {self.filename}, attempt {self.retry_count}")
            root.after(DEFAULT_RETRY_INTERVAL * 1000, lambda: self.start())  # Retry after interval
        else:
            update_gui(self, status="Error")
            messagebox.showerror("Error", f"Failed to download {self.filename} after {self.max_retries} retries.")

    def pause(self):
        """Pauses the download."""
        self.is_paused = True
        update_gui(self, status="Paused")

    def resume(self):
        """Resumes the download."""
        if self.is_paused:
            self.is_paused = False
            update_gui(self, status="Downloading")
            threading.Thread(target=self.start).start()  # Resume in a new thread

    def cancel(self):
        """Cancels the download and removes the file."""
        self.is_cancelled = True  # Set the flag to cancel download
        logging.info(f"Download canceled for {self.filename}")

        # Wait briefly to allow threads to stop
        sleep(1)

        try:
            # Close the file handle if it is open
            if self.file_handle and not self.file_handle.closed:
                self.file_handle.close()

            # Once cancellation is confirmed, remove the file
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            remove_task_from_gui(self)  # Remove the task from the GUI
        except PermissionError as e:
            update_gui(self, status="Error")
            messagebox.showerror("Error", f"Error canceling {self.filename}: {e}")

    def calculate_time_left(self):
        """Calculate time left for download completion."""
        if self.speed > 0:
            remaining_size = (self.total_size - self.downloaded_size) / (1024 * 1024)  # Remaining size in MB
            time_left = remaining_size / self.speed  # Time left in seconds
            return f"{int(time_left // 60)} min {int(time_left % 60)} sec"
        return "Calculating..."

    def schedule(self, schedule_time):
        """Schedule the download to start at a later time."""
        self.scheduler_time = schedule_time
        delay = (schedule_time - datetime.now()).total_seconds()
        logging.info(f"Scheduling download for {self.filename} at {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}")
        scheduler.enter(delay, 1, lambda: self.start())
        scheduler.run()


# GUI Update Function
def update_gui(task, status):
    index = task_list.index(task)
    progress = (task.downloaded_size / task.total_size) * 100 if task.total_size else 0
    progress_bars[index]['value'] = progress  # Update progress bar
    progress_labels[index].config(text=f"{progress:.2f}%")
    status_labels[index].config(text=status)
    if task.speed > 0:
        speed_labels[index].config(text=f"{task.speed:.2f} MB/s")
    time_left_labels[index].config(text=task.time_left)  # Show time left

# Function to check if all downloads are completed
def check_if_all_downloads_completed():
    if all(task.is_completed for task in task_list):
        if close_on_complete.get():
            root.after(1000, root.quit)  # Close after 1 second if the option is enabled

# Function to start download in a new thread
def download_thread(task):
    if task.total_size == 0:
        response = requests.head(task.url)
        content_length = response.headers.get('content-length', 0)
        if content_length:
            task.total_size = int(content_length)

    if task.total_size > 0:
        task.start()

# Add a new download with the Add Download Window
def open_add_download_window():
    add_window = tk.Toplevel(root)
    add_window.title("Add Download")
    add_window.geometry("450x550")
    
    # Ensure the add window stays on top of the main window
    add_window.transient(root)
    add_window.grab_set()

    # Toggle scheduler display based on checkbox
    def toggle_scheduler_display():
        if schedule_checkbox.get():
            cal.pack(pady=10)
            tk.Label(add_window, text="Choose Time:").pack(pady=5)
            time_box.pack(pady=5)
        else:
            cal.pack_forget()
            time_box.pack_forget()

    # Create Date Picker for scheduling
    cal = Calendar(add_window, selectmode="day", date_pattern="mm/dd/yy")
    cal.pack_forget()  # Initially hidden
    
    tk.Label(add_window, text="Choose Time:").pack_forget()
    time_box = ttk.Combobox(add_window, values=[f"{i:02d}:00" for i in range(24)], width=5)
    time_box.current(0)
    time_box.pack_forget()
    
    schedule_checkbox = tk.BooleanVar()
    tk.Checkbutton(add_window, text="Schedule Download", variable=schedule_checkbox, command=toggle_scheduler_display).pack()

    # URL entry field
    tk.Label(add_window, text="Download URL:").pack(pady=5)
    url_entry = tk.Entry(add_window, width=50)
    url_entry.pack(pady=5)
    
    # Auto paste from clipboard
    clipboard_url = pyperclip.paste()
    if is_valid_url(clipboard_url):
        url_entry.insert(0, clipboard_url)  # Automatically paste clipboard if valid URL

    # Browse location
    tk.Label(add_window, text="Save to Folder:").pack(pady=5)
    folder_entry = tk.Entry(add_window, width=50)
    folder_entry.pack(pady=5)
    
    browse_button = tk.Button(add_window, text="Browse", command=lambda: browse_folder(folder_entry))
    browse_button.pack(pady=5)

    # Add Download Button
    def add_download():
        url = url_entry.get()
        dest_folder = folder_entry.get() or os.path.join(os.getcwd(), "Downloads")
        if not url or not is_valid_url(url):
            messagebox.showwarning("Input Error", "Please enter a valid URL!")
            return
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)  # Create the folder if it doesn't exist

        task = DownloadTask(url, dest_folder)
        task_list.append(task)
        index = len(task_list) - 1
        add_download_row(index, task)

        if schedule_checkbox.get():
            date_str = cal.get_date()  # Get selected date from the calendar
            time_str = time_box.get()  # Get selected time from dropdown
            schedule_time = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%y %H:%M")
            task.schedule(schedule_time)  # Set up scheduling
        else:
            thread = threading.Thread(target=download_thread, args=(task,))
            task.threads.append(thread)  # Track the thread
            thread.start()

        add_window.destroy()  # Close the add download window

    add_button = tk.Button(add_window, text="Start Download", command=add_download)
    add_button.pack(pady=10)

# Browse function to select folder
def browse_folder(folder_entry):
    folder_selected = filedialog.askdirectory()
    folder_entry.delete(0, tk.END)
    folder_entry.insert(0, folder_selected)

# Add a new download row in the main UI
def add_download_row(index, task):
    row = index + 2

    # Create a frame to hold each row's content
    row_frame = tk.Frame(root)
    row_frame.grid(row=row, column=0, columnspan=8, padx=5, pady=5, sticky="w")

    file_name_label = tk.Label(row_frame, text=task.filename, width=30, anchor="w")
    file_name_label.grid(row=0, column=0)

    progress_bar = ttk.Progressbar(row_frame, length=200)
    progress_bar.grid(row=0, column=1)
    progress_bars.append(progress_bar)

    progress_label = tk.Label(row_frame, text="0.00%", width=10, anchor="e")
    progress_label.grid(row=0, column=2)
    progress_labels.append(progress_label)

    status_label = tk.Label(row_frame, text="Waiting", width=10, anchor="e")
    status_label.grid(row=0, column=3)
    status_labels.append(status_label)

    speed_label = tk.Label(row_frame, text="0 MB/s", width=10, anchor="e")
    speed_label.grid(row=0, column=4)
    speed_labels.append(speed_label)

    time_left_label = tk.Label(row_frame, text="Calculating...", width=15, anchor="e")
    time_left_label.grid(row=0, column=5)
    time_left_labels.append(time_left_label)

    pause_button = tk.Button(row_frame, text="Pause", command=lambda: task.pause(), width=7)
    pause_button.grid(row=0, column=6)

    resume_button = tk.Button(row_frame, text="Resume", command=lambda: task.resume(), width=7)
    resume_button.grid(row=0, column=7)

    cancel_button = tk.Button(row_frame, text="Cancel", command=lambda: task.cancel(), width=7)
    cancel_button.grid(row=0, column=8)

# Function to remove a task from the GUI
def remove_task_from_gui(task):
    index = task_list.index(task)
    task_list.remove(task)
    progress_bars.pop(index)
    progress_labels.pop(index)
    status_labels.pop(index)
    speed_labels.pop(index)
    time_left_labels.pop(index)
    refresh_gui()

# Refresh the GUI after removing a task
def refresh_gui():
    for widget in root.grid_slaves():
        if int(widget.grid_info()["row"]) > 1:
            widget.grid_forget()

    for index, task in enumerate(task_list):
        add_download_row(index, task)

# Pause All and Resume All Functions
def pause_all_downloads():
    for task in task_list:
        task.pause()

def resume_all_downloads():
    for task in task_list:
        task.resume()

# View Logs Function
def view_logs():
    log_window = tk.Toplevel(root)
    log_window.title("Download Logs")
    log_window.geometry("500x300")

    with open('download_manager.log', 'r') as log_file:
        log_data = log_file.read()

    log_text = tk.Text(log_window, wrap="word")
    log_text.insert(tk.END, log_data)
    log_text.config(state=tk.DISABLED)  # Make the log read-only
    log_text.pack(fill="both", expand=True)

# Settings menu
def open_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("300x200")

    close_checkbox = tk.Checkbutton(
        settings_window,
        text="Close when downloads complete",
        variable=close_on_complete
    )
    close_checkbox.pack(pady=10)

    # Speed limit option
    tk.Label(settings_window, text="Set Speed Limit (MB/s)").pack(pady=5)
    speed_limit_entry = tk.Entry(settings_window)
    speed_limit_entry.pack(pady=5)

    def set_speed_limit():
        try:
            speed_limit = int(speed_limit_entry.get())
            if speed_limit >= 0:
                global DEFAULT_SPEED_LIMIT
                DEFAULT_SPEED_LIMIT = speed_limit
                logging.info(f"Speed limit set to {speed_limit} MB/s")
            else:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive integer for the speed limit.")
    
    tk.Button(settings_window, text="Set Speed Limit", command=set_speed_limit).pack(pady=10)

# Create the main window
root = tk.Tk()
root.title("SlowDownloadManager")
root.geometry("1000x600")  # Increased height to fit all elements properly

# Initialize the BooleanVar after root window is created
close_on_complete = tk.BooleanVar(value=False)  # Option to close on download completion

# Add menu bar for settings
menu_bar = tk.Menu(root)
settings_menu = tk.Menu(menu_bar, tearoff=0)
settings_menu.add_command(label="Settings", command=open_settings)
settings_menu.add_command(label="View Logs", command=view_logs)
menu_bar.add_cascade(label="Options", menu=settings_menu)
root.config(menu=menu_bar)

# Pause and Resume All buttons
pause_all_button = tk.Button(root, text="Pause All", command=pause_all_downloads)
pause_all_button.grid(row=0, column=1, padx=10, pady=10, sticky="w")

resume_all_button = tk.Button(root, text="Resume All", command=resume_all_downloads)
resume_all_button.grid(row=0, column=2, padx=10, pady=10, sticky="w")

# Remove the "Ready" text (status bar removed completely)

# Download tasks and their respective progress indicators
task_list = []
progress_bars = []
progress_labels = []
status_labels = []
speed_labels = []
time_left_labels = []

# Add "+" button for opening the add download window
add_download_button = tk.Button(root, text="+", font=("Arial", 14), command=open_add_download_window)
add_download_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")

# Run the application
root.mainloop()

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import os
import tempfile
import subprocess
import threading
from PIL import Image, ImageTk

# URL of the GitHub raw file for the main program script
GITHUB_RAW_URL = 'https://raw.githubusercontent.com/Electro0000/KindaBadLauncher/refs/heads/main/CG2/old.py'

# Function to download the file using multithreading
def download_and_save_script(download_dir, progress, status_label):
    try:
        # Update UI to show downloading status
        status_label.config(text="Downloading script...")
        progress.start()

        # Efficient download using multithreading
        response = requests.get(GITHUB_RAW_URL, stream=True)
        response.raise_for_status()

        # Download to user-chosen directory
        script_filename = os.path.join(download_dir, 'old.py')
        total_size = int(response.headers.get('content-length', 0))
        chunk_size = 1024  # 1 KB per chunk

        # Write to file in chunks for efficiency
        with open(script_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        # Notify the user
        messagebox.showinfo("Success", f"Script downloaded successfully to {download_dir}!")

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Failed to download the script: {e}")
    finally:
        # Reset progress bar and status
        progress.stop()
        status_label.config(text="Ready to download.")

# Thread wrapper to keep UI responsive
def start_download(progress, status_label):
    # Ask user to select directory
    download_dir = filedialog.askdirectory()
    if not download_dir:
        messagebox.showerror("Error", "No directory selected. Please select a valid directory.")
        return

    # Start the download in a separate thread
    threading.Thread(target=download_and_save_script, args=(download_dir, progress, status_label)).start()

# Function to initialize and run the GUI
def create_gui():
    # Initialize the main window
    root = tk.Tk()
    root.title("Program Downloader")
    root.geometry("500x400")
    root.resizable(False, False)

    # Title label
    title_label = tk.Label(root, text="Download Script from GitHub", font=("Arial", 16))
    title_label.pack(pady=20)

    # Load and display image
    img = Image.open("program_image.png")  # You need to provide an image called 'program_image.png'
    img = img.resize((200, 200), Image.ANTIALIAS)
    program_image = ImageTk.PhotoImage(img)
    image_label = tk.Label(root, image=program_image)
    image_label.pack(pady=10)

    # Program name label
    program_name_label = tk.Label(root, text="Program: Old Script", font=("Arial", 14))
    program_name_label.pack(pady=10)

    # Status label
    status_label = tk.Label(root, text="Ready to download.", font=("Arial", 10))
    status_label.pack(pady=10)

    # Progress bar
    progress = ttk.Progressbar(root, orient="horizontal", mode="indeterminate", length=300)
    progress.pack(pady=10)

    # Download button
    download_button = tk.Button(root, text="Download Script", font=("Arial", 12), width=15, height=2, 
                                command=lambda: start_download(progress, status_label))
    download_button.pack(pady=20)

    # Start the main GUI loop
    root.mainloop()

if __name__ == '__main__':
    create_gui()

import tkinter as tk
from tkinter import messagebox
import requests
import os

# List of programs and their download links
programs = [
    {
        "name": "Program 1",
        "download_url": "https://example.com/program1.py"
    },
    {
        "name": "Program 2",
        "download_url": "https://example.com/program2.py"
    },
    {
        "name": "Program 3",
        "download_url": "https://example.com/program3.py"
    }
]

# Function to download the selected program
def download_program(program_name, download_url):
    try:
        response = requests.get(download_url)
        response.raise_for_status()
        
        # Save the downloaded program to the local directory
        file_name = os.path.basename(download_url)
        with open(file_name, 'wb') as file:
            file.write(response.content)
        
        messagebox.showinfo("Success", f"{program_name} downloaded successfully!")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Failed to download {program_name}: {e}")

# Function to handle program selection
def on_select(event):
    selected_program = listbox.get(listbox.curselection())
    for program in programs:
        if program['name'] == selected_program:
            download_program(selected_program, program['download_url'])

# Initialize the GUI
root = tk.Tk()
root.title("Program Downloader")

# Create a Listbox to display programs
listbox = tk.Listbox(root, width=50, height=10)
for program in programs:
    listbox.insert(tk.END, program['name'])
listbox.pack(pady=10)

# Bind the Listbox click event to the selection handler
listbox.bind("<<ListboxSelect>>", on_select)

# Start the GUI loop
root.mainloop()

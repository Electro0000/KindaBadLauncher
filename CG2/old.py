import tkinter as tk
from tkinter import filedialog, messagebox
import requests
from PIL import Image, ImageTk
from io import BytesIO
import base64  # Import base64 module

# Encoded URLs (replace with your encoded data)
programs = [
    {
        "name": "BeamNG.drive",
        "image_url": "encoded=cmbw5iclZ3bj9VZ2lmckdkTtFWZC9yY28iNv4WZvEWakVGcptWa39yZy9mLhlGZl1Warl2duQWYvxGc19yL6MHc0RHaobf",
        "download_url": "encodedL3AucHJvZ3JhbS5leGFtcGxlLmNvbS9leGFtcGxlLnB5obf"
    },
    {
        "name": "Program 2",
        "image_url": "encodedZ25wLmVnYW1pL29ubGluZS5leGFtcGxlLmNvbS9vbmxpbmUucG5nobf",
        "download_url": "encodedL3AucHJvZ3JhbS5leGFtcGxlLmNvbS9wcm9ncmFtMi5weW9ibg==obf"
    }
]

# Decoding function (reverse of the encoding)
def complex_decode(encoded_url):
    # Remove padding
    trimmed_url = encoded_url[len("encoded"):-len("obf")]
    
    # Reverse the string back to original
    reversed_url = trimmed_url[::-1]
    
    # Decode base64
    decoded_url = base64.b64decode(reversed_url).decode()
    
    return decoded_url

# Function to load and display the image from a decoded URL
def load_image_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        img_data = BytesIO(response.content)
        img = Image.open(img_data)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Error loading image: {e}")
        return None

# Function to download the selected program
def download_program(url, filename):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        messagebox.showinfo("Success", f"{filename} downloaded successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to download the file: {e}")

# Function to display the programs with images and download buttons
def show_programs():
    root = tk.Tk()
    root.title("Program Downloader")
    root.geometry("500x600")
    root.resizable(False, False)

    # Create a frame for each program
    for program in programs:
        program_name = program["name"]

        # Decode the image URL and load the image
        decoded_image_url = complex_decode(program["image_url"])
        image = load_image_from_url(decoded_image_url)

        # Decode the download URL
        decoded_download_url = complex_decode(program["download_url"])

        # Program Frame
        frame = tk.Frame(root, pady=10)
        frame.pack()

        # Program Image
        if image:
            img_label = tk.Label(frame, image=image)
            img_label.image = image  # Keep a reference
            img_label.pack()

        # Program Name
        label = tk.Label(frame, text=program_name, font=("Arial", 14))
        label.pack()

        # Download Button
        download_button = tk.Button(frame, text="Download", command=lambda u=decoded_download_url: download_program(u, f"{program_name}.py"))
        download_button.pack(pady=5)

    root.mainloop()

if __name__ == '__main__':
    show_programs()

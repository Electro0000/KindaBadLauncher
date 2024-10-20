import os
import subprocess
import sys
import urllib.request

# URL of your script on GitHub
SCRIPT_URL = "https://raw.githubusercontent.com/Electro0000/KindaBadLauncher/refs/heads/main/sdm.py"
SCRIPT_PATH = "sdm.py"

def download_script():
    """Download the latest version of the script from GitHub."""
    print("Downloading script from GitHub...")
    urllib.request.urlretrieve(SCRIPT_URL, SCRIPT_PATH)
    print(f"Downloaded script to {SCRIPT_PATH}")

def run_script():
    """Run the downloaded script."""
    print("Running script...")
    subprocess.run([sys.executable, SCRIPT_PATH])

if __name__ == "__main__":
    download_script()  # Download the latest version of the script
    run_script()  # Run the downloaded script

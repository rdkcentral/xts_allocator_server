import os
import sys
import subprocess
from pathlib import Path

def install_dependencies():
    """Install project dependencies."""
    if os.path.exists("requirements.txt"):
        print("Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("No requirements.txt found. Skipping dependency installation.")

def build_binary():
    """Build the project using PyInstaller."""
    script_name = "app.py"
    output_dir = "dist"
    binary_name = "xts_allocator"

    print("Building binary with PyInstaller...")
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",               # creates a single binary
        "--noconsole",             # hides the console (optional?)
        "--name", binary_name,     # sets the binary name
        "--distpath", output_dir,  # specifies the output directory
        script_name
    ]

    subprocess.check_call(pyinstaller_cmd)
    print(f"Build complete. Binary is located in the '{output_dir}' directory.")

def clean_up():
    """Clean up intermediate build files."""
    print("Cleaning up temporary build files...")
    build_dirs = ["build", "__pycache__"]
    spec_file = Path("xts_allocator.spec")  # PyInstaller generates a .spec file

    for directory in build_dirs:
        if Path(directory).exists():
            subprocess.run(["rm", "-rf", directory], check=True)

    if spec_file.exists():
        spec_file.unlink()

if __name__ == "__main__":
    print("Starting build process...")
    install_dependencies()
    build_binary()
    clean_up()
    print("Build process completed successfully!")

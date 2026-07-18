import sys
import os
import subprocess

def print_to_system_queue(printer_name, file_path):
    """
    Sends a standard file (PDF, PNG, etc.) to a normally registered 
    system printer queue over USB or Bluetooth.
    """
    # Check if the file actually exists before wasting time
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return False
        
    os_platform = sys.platform

    # ==========================================
    # WINDOWS SYSTEM QUEUE
    # ==========================================
    if os_platform == "win32":
        import win32api
        import win32print
        
        print(f"[Windows] Sending {file_path} to system queue for '{printer_name}'...")
        try:
            # ShellExecute acts exactly like right-clicking a file and clicking "Print"
            # '/d:"printer"' explicitly routes it to your Munbyn instead of the system default
            win32api.ShellExecute(0, "print", file_path, f'/d:"{printer_name}"', ".", 0)
            return True
        except Exception as e:
            print(f"Windows Print Error: {e}")
            return False

    # ==========================================
    # MACOS & UBUNTU (CUPS) SYSTEM QUEUE
    # ==========================================
    elif os_platform in ["darwin", "linux"]:
        print(f"[Unix/Linux] Pushing {file_path} to CUPS queue for '{printer_name}'...")
        try:
            # lp is the native command-line utility for the standard system print queue
            # -d specifies the exact printer queue name
            result = subprocess.run(["lp", "-d", printer_name, file_path], check=True, capture_output=True)
            print(result.stdout.decode().strip())
            return True
        except subprocess.CalledProcessError as e:
            print(f"Unix Print Error: {e.stderr.decode().strip()}")
            return False
            
    else:
        print(f"Unsupported Operating System: {os_platform}")
        return False

# ==========================================
# EXAMPLES FOR HOW TO RUN IT:
# ==========================================
if __name__ == "__main__":
    # 1. Put the EXACT name of the printer from your OS settings
    # Windows example: "MUNBYN RW403B"
    # Mac/Ubuntu example: "MUNBYN_RW403B" (Run 'lpstat -p' in terminal to check)
    PRINTER_NAME = "Munbyn RW403B-N(Bluetooth)" 
    
    # 2. Path to your 4x6 label file
    LABEL_FILE = "test_print.pdf" 
    
    # 3. Fire it off
    print_to_system_queue(PRINTER_NAME, LABEL_FILE)
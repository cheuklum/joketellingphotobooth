# Inside a Text DAT named 'print_worker'
import os
import glob
from datetime import datetime
import ctypes
from ctypes import wintypes
import subprocess
import win32api
import win32print
import time
from PIL import Image, ImageWin

def run_photobooth_sequence(full_path, printer_name):
	print("Text DAT sequence initiated...")
	
	# 1. Lock the cache
	op('cache1').par.active = 0
	
    # # This targets the native Windows Photo Printing wizard engine directly via command line,
    # # passing your specific printer name and bypassing the interactive prompt screens.
	# cmd = f'rundll32.exe C:\\Windows\\System32\\shimgvw.dll,ImageView_PrintTo "{full_path}" "{printer_name}"'
    
	# try:
	# 	subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
	# 	print("Print job dispatched completely silently!")
	# 	return True
	# except Exception as e:
	# 	print(f"System Print Error: {e}")
	# 	return False
		
	# Set up Windows Core Graphics (GDI) functions using ctypes
	gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
	user32 = ctypes.WinDLL('user32', use_last_error=True)

	# GDI Constants
	HORZRES = 8
	VERTRES = 10
	PHYSICALWIDTH = 110
	PHYSICALHEIGHT = 111

	try:
		# 1. Open the image natively in Python
		img = Image.open(full_path)
		
		# 2. Create the direct Printer Device Context (DC) handle without win32ui
		hdc = gdi32.CreateDCW("WINSPOOL", printer_name, None, None)
		if not hdc:
			print("Error: Could not create printer Device Context.")
			return False
			
		# 3. Pull physical label dimensions straight from your Munbyn driver
		printable_width = gdi32.GetDeviceCaps(hdc, PHYSICALWIDTH)
		printable_height = gdi32.GetDeviceCaps(hdc, PHYSICALHEIGHT)
		
		# 4. Initialize the Windows Spooler Doc Info structure
		class DOCINFOW(ctypes.Structure):
			_fields_ = [
				("cbSize", wintypes.INT),
				("lpszDocName", wintypes.LPCWSTR),
				("lpszOutput", wintypes.LPCWSTR),
				("lpszDatatype", wintypes.LPCWSTR),
				("fwType", wintypes.DWORD)
			]
		
		di = DOCINFOW()
		di.cbSize = ctypes.sizeof(DOCINFOW)
		di.lpszDocName = "TouchDesigner Photobooth Print"
		
		# 5. Start the hardware print job
		gdi32.StartDocW(hdc, ctypes.byref(di))
		gdi32.StartPage(hdc)
		
		# 6. Draw the image pixels to fill the hardware boundaries perfectly
		dib = ImageWin.Dib(img)
		dib.draw(hdc, (0, 0, printable_width, printable_height))
		
		# 7. End the job cleanly and release the printer
		gdi32.EndPage(hdc)
		gdi32.EndDoc(hdc)
		gdi32.DeleteDC(hdc)
		
		print("Success: Image scaled and printed completely silently!")
		return True
		
	except Exception as e:
		print(f"Direct GDI Print Error: {e}")
		return False
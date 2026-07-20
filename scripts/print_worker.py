# Inside a Text DAT named 'print_worker'
# Cross-platform: on Windows prints via GDI (silent, exact label sizing for the
# Munbyn driver); on macOS prints via CUPS `lp`. On either platform a print
# failure logs and returns False instead of killing the photobooth sequence.

import os
import sys
import subprocess
import time
from datetime import datetime

IS_WINDOWS = sys.platform == 'win32'

# macOS/CUPS queue name for the printer; None = system default printer.
# Find queue names with: lpstat -p   (spaces become underscores in CUPS)
MAC_PRINTER_QUEUE = None

if IS_WINDOWS:
	import ctypes
	from ctypes import wintypes
	import win32api
	import win32print
	from PIL import Image, ImageWin


def run_photobooth_sequence(full_path, printer_name):
	print("Text DAT sequence initiated...")

	# 1. Lock the cache
	op('cache1').par.active = 0

	if IS_WINDOWS:
		return _print_windows(full_path, printer_name)
	return _print_mac(full_path)


def _print_mac(full_path):
	"""Print through CUPS. The Munbyn must be added as a printer in macOS
	System Settings for this to do anything; otherwise it logs and moves on."""
	try:
		cmd = ['lp']
		if MAC_PRINTER_QUEUE:
			cmd += ['-d', MAC_PRINTER_QUEUE]
		cmd.append(full_path)
		res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
		if res.returncode == 0:
			print(f"Print job dispatched via lp: {res.stdout.strip()}")
			return True
		print(f"lp print failed: {res.stderr.strip()}")
		return False
	except Exception as e:
		print(f"macOS print error (continuing without print): {e}")
		return False


def _print_windows(full_path, printer_name):
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

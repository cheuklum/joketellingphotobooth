import os
import glob
import datetime
import subprocess
import random
import textwrap

PRINTER_NAME = "Munbyn RW403B-N(Bluetooth)" 
TEXT_FILE_PATH = os.path.normpath(os.path.join(project.folder, 'text.txt'))
WRAP_WIDTH = 35            # max characters per line; longer joke lines wrap instead of shrinking

# def onValueChange(channel, sampleIndex, val, prev):
#     # While the timer is actively running, keep the cache active!
#     if channel.name == 'running':
#         op('cache1').par.active = int(val)
#         print("START CACHE!")
#     return
    
def onOffToOn(channel, sampleIndex, val, prev):
    # While the timer is actively running, keep the cache active!
    if channel.name == 'ready_pulse':
        op('cache1').par.active = int(val)
        print("START CACHE NOW!")
    return

def onOnToOff(channel, sampleIndex, val, prev):
    if channel.name == 'done_pulse':
        should_print = op('button_enable_print').panel.state
        update_random_phrase()
        photo_path = save_photo()

        if should_print:
            print("CHOP Trigger: Off to On detected. Handing off once.")
            op('print_worker').module.run_photobooth_sequence(photo_path, PRINTER_NAME)
        else:
            print("Sequence finished, but printing is DISABLED by toggle.")
    # If you still want to run other parts of the photobooth 
    # sequence (like saving the image without printing), you'd call a different function here.
    return


def update_random_phrase():
    ts = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    print("update random phrase too")
    random_phrase = "Smile!"
    if os.path.exists(TEXT_FILE_PATH):
        with open(TEXT_FILE_PATH, 'r', encoding='utf-8') as f:
            phrases = [line.strip() for line in f.readlines() if line.strip()]
            if phrases:
                random_phrase = random.choice(phrases)

    # 1. Combine timestamp and random phrase with a newline
    combined_text = f'{ts}\n{random_phrase}'

    # 2. Perform line wrapping on the combined string
    final_text = _wrap(combined_text)

    # Instead of finding a DAT, just store it directly on the parent component!
    op('base1').par.Activetext = final_text


def _wrap(s):
	"""Wrap long lines to WRAP_WIDTH chars (at word boundaries), preserving any
	existing newlines - e.g. keeps the timestamp line, wraps the joke line. This
	makes long jokes break onto more lines instead of shrinking the font."""
	out = []
	for line in s.split('\n'):
		if len(line) <= WRAP_WIDTH:
			out.append(line)
		else:
			out.extend(textwrap.wrap(line, WRAP_WIDTH) or [line])
	return '\n'.join(out)

def save_photo():
# 2. Build paths and save image
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"pic_{ts}.jpg"
    folder = os.path.join(project.folder, 'captures')
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.normpath(os.path.join(folder, filename))

    op('final_image').save(full_path)
    print(f"Saved artwork directly to: {full_path}")
    if not os.path.exists(full_path):
        print(f"Error: File not found at {full_path}")

    return full_path
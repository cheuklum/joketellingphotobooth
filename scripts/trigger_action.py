import os
import glob
import datetime
import subprocess
import random
PRINTER_NAME = "Munbyn RW403B-N(Bluetooth)" 
TEXT_FILE_PATH = os.path.normpath(os.path.join(project.folder, 'text.txt'))

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
                
    # Instead of finding a DAT, just store it directly on the parent component!
    op('base1').par.Activetext = f"{ts}\n{random_phrase}"

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
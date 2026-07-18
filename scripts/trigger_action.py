import os
import glob
import datetime
import subprocess
PRINTER_NAME = "Munbyn RW403B-N(Bluetooth)" 
import random

def onValueChange(channel, sampleIndex, val, prev):
    # While the timer is actively running, keep the cache active!
    if channel.name == 'running':
        op('cache1').par.active = int(val)
        print("START CACHE!")
    return
    
def onOnToOff(channel, sampleIndex, val, prev):
    if channel.name == 'done_pulse':
        should_print = op('button_enable_print').panel.state
        update_random_phrase()

        if should_print:
            print("CHOP Trigger: Off to On detected. Handing off once.")
            op('print_worker').module.run_photobooth_sequence(PRINTER_NAME)
        else:
            print("Sequence finished, but printing is DISABLED by toggle.")
    # If you still want to run other parts of the photobooth 
    # sequence (like saving the image without printing), you'd call a different function here.
    return


TEXT_FILE_PATH = os.path.normpath(os.path.join(project.folder, 'text.txt'))

def update_random_phrase():
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    print("update random phrase too")
    random_phrase = "Smile!"
    if os.path.exists(TEXT_FILE_PATH):
        with open(TEXT_FILE_PATH, 'r', encoding='utf-8') as f:
            phrases = [line.strip() for line in f.readlines() if line.strip()]
            if phrases:
                random_phrase = random.choice(phrases)
                
    # Instead of finding a DAT, just store it directly on the parent component!
    op('base1').par.Activetext = f"{current_timestamp}\n{random_phrase}"
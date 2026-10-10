"""
Collect only the photobooth captures taken during the event window into a
separate folder (and, if that folder lives inside a Google Drive synced
location, Drive for Desktop live-uploads them automatically).

Event window: Fri Oct 9 2026 7:30 PM  ->  Sat Oct 10 2026 1:00 AM.

Captures are named pic_YYYYMMDD_HHMMSS.jpg, so the timestamp is read straight
from the filename. The script copies matching files that aren't already in the
destination, then keeps watching for new ones until the window closes.

Usage (from the project folder):
    python scripts/event_sync.py                 # copy into ./event_oct9 and watch
    python scripts/event_sync.py --dst "/path/inside/Google Drive/Photobooth Oct 9"
    python scripts/event_sync.py --once          # one pass, no watching
"""

import os
import re
import shutil
import time
import argparse
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WINDOW_START = datetime(2026, 10, 9, 19, 30, 0)   # Fri Oct 9, 7:30 PM
WINDOW_END   = datetime(2026, 10, 10, 1, 0, 0)    # Sat Oct 10, 1:00 AM

NAME_RE = re.compile(r'pic_(\d{8}_\d{6})')


def shot_time(filename):
    m = NAME_RE.search(filename)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), '%Y%m%d_%H%M%S')
    except ValueError:
        return None


def sync_once(src, dst):
    os.makedirs(dst, exist_ok=True)
    copied = 0
    for name in os.listdir(src):
        if not name.lower().endswith('.jpg'):
            continue
        t = shot_time(name)
        if t is None or not (WINDOW_START <= t < WINDOW_END):
            continue
        out = os.path.join(dst, name)
        if os.path.exists(out):
            continue
        shutil.copy2(os.path.join(src, name), out)
        copied += 1
        print(f'  + {name}')
    return copied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.join(PROJECT_DIR, 'captures'))
    ap.add_argument('--dst', default=os.path.join(PROJECT_DIR, 'event_oct9'))
    ap.add_argument('--once', action='store_true', help='single pass, no watching')
    ap.add_argument('--interval', type=float, default=5.0, help='seconds between scans')
    args = ap.parse_args()

    print(f'event window : {WINDOW_START}  ->  {WINDOW_END}')
    print(f'source       : {args.src}')
    print(f'destination  : {args.dst}')

    total = sync_once(args.src, args.dst)
    print(f'initial copy : {total} photo(s)')

    if args.once:
        return

    print('watching for new photos (Ctrl-C to stop)...')
    try:
        while datetime.now() < WINDOW_END + __import__('datetime').timedelta(minutes=5):
            n = sync_once(args.src, args.dst)
            if n:
                print(f'  copied {n} new')
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print('stopped.')
    print('done - window closed.')


if __name__ == '__main__':
    main()

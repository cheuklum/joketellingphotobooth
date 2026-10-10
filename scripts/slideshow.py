"""
Execute DAT ('execute_slideshow', DAT->Execute, 'Frame Start' toggle ON).

Live photo slideshow for a second monitor. Cycles through the captured photos
and loads each into a Movie File In TOP; re-scans the folder as the night goes
on so new photos appear automatically.

Targets:
  TARGET_OP   a Movie File In TOP whose File parameter gets set to each photo
  FOLDER      where the photos live (captures/ by default)

Modes:
  'sequential' - cycle oldest -> newest, loop
  'newest'     - always show the most recent photo (great for "your pic just popped up")
  'shuffle'    - random order, reshuffles after a full pass
"""

import os
import random

TARGET_OP = 'slideshow_img'
FOLDER    = 'captures'          # relative to the project folder; or 'event_oct9'
MODE      = 'sequential'        # 'sequential' | 'newest' | 'shuffle'
DWELL     = 4.0                 # seconds each photo stays up
RESCAN    = 6.0                 # seconds between folder re-scans (pick up new photos)

_state = {'files': [], 'order': [], 'idx': 0, 'last_adv': -1e9, 'last_scan': -1e9, 'shown': None}


def _scan():
	folder = os.path.join(project.folder, FOLDER)
	try:
		names = [n for n in os.listdir(folder) if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
	except Exception:
		names = []
	# sort by shot time (filename pic_YYYYMMDD_HHMMSS sorts chronologically)
	names.sort()
	return folder, names


def _rebuild_order(n):
	order = list(range(n))
	if MODE == 'shuffle':
		random.shuffle(order)
	return order


def onFrameStart(frame):
	t = op(TARGET_OP)
	if t is None:
		return
	now = absTime.seconds

	# periodically re-scan so photos taken during the event show up
	if now - _state['last_scan'] >= RESCAN:
		folder, names = _scan()
		_state['last_scan'] = now
		if names != _state['files']:
			added = len(names) - len(_state['files'])
			_state['files'] = names
			_state['folder'] = folder
			# keep/extend the play order
			if MODE == 'shuffle':
				_state['order'] = _rebuild_order(len(names))
				_state['idx'] = min(_state['idx'], max(0, len(names) - 1))
			else:
				_state['order'] = list(range(len(names)))
			if added > 0:
				print(f'[slideshow] {added} new photo(s), {len(names)} total')

	files = _state['files']
	if not files:
		return

	if MODE == 'newest':
		target_name = files[-1]
	else:
		# advance on the dwell timer
		if now - _state['last_adv'] >= DWELL:
			_state['idx'] = (_state['idx'] + 1) % len(_state['order'])
			_state['last_adv'] = now
			if MODE == 'shuffle' and _state['idx'] == 0:
				_state['order'] = _rebuild_order(len(files))
		target_name = files[_state['order'][_state['idx'] % len(_state['order'])]]

	if target_name != _state['shown']:
		t.par.file = os.path.join(_state.get('folder', os.path.join(project.folder, FOLDER)), target_name)
		_state['shown'] = target_name
	return

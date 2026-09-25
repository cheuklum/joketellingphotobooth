"""
Execute DAT ('execute_popup', DAT->Execute, 'Frame Start' toggle ON).

The kiyema.exe popup's full life cycle, driven off the shared timer1:

  IDLE       -> popup bounces around the frame, DVD-logo style.
  COUNTDOWN  -> a hand pose fires (gesture_detector pulses timer1.start), so
                timer1 starts running: the popup FREEZES in place and a countdown
                number counts the timer down.
  REVEAL     -> the countdown ends (timer1 stops): the popup re-emerges showing a
                random song title from tracklist.txt for REVEAL_SECONDS, then
                returns to bouncing.

Only READS timer1 - no protected gesture/print files are touched. Hand detection
+ the photo/print sequence keep running through the existing engine untouched;
this just adds the popup's reactions.

Targets (siblings of this DAT, or at /project1):
  POPUP_OP     Transform TOP that positions the popup window (tx/ty written)
  COUNTDOWN_OP Text TOP - the countdown number (blank except during COUNTDOWN)
  SONG_OP      Text TOP - the revealed song title (blank except during REVEAL)
  TIMER_OP     the project timer1
"""

import math
import os
import random

CORE = '/project1'
POPUP_OP     = 'popup_move'
COUNTDOWN_OP = 'popup_countdown'
SONG_OP      = 'popup_song'
TIMER_OP     = 'timer1'

POPUP_W = 0.33          # popup width  as fraction of canvas (bounce bounds)
POPUP_H = 0.30          # popup height as fraction of canvas
SPEED_X = 0.0045        # horizontal travel per frame
SPEED_Y = 0.0035        # vertical travel per frame
REVEAL_SECONDS = 6.0    # how long the song title stays up after the countdown
SONG_PREFIX = '♪ now playing: '   # printed before the title (music note)

_x = _y = 0.0
_vx = _vy = 0.0
_init = False
_prev_running = False
_reveal_until = -1.0
_song = ''
_tracklist = None


def _find(name):
	o = op(name)
	if o is None and not name.startswith('/'):
		o = op(CORE + '/' + name)
	return o


def _set_xy(o, x, y):
	if o is None:
		return
	for nx, ny in (('tx', 'ty'), ('translatex', 'translatey')):
		px = getattr(o.par, nx, None)
		py = getattr(o.par, ny, None)
		if px is not None and py is not None:
			px.val, py.val = x, y
			return


def _load_tracklist():
	global _tracklist
	path = os.path.join(project.folder, 'tracklist.txt')
	songs = []
	if os.path.exists(path):
		with open(path, 'r', encoding='utf-8') as f:
			songs = [ln.strip() for ln in f if ln.strip()]
	_tracklist = songs or ['(tracklist empty)']
	print(f"[popup] tracklist loaded: {len(_tracklist)} songs")


def _pick_song():
	if _tracklist is None:
		_load_tracklist()
	return random.choice(_tracklist)


def _set_text(o, s):
	if o is not None:
		o.par.text = s


def onFrameStart(frame):
	global _x, _y, _vx, _vy, _init, _prev_running, _reveal_until, _song
	if not _init:
		_x, _y = 0.0, 0.0
		_vx, _vy = SPEED_X, SPEED_Y
		_init = True

	timer = _find(TIMER_OP)
	running = False
	if timer is not None:
		try:
			running = float(timer['running']) > 0.5
		except Exception:
			running = False

	now = absTime.seconds

	# edge: the countdown just ended -> begin the song reveal
	if _prev_running and not running:
		_song = _pick_song()
		_reveal_until = now + REVEAL_SECONDS
	_prev_running = running

	popup     = _find(POPUP_OP)
	countdown = _find(COUNTDOWN_OP)
	song      = _find(SONG_OP)

	bx = max(0.0, 0.5 - POPUP_W / 2.0)
	by = max(0.0, 0.5 - POPUP_H / 2.0)

	if running:
		# ---- COUNTDOWN: freeze, show the number ----
		_set_xy(popup, _x, _y)
		if timer is not None:
			length = float(timer.par.length.eval())
			try:
				frac = float(timer['timer_fraction'])
			except Exception:
				frac = 0.0
			remaining = int(math.ceil(max(0.0, length * (1.0 - frac))))
			_set_text(countdown, str(remaining))
		_set_text(song, '')
	elif now < _reveal_until:
		# ---- REVEAL: hold, show the song title ----
		_set_xy(popup, _x, _y)
		_set_text(countdown, '')
		_set_text(song, SONG_PREFIX + _song)
	else:
		# ---- IDLE: bounce ----
		_x += _vx
		_y += _vy
		if _x >  bx: _x =  bx; _vx = -_vx
		if _x < -bx: _x = -bx; _vx = -_vx
		if _y >  by: _y =  by; _vy = -_vy
		if _y < -by: _y = -by; _vy = -_vy
		_set_xy(popup, _x, _y)
		_set_text(countdown, '')
		_set_text(song, '')
	return

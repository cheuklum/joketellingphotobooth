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
POPUP_OP     = 'popup_move'    # the bouncing decoration - only tx/ty is written (never scaled)
WINDOW_OP    = 'transform16'   # the popupwindow transform - this is what the CRT collapse scales
WINDOW_BASE  = 0.8             # popupwindow's normal resting scale (collapse animates from this)
COUNTDOWN_OP = 'popup_countdown'
SONG_OP      = 'popup_song'
TIMER_OP     = 'timer1'

POPUP_W = 0.33          # popup width  as fraction of canvas (bounce bounds)
POPUP_H = 0.30          # popup height as fraction of canvas
SPEED_X = 0.0045        # horizontal travel per frame
SPEED_Y = 0.0035        # vertical travel per frame
REVEAL_SECONDS = 1.0    # how long the song title stays up after the countdown
TURNOFF_SECONDS = 0.45  # CRT power-off collapse duration when the popup exits
DOT_HOLD_SECONDS = 0.35 # bright afterglow dot lingers before fully disappearing
SONG_PREFIX = '♪ now playing: '   # printed before the title (music note)

_x = _y = 0.0
_vx = _vy = 0.0
_init = False
_prev_running = False
_reveal_until = -1.0
_turnoff_until = -1.0
_dot_until = -1.0
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


def _set_scale(o, sx, sy):
	if o is None:
		return
	for nx, ny in (('sx', 'sy'), ('scalex', 'scaley')):
		px = getattr(o.par, nx, None)
		py = getattr(o.par, ny, None)
		if px is not None and py is not None:
			px.val, py.val = sx, sy
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
	global _x, _y, _vx, _vy, _init, _prev_running, _reveal_until, _turnoff_until, _dot_until, _song
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

	# edge: countdown ended -> reveal the song, then CRT turn-off, then afterglow dot
	if _prev_running and not running:
		_song = _pick_song()
		_reveal_until = now + REVEAL_SECONDS
		_turnoff_until = _reveal_until + TURNOFF_SECONDS
		_dot_until = _turnoff_until + DOT_HOLD_SECONDS
	_prev_running = running

	popup     = _find(POPUP_OP)      # bounced via tx/ty only - never scaled here
	window    = _find(WINDOW_OP)     # the popupwindow transform - gets the CRT collapse
	countdown = _find(COUNTDOWN_OP)
	song      = _find(SONG_OP)

	bx = max(0.0, 0.5 - POPUP_W / 2.0)
	by = max(0.0, 0.5 - POPUP_H / 2.0)

	flash = 0.0

	if running:
		# ---- COUNTDOWN: freeze full-size, show the number ----
		_set_scale(window, WINDOW_BASE, WINDOW_BASE)
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
		# ---- REVEAL: hold full-size, show the song title ----
		_set_scale(window, WINDOW_BASE, WINDOW_BASE)
		_set_xy(popup, _x, _y)
		_set_text(countdown, '')
		_set_text(song, SONG_PREFIX + _song)
	elif now < _turnoff_until:
		# ---- TURN-OFF: squash vertically to a line, then the line to a point;
		#      flash brightens as it collapses ----
		p = (now - _reveal_until) / max(0.001, TURNOFF_SECONDS)   # 0 -> 1
		if p < 0.6:
			sy = 1.0 - (p / 0.6) * (1.0 - 0.02)
			sx = 1.0
		else:
			sy = 0.02
			sx = max(0.0, 1.0 - (p - 0.6) / 0.4)
		_set_scale(window, WINDOW_BASE * sx, WINDOW_BASE * sy)
		_set_xy(popup, _x, _y)
		_set_text(countdown, '')
		_set_text(song, SONG_PREFIX + _song)
		flash = p
	elif now < _dot_until:
		# ---- AFTERGLOW: a tiny bright dot lingers, then fades out ----
		_set_scale(window, WINDOW_BASE * 0.02, WINDOW_BASE * 0.02)
		_set_xy(popup, _x, _y)
		_set_text(countdown, '')
		_set_text(song, '')
		flash = 1.0 - (now - _turnoff_until) / max(0.001, DOT_HOLD_SECONDS)
	else:
		# ---- IDLE: full-size, bounce (hidden by the gate) ----
		_set_scale(window, WINDOW_BASE, WINDOW_BASE)
		_x += _vx
		_y += _vy
		if _x >  bx: _x =  bx; _vx = -_vx
		if _x < -bx: _x = -bx; _vx = -_vx
		if _y >  by: _y =  by; _vy = -_vy
		if _y < -by: _y = -by; _vy = -_vy
		_set_xy(popup, _x, _y)
		_set_text(countdown, '')
		_set_text(song, '')

	# publish visibility (for the gate) and flash (for the white flare Level)
	_active = 1.0 if (running or now < _dot_until) else 0.0
	_b = _find('base1')
	if _b is not None:
		_b.store('popup_active', _active)
		_b.store('popup_flash', max(0.0, min(1.0, flash)))
	return

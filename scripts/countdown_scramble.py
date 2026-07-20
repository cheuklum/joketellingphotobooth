"""
Callbacks for an Execute DAT (e.g. 'execute_countdown', Sync to File on,
'Frame Start' toggle ON).

Drives the 'countdown' Text TOP from timer1: shows seconds remaining, and each
time the number changes it scrambles through the ascii glyph ramp for a few
frames before resolving - same feel as the joke text reveal.

IMPORTANT: the countdown Text TOP must NOT have an expression on its text
parameter anymore - this script writes the text directly. Clear it with:
	op('/project1/countdown').par.text.mode = ParMode.CONSTANT
"""

import math
import random

TIMER_OP = 'timer1'
TARGET_OP = 'countdown'

GLYPHS = "NO0A869452I3?!<>=+/:-"
RESOLVE_FRAMES = 14   # how long each new digit scrambles before locking in
CYCLE_EVERY = 2       # frames between glyph re-rolls
SCRAMBLE_ALPHA = 0.5  # text opacity while scrambling; resolved digit is 1.0

_state = {'value': None, 'started': -1e9, 'scramble': '', 'last_roll': -1}


def onFrameStart(frame):
	t = op(TIMER_OP)
	c = op(TARGET_OP)
	if t is None or c is None:
		return

	length = float(t.par.length.eval())
	try:
		frac = float(t['timer_fraction'])
	except Exception:
		frac = 0.0
	remaining = str(int(math.ceil(max(0.0, length * (1.0 - frac)))))

	now = absTime.frame
	if remaining != _state['value']:
		_state['value'] = remaining
		_state['started'] = now

	scrambling = now - _state['started'] < RESOLVE_FRAMES
	if scrambling:
		if now - _state['last_roll'] >= CYCLE_EVERY:
			_state['scramble'] = ''.join(random.choice(GLYPHS) for _ in remaining)
			_state['last_roll'] = now
		out = _state['scramble']
	else:
		out = remaining

	if c.par.text.eval() != out:
		c.par.text = out

	# dim the glyph churn, full brightness once the digit lands
	alpha = SCRAMBLE_ALPHA if scrambling else 1.0
	p = getattr(c.par, 'fontalpha', None)
	if p is not None and p.eval() != alpha:
		p.val = alpha
	return

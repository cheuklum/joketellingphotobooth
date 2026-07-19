"""
Callbacks for an Execute DAT (name it e.g. 'execute_scramble', Sync to File on,
'Frame Start' toggle ON).

Animates the joke text with an aino.agency-style scramble/decode reveal:
each character gets a randomized start delay, cycles through a glyph ramp
every few frames, then resolves to the real letter, sweeping left to right.

It watches base1's 'Activetext' custom parameter (set by chopexec1 when a new
phrase is chosen) and writes each animation frame into a Text TOP named
'joketext' - build that TOP (plus a Null after it) as the separate output and
composite it wherever you like. A monospace font on the Text TOP sells the
terminal feel.

Tuning knobs are the constants below; frame counts assume 60fps timeline.
"""

import random

SOURCE_OP = 'base1'        # component holding the Activetext custom parameter
TARGET_OP = 'joketext'     # Text TOP that displays the animation

GLYPHS = "NO0A869452I3?!<>=+/:-"   # aino's ascii ramp (dark->light), minus quiet chars
CYCLE_EVERY = 2      # frames between glyph re-rolls (higher = chunkier flicker)
STAGGER = 1.4        # frames of delay added per character index (the l->r sweep)
START_JITTER = 8     # random extra frames before a character starts scrambling
RESOLVE_AFTER = 16   # frames a character scrambles before locking in
RESOLVE_JITTER = 10  # random extra scramble frames per character

_anim = {
	'target': None,    # text currently being revealed
	'starts': [],      # per-char first visible frame
	'resolves': [],    # per-char lock-in frame
	'glyphs': [],      # per-char current scramble glyph
	'last_roll': -1,
	'last_out': None,
}


def _begin(target, now):
	_anim['target'] = target
	_anim['starts'] = []
	_anim['resolves'] = []
	_anim['glyphs'] = []
	visible_i = 0
	for ch in target:
		if ch in ('\n', ' '):
			start = resolve = now      # whitespace shows immediately
		else:
			start = now + visible_i * STAGGER + random.uniform(0, START_JITTER)
			resolve = start + RESOLVE_AFTER + random.uniform(0, RESOLVE_JITTER)
			visible_i += 1
		_anim['starts'].append(start)
		_anim['resolves'].append(resolve)
		_anim['glyphs'].append(random.choice(GLYPHS))


def onFrameStart(frame):
	target_op = op(TARGET_OP)
	source_op = op(SOURCE_OP)
	if target_op is None or source_op is None:
		return

	text = source_op.par.Activetext.eval() or ''
	now = absTime.frame

	if text != _anim['target']:
		_begin(text, now)

	target = _anim['target']
	if not target:
		return

	# re-roll the scramble glyphs on a chunky interval, not every frame
	if now - _anim['last_roll'] >= CYCLE_EVERY:
		_anim['glyphs'] = [random.choice(GLYPHS) for _ in target]
		_anim['last_roll'] = now

	out = []
	for i, ch in enumerate(target):
		if ch in ('\n', ' ') or now >= _anim['resolves'][i]:
			out.append(ch)
		elif now >= _anim['starts'][i]:
			out.append(_anim['glyphs'][i])
		else:
			out.append(' ')
	out = ''.join(out)

	if out != _anim['last_out']:
		target_op.par.text = out
		_anim['last_out'] = out
	return

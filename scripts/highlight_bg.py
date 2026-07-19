"""
Callbacks DAT for a Script TOP (e.g. 'jokehighlight').

Wire the joke Text TOP ('joketext') into its first input. It reads the actual
rendered text pixels, finds each text line's bounding box, and outputs tight
highlight bars behind them (padded, one per line) on a transparent background -
like a highlighter / redaction bar. Because it measures real pixels, it is
immune to font/alignment/resolution guesswork, and the bars track the scramble
animation as characters appear.

Composite: Over TOP with joketext as input 1 and this TOP as input 2.

Custom parameters (Setup Parameters):
  Pad X / Pad Y - bar padding in pixels around each line's text
  Merge Gap     - vertical pixel gap below which two glyph runs count as the
				  same line (keeps accents/descenders from splitting bars)
  Box Color     - highlight color
"""

import numpy as np


def onSetupParameters(scriptOp):
	page = scriptOp.appendCustomPage('Highlight')

	p = page.appendInt('Padx', label='Pad X')
	p[0].default = 24
	p[0].normMin, p[0].normMax = 0, 200

	p = page.appendInt('Pady', label='Pad Y')
	p[0].default = 10
	p[0].normMin, p[0].normMax = 0, 100

	p = page.appendInt('Mergegap', label='Merge Gap')
	p[0].default = 12
	p[0].normMin, p[0].normMax = 0, 60

	p = page.appendRGB('Boxcolor', label='Box Color')
	p[0].default, p[1].default, p[2].default = 0.13, 0.21, 0.93
	return


def onPulse(par):
	return


def _par(scriptOp, name, default):
	p = getattr(scriptOp.par, name, None)
	return p.eval() if p is not None else default


def onCook(scriptOp):
	inp = scriptOp.inputs[0] if scriptOp.inputs else None
	if inp is None:
		scriptOp.copyNumpyArray(np.zeros((4, 4, 4), dtype=np.uint8))
		return
	frame = inp.numpyArray(delayed=False)
	if frame is None:
		return
	H, W = frame.shape[:2]

	pad_x = int(_par(scriptOp, 'Padx', 24))
	pad_y = int(_par(scriptOp, 'Pady', 10))
	merge_gap = int(_par(scriptOp, 'Mergegap', 12))
	r = float(_par(scriptOp, 'Boxcolorr', 0.13))
	g = float(_par(scriptOp, 'Boxcolorg', 0.21))
	b = float(_par(scriptOp, 'Boxcolorb', 0.93))
	color = np.array([int(r * 255), int(g * 255), int(b * 255), 255], np.uint8)

	# where is there actually text? (alpha, with luminance fallback)
	ink = frame[:, :, 3] if frame.shape[2] > 3 else frame[:, :, :3].max(axis=2)
	ink = ink > 0.05

	out = np.zeros((H, W, 4), np.uint8)

	row_has_ink = ink.any(axis=1)
	if row_has_ink.any():
		# contiguous row runs -> merge runs separated by small gaps into lines
		d = np.diff(np.concatenate(([0], row_has_ink.astype(np.int8), [0])))
		starts = list(np.where(d == 1)[0])
		ends = list(np.where(d == -1)[0])
		lines = [[starts[0], ends[0]]]
		for s0, e0 in zip(starts[1:], ends[1:]):
			if s0 - lines[-1][1] <= merge_gap:
				lines[-1][1] = e0
			else:
				lines.append([s0, e0])

		for y0, y1 in lines:
			cols = np.where(ink[y0:y1].any(axis=0))[0]
			x0, x1 = cols[0], cols[-1] + 1
			yy0 = max(0, y0 - pad_y)
			yy1 = min(H, y1 + pad_y)
			xx0 = max(0, x0 - pad_x)
			xx1 = min(W, x1 + pad_x)
			out[yy0:yy1, xx0:xx1] = color

	scriptOp.copyNumpyArray(out)

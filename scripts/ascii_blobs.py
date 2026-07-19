"""
Callbacks DAT for a Script TOP (e.g. 'asciiblob1').

Wire any TOP (camera feed, stylized chain...) into its first input. The effect:
  1. Downsamples the frame to a character-cell grid.
  2. Quantizes colors and finds large connected blobs of similar color
	 (sky, smoke, road, walls - any big flat-ish region).
  3. Flattens each selected blob to its average color and typesets ASCII
	 characters over it, chosen per-cell from the original luminance using
	 the aino.agency dark->light ramp. Everything outside the blobs stays
	 untouched video.

Custom parameters (click Setup Parameters on the Script TOP):
  Cell Size    - pixel size of one character cell (bigger = chunkier + faster)
  Min Blob     - minimum blob area, in cells, before a region gets asciified
  Quantize     - color rounding step; higher merges more shades into one blob

Performance: all heavy work is vectorized numpy / OpenCV on a small grid.
If it gets choppy at high resolutions, raise Cell Size first.
"""

import cv2
import numpy as np

RAMP = "NO0A869452I3?!<>=+/:-. "   # dark -> light (aino ramp, cv2-safe glyphs)

_atlas_cache = {}


def _get_atlas(cell):
	atlas = _atlas_cache.get(cell)
	if atlas is None:
		font = cv2.FONT_HERSHEY_SIMPLEX
		scale = cv2.getFontScaleFromHeight(font, max(4, cell - 4), 1)
		atlas = np.zeros((len(RAMP), cell, cell), np.float32)
		for i, ch in enumerate(RAMP):
			img = np.zeros((cell, cell), np.uint8)
			(tw, th), _ = cv2.getTextSize(ch, font, scale, 1)
			org = ((cell - tw) // 2, (cell + th) // 2)
			cv2.putText(img, ch, org, font, scale, 255, 1, cv2.LINE_AA)
			atlas[i] = img.astype(np.float32) / 255.0
		_atlas_cache[cell] = atlas
	return atlas


def onSetupParameters(scriptOp):
	page = scriptOp.appendCustomPage('Ascii')

	p = page.appendInt('Cellsize', label='Cell Size')
	p[0].default = 14
	p[0].normMin, p[0].normMax = 6, 40

	p = page.appendInt('Minblob', label='Min Blob (cells)')
	p[0].default = 60
	p[0].normMin, p[0].normMax = 10, 500

	p = page.appendInt('Quantize', label='Quantize Step')
	p[0].default = 48
	p[0].normMin, p[0].normMax = 8, 128

	# blobs whose tone lands on this level (1 lightest .. 10 darkest) become
	# solid fills of their dominant color instead of ascii; 0 disables
	p = page.appendInt('Filltone', label='Solid Fill Tone (1-10)')
	p[0].default = 8
	p[0].normMin, p[0].normMax = 0, 10

	# height of the rectangle bands blobs get carved into, in cells
	p = page.appendInt('Lineheight', label='Line Height (cells)')
	p[0].default = 2
	p[0].normMin, p[0].normMax = 1, 10

	# show only rectangles of this tone (1-10) and make everything else
	# transparent; 0 shows all tones over the camera feed as usual
	p = page.appendInt('Showtone', label='Show Only Tone (0=all)')
	p[0].default = 0
	p[0].normMin, p[0].normMax = 0, 10
	return


def onPulse(par):
	return


def _par(scriptOp, name, default):
	p = getattr(scriptOp.par, name, None)
	return p.eval() if p is not None else default


def _band_rects(mask, line_h):
	"""Carve a cell mask into grid-aligned rectangles: one per contiguous run
	of occupied columns within each line_h-tall band."""
	rows, cols = mask.shape
	rects = []
	for y0 in range(0, rows, line_h):
		y1 = min(y0 + line_h, rows)
		cols_any = mask[y0:y1].any(axis=0)
		if not cols_any.any():
			continue
		d = np.diff(np.concatenate(([0], cols_any.astype(np.int8), [0])))
		for s0, e0 in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
			rects.append((y0, y1, s0, e0))
	return rects


def onCook(scriptOp):
	inp = scriptOp.inputs[0] if scriptOp.inputs else None
	if inp is None:
		scriptOp.copyNumpyArray(np.zeros((4, 4, 4), dtype=np.uint8))
		return
	frame = inp.numpyArray(delayed=False)
	if frame is None:
		return

	rgb = cv2.flip((frame[:, :, :3] * 255).astype(np.uint8), 0)
	H, W = rgb.shape[:2]

	cell = max(6, int(_par(scriptOp, 'Cellsize', 14)))
	min_cells = max(4, int(_par(scriptOp, 'Minblob', 60)))
	quant = max(8, int(_par(scriptOp, 'Quantize', 48)))

	rows, cols = H // cell, W // cell
	if rows < 2 or cols < 2:
		out_rgba = cv2.cvtColor(cv2.flip(rgb, 0), cv2.COLOR_RGB2RGBA)
		scriptOp.copyNumpyArray(out_rgba)
		return

	small = cv2.resize(rgb, (cols, rows), interpolation=cv2.INTER_AREA)

	# --- find large connected blobs of similar (quantized) color ---
	fill_tone = int(_par(scriptOp, 'Filltone', 8))
	q = (small.astype(np.int32) // quant * quant).astype(np.uint8)
	blob_cells = np.zeros((rows, cols), bool)   # blobs that get ascii
	fill_cells = np.zeros((rows, cols), bool)   # blobs that get a solid fill
	flat_cells = small.copy()
	text_cells = np.zeros((rows, cols), np.uint8)
	level_cells = np.zeros((rows, cols), np.uint8)   # tone level per rect cell
	show_tone = int(_par(scriptOp, 'Showtone', 0))

	line_h = max(1, int(_par(scriptOp, 'Lineheight', 2)))
	colors, counts = np.unique(q.reshape(-1, 3), axis=0, return_counts=True)
	for c0 in colors[counts >= min_cells]:
		mask = np.all(q == c0, axis=2).astype(np.uint8)
		n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
		for i in range(1, n):
			if stats[i, cv2.CC_STAT_AREA] >= min_cells:
				# carve the organic blob into grid-aligned rectangle bands
				for (y0, y1, x0, x1) in _band_rects(labels == i, line_h):
					mean = small[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)
					flat_cells[y0:y1, x0:x1] = mean.astype(np.uint8)
					# tone level 1 (lightest) .. 10 (darkest)
					level = int(np.clip(np.ceil((255.0 - mean.mean()) / 25.5), 1, 10))
					level_cells[y0:y1, x0:x1] = level
					if fill_tone > 0 and level == fill_tone:
						fill_cells[y0:y1, x0:x1] = True
						blob_cells[y0:y1, x0:x1] = False
					else:
						blob_cells[y0:y1, x0:x1] = True
						fill_cells[y0:y1, x0:x1] = False
						# light text on dark rects, dark text on light rects
						text_cells[y0:y1, x0:x1] = 90 if mean.mean() > 160 else 235

	# tone filter: keep only the selected tone's rectangles
	if show_tone > 0:
		keep = level_cells == show_tone
		blob_cells &= keep
		fill_cells &= keep

	if not blob_cells.any() and not fill_cells.any():
		if show_tone > 0:
			scriptOp.copyNumpyArray(np.zeros((H, W, 4), np.uint8))
		else:
			scriptOp.copyNumpyArray(cv2.cvtColor(cv2.flip(rgb, 0), cv2.COLOR_RGB2RGBA))
		return

	# --- per-cell ascii glyphs from original luminance (dark -> dense) ---
	lum = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
	idx = (lum.astype(np.int32) * (len(RAMP) - 1)) // 255
	atlas = _get_atlas(cell)
	glyph_img = atlas[idx].transpose(0, 2, 1, 3).reshape(rows * cell, cols * cell)

	# --- upscale cell-level data to pixels and composite ---
	H2, W2 = rows * cell, cols * cell
	flat_img = cv2.resize(flat_cells, (W2, H2), interpolation=cv2.INTER_NEAREST)
	text_img = cv2.resize(text_cells, (W2, H2), interpolation=cv2.INTER_NEAREST)
	mask_img = cv2.resize(blob_cells.astype(np.uint8), (W2, H2),
						  interpolation=cv2.INTER_NEAREST).astype(bool)
	fill_img = cv2.resize(fill_cells.astype(np.uint8), (W2, H2),
						  interpolation=cv2.INTER_NEAREST).astype(bool)

	g = glyph_img[..., None]
	ascii_region = flat_img.astype(np.float32) * (1 - g) + text_img[..., None].astype(np.float32) * g

	out = rgb.copy()
	region = out[:H2, :W2]
	region = np.where(mask_img[..., None], ascii_region, region)
	region = np.where(fill_img[..., None], flat_img, region)   # solid blocks, no glyphs
	out[:H2, :W2] = region.astype(np.uint8)

	if show_tone > 0:
		# selected tone only: everything outside its rectangles is transparent
		shown = np.zeros((H, W), bool)
		shown[:H2, :W2] = mask_img | fill_img
		out[~shown] = 0
		alpha = shown.astype(np.uint8) * 255
		out_rgba = np.dstack([cv2.flip(out, 0), cv2.flip(alpha, 0)])
	else:
		out_rgba = cv2.cvtColor(cv2.flip(out, 0), cv2.COLOR_RGB2RGBA)
	scriptOp.copyNumpyArray(out_rgba)

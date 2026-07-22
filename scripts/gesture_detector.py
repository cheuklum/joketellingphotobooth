"""
Callbacks DAT for a TouchDesigner Script TOP named e.g. 'gesture_detector'.

Network:
    [Video Device In TOP] -> [Script TOP: gesture_detector]  (this file is its Callbacks DAT)

What it does:
    - Runs MediaPipe Hands on every incoming camera frame.
    - Converts the 21 hand landmarks into a normalized (translation/scale invariant)
      63-float vector.
    - Lets you TEACH gestures: type a name in the 'Gesturename' custom parameter,
      hold the pose in front of the camera, click 'Capturesample' several times
      (varying angle/distance a little each time). Samples are stored in
      gestures/gesture_library.json.
    - Lets you DETECT gestures: with 'Detectenable' on, every frame's landmark
      vector is compared (nearest-neighbor / Euclidean distance) against the
      library. When a gesture matches for several stable frames and the cooldown
      has elapsed, the raw camera frame is saved as a .jpg into the Savefolder
      (captures/ by default), named "<gesture>_<timestamp>.jpg".

Setup (one time):
    Install mediapipe + opencv into TouchDesigner's Python:
        /Applications/TouchDesigner.app/Contents/MacOS/TouchDesigner --pip install mediapipe opencv-python
    or, from a terminal using the interpreter TD reports in a Text DAT via:
        import sys; print(sys.executable)
        <that python path> -m pip install mediapipe opencv-python
"""
import json
import os
import time
from datetime import datetime

import cv2
import numpy as np
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

_hands = mp_hands.Hands(
	static_image_mode=False,
	max_num_hands=2,
	min_detection_confidence=0.6,
	min_tracking_confidence=0.6,
)

_library = []          # list of {"label": str, "vector": [63 floats]}
_library_loaded = False
_last_label = None
_last_capture_time = 0.0
_stable_count = 0
_STABLE_FRAMES_REQUIRED = 5   # how many consecutive matching frames before it counts as "held"

# one-shot trigger: fire once per gesture appearance, re-arm only after the
# gesture has been absent for _REARM_FRAMES consecutive frames
_armed = True
_gone_count = 0
_REARM_FRAMES = 15


def _library_path():
	return os.path.join(project.folder, 'gestures', 'gesture_library.json')


def _captures_dir(scriptOp):
	folder = scriptOp.par.Savefolder.eval() or os.path.join(project.folder, 'captures')
	os.makedirs(folder, exist_ok=True)
	return folder


def _load_library():
	global _library, _library_loaded
	path = _library_path()
	if os.path.exists(path):
		with open(path, 'r') as f:
			_library = json.load(f)
		print(f"[gesture] library loaded: {len(_library)} samples from {path}")
	else:
		_library = []
		print(f"[gesture] no library file at {path} - starting empty")
	_library_loaded = True


def _save_library():
	path = _library_path()
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, 'w') as f:
		json.dump(_library, f, indent=2)


def _landmarks_to_vector(hand_landmarks):
	pts = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
	wrist = pts[0]
	pts = pts - wrist
	scale = np.linalg.norm(pts, axis=1).max()
	if scale > 1e-6:
		pts = pts / scale
	return pts.flatten().tolist()


def _classify(vector, threshold):
	if not _library or vector is None:
		return None, None
	v = np.array(vector)
	best_label, best_dist = None, float('inf')
	for sample in _library:
		d = float(np.linalg.norm(v - np.array(sample['vector'])))
		if d < best_dist:
			best_dist = d
			best_label = sample['label']
	if best_dist <= threshold:
		return best_label, best_dist
	return None, best_dist


def onSetupParameters(scriptOp):
	page = scriptOp.appendCustomPage('Gesture')

	p = page.appendStr('Gesturename', label='Gesture Name')
	p[0].default = 'fist'

	page.appendPulse('Capturesample', label='Capture Sample')

	p = page.appendToggle('Detectenable', label='Detect + Auto-Save')
	p[0].default = True

	# leave blank to save into <project folder>/captures (follows the .toe if you move it)
	page.appendFolder('Savefolder', label='Save Folder')

	p = page.appendFloat('Threshold', label='Match Threshold')
	p[0].default = 0.65
	p[0].normMin, p[0].normMax = 0.05, 1.0

	p = page.appendFloat('Cooldown', label='Cooldown (sec)')
	p[0].default = 1.5

	page.appendPulse('Clearlibrary', label='Clear Gesture Library')
	page.appendPulse('Reloadlibrary', label='Reload Gesture Library')

	_load_library()
	return


def onPulse(par):
	global _library
	scriptOp = par.owner

	if par.name == 'Capturesample':
		vector = scriptOp.fetch('lastVector', None)
		label = scriptOp.par.Gesturename.eval().strip()
		if vector is not None and label:
			_library.append({'label': label, 'vector': vector})
			_save_library()
			print(f"[gesture] captured sample for '{label}' ({len(_library)} total samples)")
		else:
			print("[gesture] no hand detected, or gesture name is empty - sample not captured")

	elif par.name == 'Clearlibrary':
		_library = []
		_save_library()
		print("[gesture] library cleared")

	elif par.name == 'Reloadlibrary':
		_load_library()
		print(f"[gesture] library reloaded ({len(_library)} samples)")

	return


def onCook(scriptOp):
	global _last_label, _last_capture_time, _stable_count

	if not _library_loaded:
		_load_library()

	input_top = scriptOp.inputs[0]
	if input_top is None:
		scriptOp.copyNumpyArray(np.zeros((4, 4, 4), dtype=np.uint8))
		return

	frame = input_top.numpyArray(delayed=False)
	if frame is None:
		return

	# TD gives float32 RGBA in [0,1], rows bottom-to-top; OpenCV/MediaPipe expect
	# uint8 BGR/RGB, rows top-to-bottom. Flip if your preview looks upside down
	# vs. what's stored - flip direction can vary by platform/driver.
	rgb = cv2.cvtColor((frame[:, :, :3] * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
	rgb = cv2.flip(rgb, 0)
	rgb_for_mp = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

	results = _hands.process(rgb_for_mp)

	vector = None
	if results.multi_hand_landmarks:
		for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
					
			# Draw all hands
			mp_drawing.draw_landmarks(rgb, hand_landmarks, mp_hands.HAND_CONNECTIONS)

			detected_side = handedness.classification[0].label
			if detected_side != "Right":
				continue
			else:
				vector = _landmarks_to_vector(hand_landmarks)

	scriptOp.store('lastVector', vector)
	threshold = scriptOp.par.Threshold.eval()
	label, dist = _classify(vector, threshold)

	if scriptOp.par.Detectenable.eval():
		global _armed, _gone_count
		now = time.time()
		if label is not None:
			_gone_count = 0
			_stable_count = _stable_count + 1 if label == _last_label else 0
		else:
			_stable_count = 0
			_gone_count += 1
			if _gone_count >= _REARM_FRAMES:
				_armed = True
		_last_label = label

		if (_armed
				and label is not None
				and _stable_count >= _STABLE_FRAMES_REQUIRED
				and (now - _last_capture_time) >= scriptOp.par.Cooldown.eval()
				and not op('timer1')['running'].eval()):
			
			# 1. Wipe out any old data in the cache
			op('cache1').par.reset.pulse() 
			
			# 2. Trigger the 5-second capture window
			op('timer1').par.start.pulse()

			_last_capture_time = now
			_stable_count = 0
			_armed = False
			# print(f"[gesture] detected '{label}' (dist={dist:.3f}) -> saved {filename}")
			print(f"[gesture] detected '{label}' (dist={dist:.3f})")

	if not _library:
		text, color = "library empty - capture samples first", (0, 0, 255)
	elif vector is None:
		text, color = "no hand detected", (0, 0, 255)
	elif label is not None and not _armed:
		text, color = f"{label} - photo taken, remove hand to re-arm", (255, 200, 0)
	elif label is not None:
		text, color = f"{label} ({dist:.2f})", (0, 255, 0)
	else:
		text, color = f"no match: dist {dist:.2f} > thr {threshold:.2f}", (0, 165, 255)
	cv2.putText(rgb, text, (10, 30),
				cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

	out = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
	out = cv2.flip(out, 0)
	out_rgba = cv2.cvtColor(out, cv2.COLOR_RGB2RGBA)
	scriptOp.copyNumpyArray(out_rgba)

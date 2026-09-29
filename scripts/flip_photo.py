"""
Fix photobooth captures that came out upside down.

By default rotates pic_*.jpg files in captures/ by 180 degrees (flips both
top-to-bottom and left-to-right, so text reads correctly again) and writes the
results to captures_flipped/ so the originals are left untouched.

Usage (from the project folder):
    python scripts/flip_photo.py                    # captures/pic_* -> captures_flipped/
    python scripts/flip_photo.py --mode vertical    # top-to-bottom only
    python scripts/flip_photo.py --mode mirror      # left-to-right only
    python scripts/flip_photo.py --pattern "*"      # every image, not just pic_*
    python scripts/flip_photo.py --in-place         # overwrite the originals
"""

import argparse
import fnmatch
import os

from PIL import Image

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}
MODES = {
	'rotate': Image.Transpose.ROTATE_180,
	'vertical': Image.Transpose.FLIP_TOP_BOTTOM,
	'mirror': Image.Transpose.FLIP_LEFT_RIGHT,
}


def main():
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument('--src', default=os.path.join(PROJECT_DIR, 'captures'))
	parser.add_argument('--dst', default=os.path.join(PROJECT_DIR, 'captures_flipped'))
	parser.add_argument('--mode', choices=MODES, default='rotate')
	parser.add_argument('--pattern', default='pic_*', help='filename glob to select which images to fix')
	parser.add_argument('--in-place', action='store_true', help='overwrite the source files')
	args = parser.parse_args()

	dst = args.src if args.in_place else args.dst
	os.makedirs(dst, exist_ok=True)
	transform = MODES[args.mode]

	names = sorted(
		n for n in os.listdir(args.src)
		if os.path.splitext(n)[1].lower() in IMAGE_EXTS and fnmatch.fnmatch(n, args.pattern)
	)
	done = 0
	for name in names:
		src_path = os.path.join(args.src, name)
		try:
			with Image.open(src_path) as img:
				img.load()
				out = img.transpose(transform)
		except Exception as e:
			print(f'skipped {name}: {e}')
			continue

		save_kwargs = {'quality': 95} if name.lower().endswith(('.jpg', '.jpeg')) else {}
		out.save(os.path.join(dst, name), **save_kwargs)
		done += 1

	print(f'{args.mode}: fixed {done}/{len(names)} images -> {dst}')


if __name__ == '__main__':
	main()

#!/usr/bin/env python3
"""
Turn a turntable video (and/or a rotation GIF) into a 360 spin frame set.

Why this exists: product footage from the factory is usually a studio turntable
clip where the object drifts across frame, plus a low-frame-count "360" GIF.
Neither is directly usable as a spin viewer. This normalises both.

What it does per frame:
  1. finds the object by thresholding against the white sweep,
  2. re-centres on the object's bounding box (the turntable is off-centre, so
     the object slides sideways across the raw clip),
  3. crops a fixed square and resizes.

If the footage only covers 180 degrees, pass --mirror to synthesise the back
half by horizontally flipping frames n-2 .. 1. That produces a seamless loop,
but any text on the product will read backwards in the mirrored half.

Usage:
  python3 build_spin.py video  IN.mp4 OUT_DIR --prefix s_ --end 8.2 --step 5
  python3 build_spin.py gif    IN.gif OUT_DIR --prefix c_ --box 2050 --size 900
"""

import argparse, glob, os, shutil, subprocess, sys, tempfile

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("needs pillow + numpy:  pip3 install pillow numpy")


def bbox(im, thr):
    """Bounding box of everything darker than `thr` (i.e. the product)."""
    g = np.array(im.convert("L"))
    ys, xs = np.nonzero(g < thr)
    if len(xs) == 0:
        return None
    return xs.min(), xs.max(), ys.min(), ys.max()


def normalise(paths, out_dir, prefix, box, size, thr, quality, mirror):
    os.makedirs(out_dir, exist_ok=True)
    half = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        bb = bbox(im, thr)
        if bb is None:
            print(f"  skip (nothing found): {p}")
            continue
        x0, x1, y0, y1 = bb
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        crop = im.crop((cx - box // 2, cy - box // 2, cx + box // 2, cy + box // 2))
        half.append(crop.resize((size, size), Image.LANCZOS))

    seq = half + ([f.transpose(Image.FLIP_LEFT_RIGHT) for f in half[-2:0:-1]] if mirror else [])
    for i, im in enumerate(seq):
        im.save(os.path.join(out_dir, f"{prefix}{i:03d}.jpg"), quality=quality, optimize=True)

    print(f"wrote {len(seq)} frames to {out_dir}  (real: {len(half)}, mirrored: {len(seq) - len(half)})")
    print(f"  -> half count for index.html SETS entry: {len(half)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["video", "gif"])
    ap.add_argument("src")
    ap.add_argument("out_dir")
    ap.add_argument("--prefix", default="s_")
    ap.add_argument("--start", type=float, default=0.0, help="video: seconds to skip")
    ap.add_argument("--end", type=float, default=None, help="video: seconds where the 180/360 sweep ends")
    ap.add_argument("--step", type=int, default=5, help="video: keep every Nth extracted frame")
    ap.add_argument("--box", type=int, default=470, help="crop square, in SOURCE pixels")
    ap.add_argument("--size", type=int, default=640, help="output square, in pixels")
    ap.add_argument("--thr", type=int, default=120, help="darker-than-this counts as the object")
    ap.add_argument("--quality", type=int, default=86)
    ap.add_argument("--mirror", action="store_true", help="fake the back half by flipping (180-degree footage)")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="spin_")
    try:
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        if a.start:
            cmd += ["-ss", str(a.start)]
        if a.end:
            cmd += ["-t", str(a.end - a.start)]
        cmd += ["-i", a.src]
        cmd += ["-vf", "fps=30"] if a.kind == "video" else ["-vsync", "0"]
        cmd += ["-q:v", "1", os.path.join(tmp, "r_%04d.jpg")]
        subprocess.run(cmd, check=True)

        frames = sorted(glob.glob(os.path.join(tmp, "r_*.jpg")))
        if a.kind == "video":
            frames = frames[:: a.step]
        print(f"{len(frames)} source frames")
        normalise(frames, a.out_dir, a.prefix, a.box, a.size, a.thr, a.quality, a.mirror)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

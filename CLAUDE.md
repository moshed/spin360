# spin360

Static 360-degree product spin viewer. Live at **https://360.dancykier.com**
(repo `moshed/spin360`, GitHub Pages off `main` root, `CNAME` file in repo root).

Currently shows one product: the **COBY CETW526** earbud case.

## Layout

```
index.html        the whole viewer — no build step, no dependencies
smooth/s_###.jpg  74 frames, 640px — from "526 Video.mp4" (30fps turntable clip)
crisp/c_###.jpg   12 frames, 900px — from "360 Degree rotation Image.gif" (2400px stills)
tools/build_spin.py   regenerates either frame set from source footage
CNAME             360.dancykier.com
```

Source footage came from the factory and lives in `~/Downloads/CETW526/` and
`~/Downloads/526 Video.mp4` — **not** committed (large, and not ours to publish).

## The load-bearing constraint: the footage is only 180 degrees

Both the video and the GIF cover front → side → back and stop. There is no
back-to-front half. So the frame sets are built as:

- **real half** — N frames covering ~0–180 degrees
- **mirrored half** — frames N-2 .. 1, horizontally flipped, standing in for 180–360

The loop is seamless and the case is bilaterally symmetric, so the silhouette is
correct — but **the COBY logo reads backwards through the mirrored half**. This is
disclosed in the note under the viewer, and the "180° real only" button shows just
the genuine frames.

If a real 360 turntable set ever arrives, rebuild with `--mirror` omitted and set
`half` equal to `total` in the `SETS` object in `index.html`.

## Things that were not obvious

- **The turntable is off-centre.** In the raw video the case slides from x≈618 to
  x≈827 across the sweep. Every frame must be re-centred on its own bounding box
  or the object wobbles around the frame. `build_spin.py` does this.
- **Optical-flow interpolation does not work here.** The GIF's 7 frames sit 30
  degrees apart; `ffmpeg minterpolate` warps the silhouette and leaves ghost
  halos. That's why the crisp set stays at 12 chunky-but-clean steps rather than
  being smoothed. Don't retry it without denser source frames.
- **Photogrammetry (Object Capture / `.usdz`) is a dead end for this product.**
  Matte black, no surface texture, seamless white background, half the angles
  missing — it fails on every count. The spin viewer is the honest alternative.
- **`turn` is tracked in revolutions, not frame indices.** That way switching
  between the smooth and crisp sets (different frame counts) keeps the case
  pointing the same direction instead of jumping.
- Drag distance is normalised to `stage.clientWidth`, so one drag across the
  viewer equals exactly one revolution at any screen size.
- Drag right decreases the frame index — in this footage the visible face travels
  left as the index rises, so the sign is flipped to make dragging feel direct.

## Adding another product

1. Build frames: `python3 tools/build_spin.py video IN.mp4 <name>/ --prefix p_ --end <sec> --mirror`
2. Add an entry to `SETS` in `index.html` with `dir`, `prefix`, `total`, `half`.
3. Commit, push. Pages rebuilds on its own.

## Deploy

Standard free-subdomain pattern — see the `dancykier_dns_namecheap` memory.
Namecheap `setHosts` must re-send every existing record **and** pass `EmailType=OX`,
or Moshe's email breaks.

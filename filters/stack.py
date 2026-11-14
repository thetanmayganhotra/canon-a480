#!/usr/bin/env python3
"""
stack.py - merge a burst of tripod shots from the A480.

  python stack.py lighten <folder or files>   # light trails / star trails (LONGEXP.LUA, 20+ shots)
  python stack.py mean    <folder or files>   # clean noisy night shots, silky water (5-10 shots)
  python stack.py fuse    <files>             # HDR bracket -> natural-looking merge (HDR.LUA)

  -o OUT.jpg to pick the output name. Then run film.py on the result if you want a look.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from film import gather, load, to_image, blur


def resize(a, w, h):
    chans = [a] if a.ndim == 2 else [a[..., i] for i in range(a.shape[2])]
    out = [np.asarray(Image.fromarray(c.astype(np.float32), "F").resize((w, h), Image.BILINEAR)) for c in chans]
    return out[0] if a.ndim == 2 else np.stack(out, -1)


def down(a):
    h, w = a.shape[:2]
    return resize(blur(a, 1.0), max(1, (w + 1) // 2), max(1, (h + 1) // 2))


def up(a, shape):
    return resize(a, shape[1], shape[0])


def fuse(imgs):
    """Mertens exposure fusion: keep the well-exposed, detailed, colourful bits of each frame."""
    ws = []
    for x in imgs:
        g = x.mean(-1)
        lap = np.abs(4 * g - np.roll(g, 1, 0) - np.roll(g, -1, 0) - np.roll(g, 1, 1) - np.roll(g, -1, 1))
        sat = x.std(-1)
        well = np.prod(np.exp(-((x - 0.5) ** 2) / (2 * 0.2 ** 2)), -1)
        ws.append(lap * sat * well + 1e-6)
    ws = np.array(ws)
    ws /= ws.sum(0)

    levels = max(3, int(np.log2(min(imgs[0].shape[:2]))) - 4)
    result = None
    for x, w in zip(imgs, ws):
        gp_w, g = [w], x
        lp = []
        for _ in range(levels):
            g2 = down(g)
            lp.append(g - up(g2, g.shape))
            g = g2
            gp_w.append(down(gp_w[-1]))
        lp.append(g)
        blended = [l * gw[..., None] for l, gw in zip(lp, gp_w)]
        result = blended if result is None else [r + b for r, b in zip(result, blended)]
    out = result[-1]
    for l in reversed(result[:-1]):
        out = up(out, l.shape) + l
    return np.clip(out, 0, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["lighten", "mean", "fuse"])
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--out")
    a = p.parse_args()

    files = gather(a.inputs)
    if len(files) < 2:
        sys.exit("need at least 2 images")
    print(f"{a.mode}: {len(files)} images")
    sizes = {Image.open(f).size for f in files if f.suffix.lower() not in {".dng", ".crw", ".cr2"}}
    if len(sizes) > 1:
        sys.exit(f"images are different sizes {sorted(sizes)} - stack only shots from the same burst")

    if a.mode == "fuse":
        imgs = [load(f)[0] for f in files]
        res = fuse(imgs)
    else:
        acc = None
        for i, f in enumerate(files, 1):
            x = load(f)[0]
            if acc is None:
                acc = x.copy() if a.mode == "lighten" else x.astype(np.float64)
            elif a.mode == "lighten":
                np.maximum(acc, x, out=acc)
            else:
                acc += x
            print(f"  {i}/{len(files)} {f.name}", end="\r")
        print()
        res = acc if a.mode == "lighten" else (acc / len(files)).astype(np.float32)

    out = Path(a.out or f"{files[0].stem}_{a.mode}.jpg")
    to_image(res).save(out, quality=95)
    print(f"  {out}")


if __name__ == "__main__":
    main()

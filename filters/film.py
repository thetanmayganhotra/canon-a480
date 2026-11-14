#!/usr/bin/env python3
"""
film.py - film-look filters for photos off the PowerShot A480 (JPEG or CHDK DNG).

  python film.py list
  python film.py apply portra photos/                 # one filter, whole folder
  python film.py apply portra,trix,lomo IMG_0042.JPG  # several filters
  python film.py apply all IMG_0042.JPG               # every filter
  python film.py sheet IMG_0042.JPG                   # contact sheet of every look
  python film.py luts                                 # export .cube LUTs (colour only)

Options for apply: -o OUTDIR, --strength 0..1, --ev STOPS, --no-grain,
                   --date / --no-date, --frame / --no-frame
"""
import argparse
import datetime as dt
import os
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from recipes import RECIPES

RAW_EXT = {".dng", ".crw", ".cr2"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff"} | RAW_EXT
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


# ---------------------------------------------------------------- helpers
def luma(x):
    return x @ LUMA


def mono_curve(points, n=1024):
    """Monotone cubic (Fritsch-Carlson) curve through points -> lookup table."""
    p = np.array(sorted(points), np.float64)
    xs, ys = p[:, 0], p[:, 1]
    if len(xs) == 2:
        t = np.linspace(0, 1, n)
        return np.interp(t, xs, ys).astype(np.float32)
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.empty_like(ys)
    m[0], m[-1] = d[0], d[-1]
    m[1:-1] = (d[:-1] + d[1:]) / 2
    for k in range(len(d)):
        if d[k] == 0:
            m[k] = m[k + 1] = 0
        else:
            a, b = m[k] / d[k], m[k + 1] / d[k]
            s = a * a + b * b
            if s > 9:
                tau = 3 / np.sqrt(s)
                m[k], m[k + 1] = tau * a * d[k], tau * b * d[k]
    t = np.linspace(0, 1, n)
    t = np.clip(t, xs[0], xs[-1])
    k = np.clip(np.searchsorted(xs, t) - 1, 0, len(h) - 1)
    u = (t - xs[k]) / h[k]
    h00 = (1 + 2 * u) * (1 - u) ** 2
    h10 = u * (1 - u) ** 2
    h01 = u * u * (3 - 2 * u)
    h11 = u * u * (u - 1)
    out = h00 * ys[k] + h10 * h[k] * m[k] + h01 * ys[k + 1] + h11 * h[k] * m[k + 1]
    return np.clip(out, 0, 1).astype(np.float32)


def apply_lut1d(x, lut):
    idx = np.clip(x, 0, 1) * (len(lut) - 1)
    return np.interp(idx, np.arange(len(lut)), lut).astype(np.float32)


def rgb_to_hsv(x):
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mx, mn = x.max(-1), x.min(-1)
    d = mx - mn
    dd = np.where(d > 1e-6, d, 1)
    h = np.select([mx == r, mx == g], [((g - b) / dd) % 6, (b - r) / dd + 2], (r - g) / dd + 4)
    h = np.where(d > 1e-6, h * 60, 0)
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    return h.astype(np.float32), s.astype(np.float32), mx.astype(np.float32)


def hsv_to_rgb(h, s, v):
    h6 = (h / 60.0) % 6
    i = np.floor(h6).astype(np.int8) % 6
    f = h6 - np.floor(h6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1).astype(np.float32)


def hue_rgb(deg):
    return hsv_to_rgb(np.float32(deg), np.float32(1), np.float32(1))


def box_blur(a, r, axis):
    if r < 1:
        return a
    r = int(r)
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def blur(a, radius):
    """Approx. gaussian blur of an HxW or HxWxC float image (downsample + 3x box)."""
    if radius < 0.5:
        return a
    H, W = a.shape[:2]
    k = max(1, int(radius / 3))
    chans = [a] if a.ndim == 2 else [a[..., i] for i in range(a.shape[2])]
    out = []
    for ch in chans:
        small = ch
        if k > 1:
            small = np.asarray(Image.fromarray(ch, "F").resize((max(1, W // k), max(1, H // k)), Image.BOX))
        r = max(1, radius / k / 1.7)
        for _ in range(3):
            small = box_blur(box_blur(small, r, 0), r, 1)
        if k > 1:
            small = np.asarray(Image.fromarray(small.astype(np.float32), "F").resize((W, H), Image.BILINEAR))
        out.append(small.astype(np.float32))
    return out[0] if a.ndim == 2 else np.stack(out, -1)


# ---------------------------------------------------------------- colour (LUT-able)
def color(x, r, ev=0.0):
    """Pure per-pixel colour transform. Everything here can be baked into a .cube LUT."""
    x = np.clip(x, 0, 1).astype(np.float32)

    # exposure / white balance / channel mix in (approx) linear light
    lin = x ** 2.2
    t, m = r.get("temp", 0.0), r.get("tint", 0.0)
    gains = np.array([1 + 0.3 * t, 1 - 0.15 * m, 1 - 0.3 * t], np.float32)
    gains *= 2 ** (r.get("exposure", 0.0) + ev)
    lin = lin * gains
    if "mixer" in r:
        lin = lin @ np.array(r["mixer"], np.float32).T
    x = np.clip(lin, 0, 1) ** (1 / 2.2)

    # black & white conversion (weights act like a coloured lens filter)
    if "bw" in r:
        w = np.array(r["bw"], np.float32)
        x = np.repeat((x @ (w / w.sum()))[..., None], 3, -1)

    # tone curves
    if "curve" in r:
        x = apply_lut1d(x, mono_curve(r["curve"]))
    for i, ch in enumerate("rgb"):
        if ch in r.get("curves", {}):
            x[..., i] = apply_lut1d(x[..., i], mono_curve(r["curves"][ch]))

    # per-hue saturation / hue shift / brightness
    if r.get("hues") and "bw" not in r:
        h, s, v = rgb_to_hsv(x)
        smul = np.ones_like(h)
        vmul = np.ones_like(h)
        shift = np.zeros_like(h)
        for center, width, sat, hshift, val in r["hues"]:
            dh = (h - center + 180) % 360 - 180
            w = np.exp(-0.5 * (dh / width) ** 2) * np.clip(s * 4, 0, 1)
            smul *= 1 + (sat - 1) * w
            vmul *= 1 + (val - 1) * w
            shift += hshift * w
        x = hsv_to_rgb((h + shift) % 360, np.clip(s * smul, 0, 1), np.clip(v * vmul, 0, 1))

    # global saturation
    if "sat" in r and "bw" not in r:
        L = luma(x)[..., None]
        x = L + (x - L) * r["sat"]

    # split toning: (hue_deg, amount)
    if "split" in r:
        L = np.clip(luma(x), 0, 1)[..., None]
        for key, wfun in (("shadows", (1 - L) ** 2), ("highlights", L ** 2)):
            if key in r["split"]:
                hue, amt = r["split"][key]
                c = hue_rgb(hue)
                x = x + (c - c.mean()) * 0.25 * amt * wfun

    return np.clip(x, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- texture / optics
def find_font():
    for f in ("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
              "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
              "/System/Library/Fonts/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
              "C:/Windows/Fonts/courbd.ttf"):
        if os.path.exists(f):
            return f
    return None


def date_stamp(x, when):
    H, W = x.shape[:2]
    long_ = max(H, W)
    size = max(10, int(long_ * 0.04))
    path = find_font()
    font = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    text = when.strftime("'%y %m %d")
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    bx = d.textbbox((0, 0), text, font=font)
    tw, th = bx[2] - bx[0], bx[3] - bx[1]
    mx = int(long_ * 0.045)
    d.text((W - mx - tw - bx[0], H - mx - th - bx[1]), text, font=font, fill=255)
    m = np.asarray(mask, np.float32) / 255
    glow = np.clip(blur(m, size * 0.18) * 1.6, 0, 1)
    orange = np.array([1.0, 0.52, 0.12], np.float32)
    x = 1 - (1 - x) * (1 - glow[..., None] * orange * 0.55)          # screen glow
    core = np.clip(m * 1.2, 0, 1)[..., None]
    return x * (1 - core) + np.array([1.0, 0.72, 0.35], np.float32) * core


def effects(x, fx, seed, strength=1.0, grain=True, date=None, frame=True):
    H, W = x.shape[:2]
    long_ = max(H, W)
    rng = np.random.default_rng(seed)
    k = strength

    if fx.get("sharpen"):
        x = x + fx["sharpen"] * k * (x - blur(x, max(1.0, long_ / 2500)))

    if fx.get("ca"):  # chromatic aberration: scale red + green up a hair, crop centre
        px = fx["ca"] * k * long_ / 3000
        for i, s in ((0, px), (1, px / 2)):
            if s < 0.25:
                continue
            nw, nh = int(round(W + 2 * s)), int(round(H + 2 * s * H / W))
            big = np.asarray(Image.fromarray(x[..., i], "F").resize((nw, nh), Image.BILINEAR))
            ox, oy = (nw - W) // 2, (nh - H) // 2
            x[..., i] = big[oy:oy + H, ox:ox + W]

    L = luma(x)
    if fx.get("halation"):  # red glow bleeding around bright light (no anti-halation layer)
        thr = fx.get("halation_thr", 0.75)
        bright = np.clip((L - thr) / (1 - thr), 0, 1)
        glow = blur(bright, long_ * fx.get("halation_r", 0.01))
        x = x + glow[..., None] * np.array([1.0, 0.28, 0.08], np.float32) * fx["halation"] * k

    if fx.get("bloom"):
        hi = x * np.clip((L - 0.55) / 0.45, 0, 1)[..., None]
        b = np.clip(blur(hi, long_ * 0.02) * fx["bloom"] * k * 2, 0, 1)
        x = 1 - (1 - np.clip(x, 0, 1)) * (1 - b)

    if fx.get("leak"):
        cx = rng.choice([-0.1, 1.1]) * W
        cy = rng.uniform(0.1, 0.9) * H
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / long_
        g = np.exp(-(d / 0.45) ** 2)[..., None] * np.array([1.0, 0.42, 0.12], np.float32)
        x = 1 - (1 - np.clip(x, 0, 1)) * (1 - g * fx["leak"] * k)

    if fx.get("vignette"):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
        x = x * (1 - fx["vignette"] * k * d ** 2.2)[..., None]

    if grain and fx.get("grain"):
        raw_size = fx.get("grain_size", 1.4) * long_ / 3000   # grain scales with the frame
        size = max(1.0, raw_size)
        k = k * min(1.0, raw_size)        # small/downsized images: grain averages out
        gh, gw = max(2, int(H / size)), max(2, int(W / size))
        n = rng.standard_normal((gh, gw)).astype(np.float32)
        if size > 1:
            n = np.asarray(Image.fromarray(n, "F").resize((W, H), Image.BICUBIC))
            n = n / (n.std() + 1e-6)
        L = np.clip(luma(x), 0, 1)
        w = 0.35 + 0.65 * 4 * L * (1 - L)          # grain is strongest in the midtones
        amt = fx["grain"] * k
        x = x + (n * w * amt)[..., None]
        if fx.get("grain_color", 0):
            c = rng.standard_normal((H, W, 3)).astype(np.float32)
            x = x + c * w[..., None] * amt * fx["grain_color"]

    x = np.clip(x, 0, 1)
    if date is not None:
        x = date_stamp(x, date)
    if frame and fx.get("frame") == "polaroid":
        side = int(W * 0.06)
        canvas = np.ones((H + side + int(W * 0.24), W + 2 * side, 3), np.float32)
        canvas *= np.array([0.95, 0.94, 0.90], np.float32)
        canvas[side:side + H, side:side + W] = x
        x = canvas
    return x


# ---------------------------------------------------------------- IO
def load(path, ev_raw=0.0):
    path = Path(path)
    if path.suffix.lower() in RAW_EXT:
        import rawpy
        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess(use_camera_wb=True, output_bps=16, bright=2 ** ev_raw,
                                  auto_bright_thr=0.005)
        return rgb.astype(np.float32) / 65535.0, None
    im = ImageOps.exif_transpose(Image.open(path))
    exif = im.info.get("exif")
    return np.asarray(im.convert("RGB"), np.float32) / 255.0, exif


def shot_date(path):
    try:
        ex = Image.open(path).getexif()
        s = ex.get_ifd(0x8769).get(36867) or ex.get(306)
        if s:
            return dt.datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return dt.datetime.fromtimestamp(os.path.getmtime(path))


def render(x, name, seed, strength=1.0, ev=0.0, grain=True, date=None, frame=True):
    r = RECIPES[name]
    y = color(x, r, ev)
    if strength < 1:
        y = x + (y - x) * strength
    return effects(y, r.get("fx", {}), seed, strength, grain, date=date, frame=frame)


def to_image(x):
    return Image.fromarray((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8))


def gather(inputs):
    files = []
    for p in map(Path, inputs):
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in IMG_EXT)
        elif p.exists():
            files.append(p)
        else:
            print(f"skip: {p} not found", file=sys.stderr)
    return files


def pick(spec):
    names = list(RECIPES) if spec == "all" else [s.strip() for s in spec.split(",")]
    bad = [n for n in names if n not in RECIPES]
    if bad:
        sys.exit(f"unknown filter(s): {', '.join(bad)}. run: python film.py list")
    return names


# ---------------------------------------------------------------- commands
def cmd_list(_):
    for n, r in RECIPES.items():
        print(f"  {n:<14} {r['desc']}")


def cmd_apply(a):
    names = pick(a.filters)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in gather(a.inputs):
        x, exif = load(f, a.ev if f.suffix.lower() in RAW_EXT else 0)
        when = shot_date(f)
        for n in names:
            date = when if (a.date or (a.date is None and RECIPES[n].get("fx", {}).get("date"))) else None
            y = render(x, n, zlib.crc32(f.name.encode()), a.strength,
                       0 if f.suffix.lower() in RAW_EXT else a.ev,
                       grain=not a.no_grain, date=date, frame=a.frame)
            dst = out / f"{f.stem}_{n}.jpg"
            kw = {"quality": 95, "subsampling": 0}
            if exif:
                kw["exif"] = exif
            to_image(y).save(dst, **kw)
            print(f"  {dst}")


def cmd_luts(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    N = a.size
    v = np.linspace(0, 1, N, dtype=np.float32)
    b, g, r = np.meshgrid(v, v, v, indexing="ij")           # red changes fastest
    grid = np.stack([r, g, b], -1).reshape(-1, 1, 3)
    for n, rec in RECIPES.items():
        y = color(grid, rec).reshape(-1, 3)
        with open(out / f"{n}.cube", "w") as fh:
            fh.write(f'TITLE "{n}"\nLUT_3D_SIZE {N}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
            fh.writelines(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n" for p in y)
        print(f"  {out / (n + '.cube')}")


def cmd_sheet(a):
    names = pick(a.filters)
    x, _ = load(a.image)
    im = to_image(x)
    im.thumbnail((a.width, a.width))
    x = np.asarray(im, np.float32) / 255
    when = shot_date(a.image)
    tiles = [("original", x)] + [(n, render(x, n, 7, date=when if RECIPES[n].get("fx", {}).get("date") else None,
                                            frame=False)) for n in names]
    cols = a.cols
    th, tw = x.shape[:2]
    pad, lab = 12, 34
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lab + pad) + pad), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    fpath = find_font()
    font = ImageFont.truetype(fpath, 24) if fpath else ImageFont.load_default()
    for i, (n, t) in enumerate(tiles):
        cx, cy = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + lab + pad)
        sheet.paste(to_image(t), (cx, cy))
        d.text((cx, cy + th + 6), n, fill=(235, 235, 235), font=font)
    sheet.save(a.out, quality=90)
    print(f"  {a.out}")


def main():
    p = argparse.ArgumentParser(description="Film-look filters for the PowerShot A480")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("list", help="show all filters").set_defaults(fn=cmd_list)

    ap = sp.add_parser("apply", help="apply filter(s) to files/folders")
    ap.add_argument("filters", help="name, comma list, or 'all'")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--out", default="filtered")
    ap.add_argument("--strength", type=float, default=1.0, help="0..1, how strong the look is")
    ap.add_argument("--ev", type=float, default=0.0, help="exposure tweak in stops (DNG: applied at decode)")
    ap.add_argument("--no-grain", action="store_true")
    ap.add_argument("--date", dest="date", action="store_true", default=None, help="force date stamp on")
    ap.add_argument("--no-date", dest="date", action="store_false", help="force date stamp off")
    ap.add_argument("--no-frame", dest="frame", action="store_false", default=True)
    ap.set_defaults(fn=cmd_apply)

    lp = sp.add_parser("luts", help="export .cube LUTs (colour only - no grain/glow)")
    lp.add_argument("-o", "--out", default="luts")
    lp.add_argument("--size", type=int, default=33)
    lp.set_defaults(fn=cmd_luts)

    sh = sp.add_parser("sheet", help="contact sheet comparing filters on one photo")
    sh.add_argument("image")
    sh.add_argument("filters", nargs="?", default="all")
    sh.add_argument("-o", "--out", default="sheet.jpg")
    sh.add_argument("--width", type=int, default=640)
    sh.add_argument("--cols", type=int, default=4)
    sh.set_defaults(fn=cmd_sheet)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

"""
Film-look recipes. Tweak freely - every number is plain and safe to play with.

Colour keys (these get baked into the .cube LUTs):
  exposure   stops (+ brighter)
  temp       white balance, + warmer / - cooler   (~ -1..1)
  tint       + magenta / - green                  (~ -1..1)
  mixer      3x3 channel mixer in linear light (rows should sum to ~1)
  bw         [r, g, b] weights -> black & white (more red = darker skies, like a red lens filter)
  curve      master tone curve, list of (in, out) points 0..1
  curves     per-channel curves {"r": [...], "g": [...], "b": [...]}
  hues       list of (hue_deg, width_deg, sat_mult, hue_shift_deg, brightness_mult)
             hue: 0 red, 30 orange/skin, 55 yellow, 110 green, 180 cyan, 215 blue, 300 magenta
  sat        global saturation multiplier
  split      {"shadows": (hue_deg, amount), "highlights": (hue_deg, amount)}

Texture keys under "fx" (applied by film.py only, not in LUTs):
  grain, grain_size, grain_color, halation, halation_thr, halation_r,
  bloom, vignette, ca (chromatic aberration), sharpen, leak, date, frame
"""

RECIPES = {
    # ------------------------------------------------------------ Kodak-ish
    "portra": {
        "desc": "Kodak Portra-ish - warm, soft, flattering skin, calm greens",
        "temp": 0.25, "tint": 0.08,
        "curve": [(0, 0.04), (0.25, 0.245), (0.5, 0.52), (0.75, 0.78), (1, 0.97)],
        "curves": {"b": [(0, 0.03), (0.5, 0.485), (1, 0.96)]},
        "hues": [(110, 35, 0.72, -8, 1.0), (25, 22, 0.95, 2, 1.03), (215, 35, 0.85, -4, 1.0)],
        "sat": 0.93,
        "split": {"shadows": (200, 0.25), "highlights": (35, 0.2)},
        "fx": {"grain": 0.03, "grain_size": 1.4, "halation": 0.05, "vignette": 0.12},
    },
    "gold": {
        "desc": "Kodak Gold-ish - golden-hour yellow warmth, punchy reds, nostalgic",
        "temp": 0.45,
        "curve": [(0, 0.03), (0.25, 0.22), (0.5, 0.52), (0.75, 0.8), (1, 0.98)],
        "curves": {"b": [(0, 0.02), (0.5, 0.45), (1, 0.9)]},
        "hues": [(0, 25, 1.15, 0, 1.0), (55, 25, 1.2, -5, 1.03), (110, 35, 0.88, -12, 1.0),
                 (215, 35, 0.9, 0, 0.97)],
        "sat": 1.08,
        "fx": {"grain": 0.045, "grain_size": 1.5, "vignette": 0.18, "halation": 0.04},
    },
    "ektar": {
        "desc": "Kodak Ektar-ish - vivid landscape film, deep blues, rich reds",
        "temp": 0.15,
        "curve": [(0, 0.0), (0.25, 0.2), (0.5, 0.5), (0.75, 0.82), (1, 1.0)],
        "hues": [(0, 25, 1.25, 0, 0.97), (30, 20, 1.12, 0, 1.0), (110, 35, 1.1, 0, 0.97),
                 (215, 35, 1.2, -5, 0.94)],
        "sat": 1.18,
        "fx": {"grain": 0.022, "grain_size": 1.2, "vignette": 0.1},
    },
    "kodachrome": {
        "desc": "Kodachrome-ish - contrasty, deep crimson reds, cyan-blue skies, vintage magazine",
        "temp": 0.12, "tint": 0.05,
        "curve": [(0, 0.0), (0.2, 0.12), (0.5, 0.48), (0.8, 0.86), (1, 0.98)],
        "hues": [(0, 22, 1.3, -4, 0.92), (30, 20, 1.05, -3, 1.0), (55, 25, 1.1, -6, 1.0),
                 (110, 35, 0.9, 8, 0.92), (215, 35, 1.15, -12, 0.9)],
        "sat": 1.1,
        "fx": {"grain": 0.025, "grain_size": 1.2, "vignette": 0.2},
    },
    # ------------------------------------------------------------ Fuji-ish
    "superia": {
        "desc": "Fuji Superia-ish - cool green shadows, magenta-ish highlights, punchy greens",
        "temp": -0.05, "tint": -0.15,
        "curve": [(0, 0.03), (0.25, 0.23), (0.5, 0.5), (0.75, 0.79), (1, 0.98)],
        "curves": {"g": [(0, 0.03), (0.4, 0.415), (1, 1.0)]},
        "hues": [(120, 35, 1.15, 6, 1.0), (215, 35, 1.1, 0, 1.0), (0, 25, 1.05, -4, 1.0)],
        "sat": 1.05,
        "split": {"shadows": (165, 0.45), "highlights": (320, 0.2)},
        "fx": {"grain": 0.045, "grain_size": 1.5, "vignette": 0.12},
    },
    "velvia": {
        "desc": "Fuji Velvia-ish - super saturated slide film, made for skies and leaves",
        "temp": 0.05,
        "curve": [(0, 0.0), (0.2, 0.13), (0.5, 0.5), (0.8, 0.88), (1, 1.0)],
        "hues": [(215, 35, 1.18, 0, 0.94), (110, 35, 1.3, -4, 0.95), (0, 25, 1.3, 0, 1.0),
                 (300, 30, 1.2, 0, 1.0)],
        "sat": 1.35,
        "fx": {"grain": 0.015, "grain_size": 1.0, "vignette": 0.15},
    },
    "pro400h": {
        "desc": "Fuji Pro 400H-ish - airy, pastel, minty greens, wedding-blog bright",
        "exposure": 0.3, "temp": -0.05, "tint": -0.08,
        "curve": [(0, 0.07), (0.3, 0.33), (0.6, 0.65), (1, 0.97)],
        "hues": [(110, 35, 0.85, 14, 1.03), (25, 22, 0.85, 0, 1.03), (215, 35, 0.9, -6, 1.0)],
        "sat": 0.85,
        "split": {"shadows": (185, 0.35)},
        "fx": {"grain": 0.03, "grain_size": 1.4, "bloom": 0.08},
    },
    "chrome": {
        "desc": "Classic-Chrome-ish - muted documentary colour, hard shadows, teal skies",
        "curve": [(0, 0.02), (0.2, 0.14), (0.5, 0.48), (0.8, 0.82), (1, 0.96)],
        "hues": [(0, 25, 0.8, 5, 1.0), (55, 25, 0.8, -5, 1.0), (110, 35, 0.65, -8, 0.95),
                 (215, 35, 0.75, -12, 0.92)],
        "sat": 0.78,
        "split": {"shadows": (195, 0.2)},
        "fx": {"grain": 0.02, "grain_size": 1.2, "vignette": 0.1},
    },
    # ------------------------------------------------------------ cinema
    "cinestill": {
        "desc": "CineStill 800T-ish - tungsten blue night film, red halation around lights",
        "temp": -0.45, "tint": 0.08,
        "curve": [(0, 0.03), (0.25, 0.2), (0.5, 0.5), (0.75, 0.8), (1, 0.99)],
        "hues": [(0, 25, 1.15, 0, 1.0), (215, 35, 1.1, -6, 1.0)],
        "sat": 1.05,
        "split": {"shadows": (185, 0.3)},
        "fx": {"halation": 0.5, "halation_thr": 0.7, "halation_r": 0.012, "grain": 0.05,
               "grain_size": 1.6, "bloom": 0.05, "vignette": 0.1},
    },
    "teal_orange": {
        "desc": "Blockbuster teal & orange - orange skin, teal everything else",
        "curve": [(0, 0.03), (0.25, 0.21), (0.5, 0.5), (0.75, 0.8), (1, 0.98)],
        "hues": [(30, 30, 1.2, -3, 1.02), (0, 20, 1.0, 12, 1.0), (55, 20, 0.9, -15, 1.0),
                 (215, 40, 1.1, -25, 0.95), (110, 40, 0.55, 45, 0.95)],
        "split": {"shadows": (190, 0.6), "highlights": (32, 0.35)},
        "fx": {"grain": 0.02, "grain_size": 1.2, "vignette": 0.15},
    },
    # ------------------------------------------------------------ black & white
    "trix": {
        "desc": "Tri-X-ish B&W - gritty, contrasty, street-photo grain",
        "bw": [0.4, 0.45, 0.15],
        "curve": [(0, 0.02), (0.2, 0.12), (0.5, 0.5), (0.8, 0.88), (1, 0.99)],
        "fx": {"grain": 0.09, "grain_size": 1.7, "vignette": 0.2},
    },
    "hp5": {
        "desc": "HP5-ish B&W - softer tones, gentle grain, slightly warm paper",
        "bw": [0.33, 0.5, 0.17],
        "curve": [(0, 0.06), (0.25, 0.24), (0.5, 0.5), (0.75, 0.76), (1, 0.95)],
        "split": {"highlights": (40, 0.15)},
        "fx": {"grain": 0.065, "grain_size": 1.9, "vignette": 0.12},
    },
    "noir": {
        "desc": "Red-filter noir B&W - black skies, glowing skin, heavy drama",
        "bw": [0.75, 0.22, 0.03],
        "curve": [(0, 0.0), (0.25, 0.1), (0.5, 0.48), (0.75, 0.88), (1, 1.0)],
        "fx": {"grain": 0.05, "grain_size": 1.4, "vignette": 0.4, "bloom": 0.06},
    },
    # ------------------------------------------------------------ fun / lo-fi
    "polaroid": {
        "desc": "Instant film - faded, cyan shadows, creamy highlights, white frame",
        "exposure": 0.2, "temp": 0.1,
        "curve": [(0, 0.1), (0.3, 0.36), (0.6, 0.64), (1, 0.93)],
        "hues": [(110, 35, 0.8, 10, 1.0)],
        "sat": 0.8,
        "split": {"shadows": (195, 0.5), "highlights": (48, 0.35)},
        "fx": {"vignette": 0.25, "bloom": 0.1, "grain": 0.02, "frame": "polaroid"},
    },
    "disposable": {
        "desc": "Disposable camera - flash-blown, greenish shadows, heavy grain, date stamp",
        "temp": 0.2, "tint": -0.12,
        "curve": [(0, 0.04), (0.2, 0.15), (0.5, 0.52), (0.8, 0.86), (1, 0.97)],
        "curves": {"g": [(0, 0.05), (0.5, 0.51), (1, 1.0)]},
        "sat": 1.1,
        "fx": {"grain": 0.075, "grain_size": 1.7, "grain_color": 0.25, "vignette": 0.3, "ca": 1.5,
               "date": True},
    },
    "lomo": {
        "desc": "Lomo / cross-processed - crushed contrast, yellow highs, blue lows, light leak",
        "curve": [(0, 0.0), (0.25, 0.15), (0.5, 0.5), (0.75, 0.87), (1, 1.0)],
        "curves": {"r": [(0, 0.0), (0.5, 0.55), (1, 1.0)],
                   "g": [(0, 0.02), (0.5, 0.52), (1, 0.98)],
                   "b": [(0, 0.12), (0.5, 0.45), (1, 0.85)]},
        "sat": 1.3,
        "fx": {"vignette": 0.55, "ca": 2.0, "grain": 0.04, "grain_size": 1.5, "leak": 0.35},
    },
    "y2k": {
        "desc": "Y2K CCD digicam - cool, bright, crispy, bloomy, orange date stamp",
        "temp": -0.25, "tint": 0.02,
        "curve": [(0, 0.0), (0.25, 0.22), (0.5, 0.54), (0.75, 0.84), (1, 1.0)],
        "hues": [(215, 35, 1.2, 0, 1.0)],
        "sat": 1.15,
        "fx": {"sharpen": 0.6, "bloom": 0.12, "ca": 1.0, "grain": 0.012, "grain_color": 0.6,
               "date": True},
    },
}

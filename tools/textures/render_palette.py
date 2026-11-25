"""Palette swatch for docs/art_bible.md (the five ink tones, paper, vermilion).
    blender -b --factory-startup --python tools/textures/render_palette.py
"""
import os
import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SW = [("paper", (0.92, 0.905, 0.865)), ("sei", (0.80,) * 3), ("tan", (0.52,) * 3), ("ju", (0.22,) * 3),
      ("no", (0.10,) * 3), ("sho", (0.035,) * 3), ("shu", (0.62, 0.11, 0.08))]
w, h = 140, 140
img = np.ones((h, w * len(SW), 4))
for i, (_, c) in enumerate(SW):
    img[:, i * w:(i + 1) * w, :3] = [x ** 2.2 for x in c]  # store linear; Blender writes sRGB
out = bpy.data.images.new("palette", w * len(SW), h)
out.pixels.foreach_set(img.astype(np.float32).ravel())
path = os.path.join(ROOT, "docs", "renders", "palette.png")
os.makedirs(os.path.dirname(path), exist_ok=True)
out.filepath_raw = path
out.file_format = "PNG"
out.save()
print("[palette]", path)

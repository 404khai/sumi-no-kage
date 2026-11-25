"""Procedural ink textures for the Godot shaders. Deterministic (fixed seeds).

    blender -b --factory-startup --python tools/textures/generate_ink_textures.py

Runs inside Blender only for its bundled numpy + PNG writer (no extra deps).
Outputs to game/textures/ink/. All tileable textures are built in the
frequency domain, which makes them seamless by construction.
"""

import math
import os
import sys

import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "game", "textures", "ink")


def save(name, rgba):
    """rgba: float array (h, w, 4) in 0..1, row 0 = top of the image."""
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.ascontiguousarray(np.flipud(np.clip(rgba, 0, 1))).astype(np.float32).ravel())
    path = os.path.join(OUT, name + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("[ink-tex]", os.path.relpath(path, ROOT), f"{w}x{h}")


def spectral_noise(shape, beta, rng, aniso=(1.0, 1.0)):
    """Periodic 1/f^beta noise normalised to 0..1."""
    h, w = shape
    white = rng.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None] * aniso[0]
    fx = np.fft.fftfreq(w)[None, :] * aniso[1]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    spec = np.fft.fft2(white) / f ** beta
    spec[0, 0] = 0
    n = np.real(np.fft.ifft2(spec))
    n -= n.min()
    return n / (n.max() + 1e-9)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def paper_grain(rng):
    """Washi: soft cloud + long kozo fibres + fine tooth. Grey value, 0.5 = neutral."""
    s = 512
    cloud = spectral_noise((s, s), 1.6, rng)
    tooth = spectral_noise((s, s), 0.4, rng)
    fibres = spectral_noise((s, s), 1.2, rng, aniso=(0.12, 1.0))   # stretched -> long fibres
    fibres2 = spectral_noise((s, s), 1.2, rng, aniso=(1.0, 0.15))
    fib = np.maximum(smoothstep(0.62, 0.78, fibres), smoothstep(0.64, 0.80, fibres2))
    g = 0.5 + 0.18 * (cloud - 0.5) + 0.10 * (tooth - 0.5) + 0.12 * fib
    rgba = np.dstack([g, cloud, tooth, np.ones_like(g)])
    save("paper_grain", rgba)


def wash_noise(rng):
    """R: large wash blooms, G: medium, B: bleed edges (high-frequency), A: 1."""
    s = 512
    r = spectral_noise((s, s), 2.2, rng)
    g = spectral_noise((s, s), 1.5, rng)
    b = spectral_noise((s, s), 0.9, rng)
    save("ink_wash_noise", np.dstack([r, g, b, np.ones_like(r)]))


def brush_stroke(rng):
    """A single horizontal dry-brush stroke (u = along stroke, v = across).

    R: ink density, G: bristle streaks, B: along-stroke dryness gradient, A: coverage.
    Used by slash trails, phantom-step streaks and to break up toon bands.
    """
    w, h = 1024, 256
    u = np.linspace(0, 1, w)[None, :]
    v = np.linspace(-1, 1, h)[:, None]
    # width profile: pressed start, long body, lifting tail
    width = 0.55 + 0.35 * smoothstep(0.0, 0.12, u) - 0.55 * smoothstep(0.55, 1.0, u) ** 1.4
    # stroke centre wobbles a little
    centre = 0.06 * np.sin(u * 5.0 + 0.7) * (1 - u)
    across = np.abs(v - centre) / np.maximum(width, 0.02)
    # bristles: streaks running along u
    bristle = spectral_noise((h, 64), 0.8, rng)
    bristle = np.repeat(bristle, w // 64 + 1, axis=1)[:, :w]
    streak_noise = spectral_noise((h, w), 1.0, rng, aniso=(1.0, 0.04))
    streak = 0.65 * bristle + 0.35 * streak_noise
    dryness = smoothstep(0.35, 1.0, u)  # paint runs out toward the tail
    edge_noise = spectral_noise((h, w), 1.3, rng)
    edge = 1 - smoothstep(0.75 + 0.18 * (edge_noise - 0.5), 1.02, across)
    dry_gaps = smoothstep(0.25 + 0.55 * dryness, 0.45 + 0.55 * dryness, streak)
    head = smoothstep(0.0, 0.03, u)
    alpha = np.clip(edge * (1 - dryness * (1 - dry_gaps)) * head, 0, 1)
    density = np.clip(0.75 + 0.25 * streak - 0.4 * dryness, 0, 1)
    rgba = np.dstack([density, streak, np.broadcast_to(dryness, alpha.shape), alpha])
    save("brush_stroke", rgba)


def ink_blots(rng):
    """4x4 atlas of ink splats/drops for particles. White = ink coverage in A."""
    cell, n = 256, 4
    atlas = np.zeros((cell * n, cell * n, 4))
    yy, xx = np.mgrid[0:cell, 0:cell]
    cx = (xx - cell / 2) / (cell / 2)
    cy = (yy - cell / 2) / (cell / 2)
    rad = np.sqrt(cx * cx + cy * cy)
    ang = np.arctan2(cy, cx)
    for i in range(n * n):
        k = i / (n * n - 1)
        base_r = 0.30 + 0.25 * rng.random()
        lobes = np.zeros_like(rad)
        for m, amp in ((1, 0.18), (2, 0.16), (3, 0.10), (5, 0.04), (9, 0.015)):
            lobes += rng.uniform(0.3, 1.0) * amp * np.sin(m * ang + rng.uniform(0, 6.28))
        n_tex = spectral_noise((cell, cell), 1.4, rng)
        n_edge = spectral_noise((cell, cell), 1.9, rng)
        r_edge = base_r * (1 + lobes) + 0.22 * (n_edge - 0.5) + 0.04 * (n_tex - 0.5)
        blot = 1 - smoothstep(r_edge - 0.02, r_edge + 0.01, rad)
        # satellite droplets thrown outward
        for _ in range(int(4 + 10 * k)):
            a = rng.uniform(0, 6.28)
            d = rng.uniform(base_r * 1.1, 0.92)
            r = rng.uniform(0.015, 0.06) * (1.1 - d)
            px, py = math.cos(a) * d, math.sin(a) * d
            blot = np.maximum(blot, 1 - smoothstep(r * 0.8, r, np.sqrt((cx - px) ** 2 + (cy - py) ** 2)))
        # pooled ink: darker rim, lighter centre (wet edge of sumi)
        rim = smoothstep(r_edge - 0.10, r_edge - 0.01, rad) * blot
        dens = np.clip(0.80 + 0.2 * rim - 0.15 * n_tex, 0, 1)
        y0, x0 = (i // n) * cell, (i % n) * cell
        atlas[y0:y0 + cell, x0:x0 + cell] = np.dstack([dens, rim, n_tex, blot])
    save("ink_blots_atlas", atlas)


def mountain_layers(rng):
    """Four horizontal bands, each a haboku-style mountain range silhouette.

    A = coverage, R = wash density (dark ridge line fading downward into mist).
    Bands are tileable horizontally so the cards can wrap around the level.
    """
    w, band_h, bands = 2048, 256, 4
    out = np.zeros((band_h * bands, w, 4))
    x = np.arange(w)
    for b in range(bands):
        ridge = np.zeros(w)
        # periodic ridge from a sum of harmonics (tileable)
        for octave, amp in ((2, 0.30), (5, 0.16), (11, 0.08), (23, 0.04), (47, 0.02)):
            for _ in range(2):
                ridge += amp * rng.uniform(0.4, 1.0) * np.sin(2 * np.pi * octave * x / w + rng.uniform(0, 6.28))
        # sharpen peaks (ink painters exaggerate verticals)
        ridge = (ridge - ridge.min()) / (ridge.max() - ridge.min())
        ridge = 0.18 + 0.68 * ridge ** (1.4 + 0.3 * b)
        yy = np.linspace(1, 0, band_h)[:, None]  # 1 at top of band
        top = ridge[None, :]
        inside = yy < top
        depth_below = np.clip((top - yy) / np.maximum(top, 1e-3), 0, 1)
        n = spectral_noise((band_h, w), 1.3, rng)
        streaks = spectral_noise((band_h, w), 1.1, rng, aniso=(0.08, 1.0))  # vertical texture strokes
        dens = (1 - smoothstep(0.0, 0.55 + 0.2 * n, depth_below)) * (0.75 + 0.25 * streaks)
        cov = inside * smoothstep(0.0, 0.015, top - yy)
        # mist eats the foot of the mountain
        cov = cov * (1 - smoothstep(0.35, 0.95 + 0.1 * n, depth_below))
        y0 = b * band_h
        out[y0:y0 + band_h] = np.dstack([dens, streaks, n, cov])
    save("mountain_layers", out)


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(1103)
    paper_grain(rng)
    wash_noise(rng)
    brush_stroke(rng)
    ink_blots(rng)
    mountain_layers(rng)


main()

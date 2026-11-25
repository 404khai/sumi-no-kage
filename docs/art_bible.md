# Sumi no Kage — Art Bible (v1)

> A sumi-e painting that you can walk into. Ink on washi, brought into three dimensions.

![palette](renders/palette.png)
*Paper · sei · tan · jū · nō · shō · shu (vermilion)*

## 1. Pillars

1. **Ink and paper, nothing else.** Every pixel is either paper, a tone of ink, or (rarely) vermilion. A full-screen grade enforces this (`ink_post.gdshader` collapses everything except strong reds to value).
2. **The figure is the darkest thing on the page.** Kage is drawn in *shō* and *nō*; the world sits in *tan* and *sei* and dissolves into paper with distance. If a background element competes with the character's value, it is wrong.
3. **Negative space is a material.** Mist and empty paper are as deliberate as geometry. Distance fades to paper, never to grey or blue.
4. **Brush logic over surface detail.** Shape is explained by contour, rim and two or three tonal bands, not by texture noise or specular highlights. Detail lives in silhouettes (tattered hems, notched spines, streaming ties).
5. **Red is a seal, not a colour scheme.** Vermilion (*shu*) appears only where the eye must land: cords and tassels, the torii, bridge rails, blood-ink on hits. On screen it should cover well under 3% of the image.

## 2. Tone scale (the five inks)

Classical sumi-e names five tones of ink. They are the only greys we use, stored in `tools/blender/lib/sumi.py` (`INK_TONES`) and `game/shaders/ink_common.gdshaderinc`.

| Tone | Kanji | sRGB value | Use |
|---|---|---|---|
| Paper | 紙 | 0.92 (warm, `#EBE7DD`) | sky, fog, distance, lit ground |
| Sei — clear | 清 | 0.80 | far mountains, mist-lit stone |
| Tan — light | 淡 | 0.52 | mid-ground architecture, bamboo |
| Jū — heavy | 重 | 0.22 | wood, wraps, sash, near props |
| Nō — thick | 濃 | 0.10 | Kage's clothing, roofs, foliage |
| Shō — burnt | 焦 | 0.035 | contour lines, eyes, the hood, crevices |
| Shu — vermilion | 朱 | `#9E1C14` (0.62, 0.11, 0.08) | accents only |

**Value budget per frame:** the character occupies *shō–jū*; anything within ~6 m of the camera may go down to *jū*; beyond that the fog pulls everything toward *sei*/paper.

## 3. Shape language

- **Character:** tapering verticals (ties, sash tails, hakama gathering into wraps), a rounded hooded head with one horizontal pale slit (the eyes), angular tatters at every hem. Read as a single brushstroke at 30 m.
- **Architecture:** heavy, dark roofs with upswept eaves over light posts, so the roof is the brush mark and the body is negative space.
- **Nature:** pines with flat, pressed "cloud pads" (the brush laid on its side); bamboo as vertical strokes; mountains as *haboku* (splashed-ink) silhouettes whose feet dissolve into mist.
- **Weapons:** long thin negative-space blades with a hard ink spine, dark grips, small red accents (see `weapon_design_language.md`).

## 4. Materials

There are no PBR materials in the game. Every surface uses `ink_surface.gdshader` or `ink_blade.gdshader`:

| Feature | How | Why |
|---|---|---|
| Two-band ink ramp | custom `light()`; shadow, half-tone, lit | painters use 2–3 washes, not gradients |
| Brush-broken band edges | wash noise offsets the band threshold | terminators bleed like wet ink |
| Bristle streaks | `brush_stroke.png` G channel along UV | cloth reads as brushed, not printed |
| Ink rim | fresnel mixed toward *shō* | the contour line *inside* the silhouette |
| Ink pooling | vertex colour R baked from curvature | folds and crevices gather ink |
| Brush outline | inverted hull with noise-varied width | loaded-brush contour, thicker on dark masses |
| No specular | `specular_disabled` | glossy highlights break the illusion |

Avoid: anime cel shading with hard black shadows and coloured rim lights, photoreal roughness/metal response, bloom, chromatic aberration, colour fog.

## 5. Light and atmosphere

- One key light (the moon), upper-left, soft shadows. Ambient is flat paper-white at ~0.4.
- Exponential + height fog, coloured exactly as paper. It is the primary depth cue and the main "wash" tool.
- The sky is paper with a faint wash bloom and a pale ink moon (`ink_sky.gdshader`).
- The far landscape is three wrap-around *haboku* mountain bands, each paler than the one in front.

## 6. Effects (ink, never light)

| Event | Effect |
|---|---|
| Weapon swing | dry-brush ribbon that breaks into bristle gaps as it ages (`InkTrail`) |
| Hit | splatter of ink blots; vermilion blots for blood (`InkBurst`) |
| Phantom Step | body dissolves into ink, a brush streak marks the path, re-forms at the destination (`PhantomStepVFX`) |

No glows, no additive particles, no light emission. Energy is shown with **speed of the brush** (stroke shape, dryness), not brightness.

## 7. Reference

Public-domain works that define the target:
- Sesshū Tōyō, *Haboku Sansui* (1495): splashed-ink landscape, the model for the mountain bands.
- Hasegawa Tōhaku, *Shōrin-zu byōbu* (Pine Trees screen, late 16th c.): mist as subject, pines emerging from paper.
- Sesshū, *Autumn and Winter Landscapes*: hard contour strokes against wash.
- Edo-period *ninja* illustration (Hokusai, *Hokusai Manga*): the shinobi silhouette, the hood tie and the tabi.

Weapon reference images supplied by the director live in `docs/reference/` (see `weapon_design_language.md` for how they translate into this palette).

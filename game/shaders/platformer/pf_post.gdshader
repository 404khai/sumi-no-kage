// Platformer screen pass. Unlike ink_post it keeps colour (the heroes are
// coloured ink now). Washi grain + vignette on both sides; on the neon side a
// touch of chromatic split and scanlines. `wipe` drives the portal transition:
// an ink flood that closes in from the edges with a ragged brush front.
shader_type canvas_item;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform sampler2D paper_grain : filter_linear_mipmap, repeat_enable;
uniform sampler2D wash_noise : filter_linear_mipmap, repeat_enable;
uniform float zone : hint_range(0.0, 1.0) = 0.0;
uniform float wipe : hint_range(0.0, 1.0) = 0.0;
uniform float grain_strength = 0.16;

void fragment() {
	vec2 uv = SCREEN_UV;
	float ca = 0.0018 * zone;
	vec3 c;
	c.r = texture(screen_tex, uv + vec2(ca, 0.0)).r;
	c.g = texture(screen_tex, uv).g;
	c.b = texture(screen_tex, uv - vec2(ca, 0.0)).b;
	vec2 px = FRAGCOORD.xy / vec2(textureSize(paper_grain, 0));
	vec4 pg = texture(paper_grain, px);
	float g = 0.5 + (pg.b - 0.5) * 0.8 + (pg.r - 0.5) * 0.35;
	float lum = dot(c, vec3(0.299, 0.587, 0.114));
	c *= 1.0 + (g - 0.5) * grain_strength * mix(0.4 + 0.6 * lum, 0.5, zone);
	c *= 1.0 - zone * 0.06 * step(0.5, fract(FRAGCOORD.y * 0.5));
	vec2 q = uv - 0.5;
	float v = smoothstep(0.38, 0.8, length(q * vec2(1.1, 1.0)));
	c = mix(c, c * mix(0.6, 0.35, zone), v * 0.45);
	// ink flood
	float n = texture(wash_noise, uv * vec2(2.2, 1.3)).r;
	float d = length(q * vec2(1.78, 1.0));
	float front = (1.0 - wipe) * 1.15 - 0.05;
	float flood = smoothstep(front - 0.02, front + 0.02, d + (n - 0.5) * 0.25);
	c = mix(c, SUMI_INK, flood * step(0.001, wipe));
	COLOR = vec4(c, 1.0);
}

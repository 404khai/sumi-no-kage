// Platformer sky, full-screen behind everything. zone 0 = washi paper with a
// vermilion sun and ink-wash clouds; zone 1 = the far side of the portal:
// violet dusk, a magenta horizon, stars. `zone` is animated during the wipe.
shader_type canvas_item;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D wash_noise : filter_linear_mipmap, repeat_enable;
uniform float zone : hint_range(0.0, 1.0) = 0.0;
uniform float scroll = 0.0;

vec3 ink_sky(vec2 uv) {
	vec3 c = mix(SUMI_PAPER, SUMI_PAPER * 0.86, uv.y);
	vec2 sun = vec2(0.72, 0.28);
	float d = length((uv - sun) * vec2(1.78, 1.0));
	c = mix(c, SUMI_SHU, smoothstep(0.105, 0.098, d));
	float n = texture(wash_noise, uv * vec2(1.6, 0.7) + vec2(scroll * 0.02 + TIME * 0.004, 0.0)).r;
	float band = smoothstep(0.55, 0.75, n) * smoothstep(0.55, 0.15, uv.y);
	c = mix(c, SUMI_INK, band * 0.12);
	return c;
}

vec3 neon_sky(vec2 uv) {
	vec3 top = vec3(0.04, 0.02, 0.1);
	vec3 mid = vec3(0.22, 0.05, 0.32);
	vec3 hor = vec3(0.95, 0.25, 0.55);
	vec3 c = mix(top, mid, smoothstep(0.0, 0.6, uv.y));
	c = mix(c, hor, smoothstep(0.55, 0.78, uv.y) * 0.8);
	vec2 g = floor(uv * vec2(320.0, 180.0));
	float s = step(0.9965, sumi_hash(g)) * smoothstep(0.6, 0.0, uv.y);
	c += vec3(s) * (0.6 + 0.4 * sin(TIME * 3.0 + g.x));
	// a huge dim sun cut by horizontal bars
	float d = length((uv - vec2(0.3, 0.62)) * vec2(1.78, 1.0));
	float bars = step(0.5, fract(uv.y * 60.0)) + step(uv.y, 0.55);
	c = mix(c, vec3(1.0, 0.55, 0.3), smoothstep(0.2, 0.19, d) * clamp(bars, 0.0, 1.0) * 0.7);
	return c;
}

void fragment() {
	COLOR = vec4(mix(ink_sky(UV), neon_sky(UV), zone), 1.0);
}

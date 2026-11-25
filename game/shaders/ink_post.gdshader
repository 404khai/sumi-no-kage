// Full-screen paper pass (one cheap pass): enforces the ink palette by
// collapsing colour to value except for vermilion, multiplies washi grain,
// and darkens the frame edges like ink soaking into the sheet border.
shader_type canvas_item;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform sampler2D paper_grain : filter_linear_mipmap, repeat_enable;
uniform float grain_strength : hint_range(0.0, 1.0) = 0.14;
uniform float grain_scale = 1.0;
uniform float vignette : hint_range(0.0, 1.0) = 0.25;
uniform float keep_red : hint_range(0.0, 1.0) = 1.0;

void fragment() {
	vec3 c = texture(screen_tex, SCREEN_UV).rgb;
	float lum = dot(c, vec3(0.299, 0.587, 0.114));
	// redness: only strong warm hues survive the grade
	float red = clamp((c.r - max(c.g, c.b)) * 3.0, 0.0, 1.0) * keep_red;
	vec3 graded = mix(vec3(lum) * vec3(1.0, 0.985, 0.95), c, red);
	vec2 px = FRAGCOORD.xy / vec2(textureSize(paper_grain, 0)) * grain_scale;
	vec4 pg = texture(paper_grain, px);
	float g = 0.5 + (pg.b - 0.5) * 0.8 + (pg.r - 0.5) * 0.35;  // fine tooth + a little fibre
	graded *= 1.0 + (g - 0.5) * grain_strength * (0.4 + 0.6 * lum);
	vec2 q = SCREEN_UV - 0.5;
	float v = smoothstep(0.35, 0.75, length(q * vec2(1.1, 1.0)));
	graded = mix(graded, graded * 0.55, v * vignette);
	COLOR = vec4(graded, 1.0);
}

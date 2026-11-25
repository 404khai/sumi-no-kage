// Blade steel in ink: pale negative-space steel, a misty hamon line, dark spine
// (mune), the family inlay (channel + ring, see docs/weapon_design_language.md)
// and a stepped glint that sweeps with the view.
// UV contract (build_daggers.py): U = spine(0) -> edge(1), V = habaki(0) -> tip(1).
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_disabled;

#include "res://shaders/ink_common.gdshaderinc"

uniform vec3 steel_color : source_color = vec3(0.95, 0.94, 0.91);
uniform vec3 jigane_color : source_color = vec3(0.72, 0.72, 0.72);
uniform float hamon_position : hint_range(0.0, 1.0) = 0.62;
uniform float hamon_wave = 0.07;
uniform float hamon_frequency = 18.0;
uniform vec3 inlay_color : source_color = vec3(0.028, 0.027, 0.03); // set to SHU for the red variant
uniform float inlay_strength : hint_range(0.0, 1.0) = 1.0;
uniform float shadow_level : hint_range(0.0, 1.0) = 0.78;
uniform sampler2D wash_noise : hint_default_white, filter_linear_mipmap, repeat_enable;
instance uniform float dissolve : hint_range(0.0, 1.0) = 0.0;  // Phantom Step, per instance
uniform float glint_strength : hint_range(0.0, 1.0) = 0.7;

varying float v_n;

void fragment() {
	float u = UV.x;
	float v = UV.y;
	float n = texture(wash_noise, vec2(u * 0.4, v * 2.0)).b;
	v_n = n;
	float wave = hamon_wave * sin(v * hamon_frequency + n * 3.0) + 0.06 * (n - 0.5);
	float hamon = smoothstep(hamon_position + wave - 0.04, hamon_position + wave + 0.02, u);
	vec3 col = mix(jigane_color, steel_color, hamon);
	// mune: the spine is drawn as a hard ink line
	col = mix(col, SUMI_INK, 1.0 - smoothstep(0.03, 0.09, u));
	// fuller channel along the upper blade
	float channel = (1.0 - smoothstep(0.0, 0.03, abs(u - 0.26))) * smoothstep(0.10, 0.16, v) * (1.0 - smoothstep(0.62, 0.70, v));
	// ring mark near the base
	vec2 rc = vec2((u - 0.40) * 1.0, (v - 0.10) * 2.6);
	float ring = 1.0 - smoothstep(0.0, 0.022, abs(length(rc) - 0.11));
	col = mix(col, inlay_color, clamp(channel + ring, 0.0, 1.0) * inlay_strength);
	// view-dependent glint: a single bright stepped streak across the flat
	float g = abs(dot(NORMAL, normalize(vec3(0.0, 0.3, 1.0)) + VIEW * 0.6));
	float glint = step(0.92, fract(v * 1.3 + g * 0.8)) * glint_strength * hamon;
	col = mix(col, SUMI_PAPER, glint);
	if (dissolve > 0.0 && n < dissolve) {
		discard;
	}
	ALBEDO = col;
}

void light() {
	float ndl = clamp(dot(NORMAL, LIGHT), 0.0, 1.0) * ATTENUATION;
	float b = sumi_bands(ndl + (v_n - 0.5) * 0.2, 0.15, 0.5, 0.04);
	DIFFUSE_LIGHT += mix(shadow_level, 1.0, b) * LIGHT_COLOR / PI;
}

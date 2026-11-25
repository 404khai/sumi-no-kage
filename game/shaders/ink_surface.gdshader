// Sumi-e surface: stepped "ink ramp" lighting, brush-broken band edges,
// grazing-angle ink rims, cavity pooling from vertex colour R, and an
// ink-dissolve used by the Phantom Step.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_disabled;

#include "res://shaders/ink_common.gdshaderinc"

group_uniforms tone;
uniform vec3 base_color : source_color = vec3(0.12);
uniform float shadow_level : hint_range(0.0, 1.0) = 0.45;   // fraction of light left in the shadow band
uniform float band_low : hint_range(0.0, 1.0) = 0.18;
uniform float band_high : hint_range(0.0, 1.0) = 0.55;
uniform float band_softness : hint_range(0.0, 0.3) = 0.05;
uniform float light_gain = 1.0;

group_uniforms brush;
uniform sampler2D wash_noise : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D brush_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool use_triplanar = false;          // static environment meshes
uniform float noise_scale = 1.5;
uniform float band_noise : hint_range(0.0, 1.0) = 0.25; // how much the wash breaks the band edges
uniform float streak_strength : hint_range(0.0, 1.0) = 0.12;
uniform vec2 streak_scale = vec2(1.0, 4.0);

group_uniforms ink;
uniform float rim_ink : hint_range(0.0, 1.0) = 0.55;
uniform float rim_width : hint_range(0.0, 1.0) = 0.32;
uniform float cavity_strength : hint_range(0.0, 1.0) = 0.6;
uniform float height_wash : hint_range(0.0, 1.0) = 0.0;   // darken toward the base (vertex colour G)

group_uniforms dissolve;
instance uniform float dissolve : hint_range(0.0, 1.0) = 0.0;  // Phantom Step, per instance
uniform float dissolve_edge : hint_range(0.0, 0.3) = 0.08;
uniform vec3 dissolve_edge_color : source_color = vec3(0.028, 0.027, 0.03);

varying vec3 v_world_pos;
varying vec3 v_world_normal;
varying vec4 v_color;
varying float v_noise;

void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_color = COLOR;
}

void fragment() {
	float n;
	float streak;
	if (use_triplanar) {
		n = sumi_triplanar(wash_noise, v_world_pos, v_world_normal, noise_scale * 0.08, 1);
		streak = sumi_triplanar(brush_tex, v_world_pos, v_world_normal, noise_scale * 0.05, 1);
	} else {
		n = texture(wash_noise, UV * noise_scale).g;
		streak = texture(brush_tex, UV * streak_scale).g;
	}
	v_noise = n;

	vec3 col = base_color * (1.0 - streak_strength * (streak - 0.5));
	// ink pools in crevices
	col = mix(col, SUMI_INK, (1.0 - v_color.r) * cavity_strength);
	col = mix(col, col * 0.55, (1.0 - v_color.g) * height_wash);
	// grazing-angle rim: the brush outline inside the silhouette
	float fres = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float rim = smoothstep(1.0 - rim_width + 0.15 * (n - 0.5), 1.0, fres);
	col = mix(col, SUMI_INK, rim * rim_ink);

	if (dissolve > 0.0) {
		float d = n * 0.7 + streak * 0.3;
		if (d < dissolve) {
			discard;
		}
		col = mix(col, dissolve_edge_color, 1.0 - smoothstep(dissolve, dissolve + dissolve_edge, d));
	}
	ALBEDO = col;
}

void light() {
	float ndl = clamp(dot(NORMAL, LIGHT), 0.0, 1.0) * ATTENUATION;
	float x = ndl + (v_noise - 0.5) * band_noise;
	float b = sumi_bands(x, band_low, band_high, band_softness);
	DIFFUSE_LIGHT += mix(shadow_level, 1.0, b) * LIGHT_COLOR * light_gain / PI;
}

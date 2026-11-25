// Inverted-hull brush outline (used as next_pass). Width varies along the mesh
// with the wash noise so the contour reads as a loaded brush, not a CAD line.
shader_type spatial;
render_mode unshaded, cull_front, depth_draw_opaque, specular_disabled, shadows_disabled;

#include "res://shaders/ink_common.gdshaderinc"

uniform float width = 0.004;            // metres at 1 m from the camera
uniform float width_variation : hint_range(0.0, 1.0) = 0.6;
uniform float max_distance_scale = 10.0;
uniform vec3 ink_color : source_color = vec3(0.028, 0.027, 0.03);
uniform sampler2D wash_noise : hint_default_white, filter_linear, repeat_enable;
instance uniform float dissolve : hint_range(0.0, 1.0) = 0.0;  // Phantom Step, per instance

varying float v_n;

void vertex() {
	vec4 view_pos = MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
	float dist = clamp(-view_pos.z, 0.5, max_distance_scale);
	float n = textureLod(wash_noise, UV * 2.0, 0.0).b;
	v_n = n;
	float w = width * dist * mix(1.0 - width_variation, 1.0 + width_variation, n);
	VERTEX += NORMAL * w;
}

void fragment() {
	if (dissolve > 0.0 && v_n < dissolve) {
		discard;
	}
	ALBEDO = ink_color;
}

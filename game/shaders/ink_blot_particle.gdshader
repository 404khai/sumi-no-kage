// Ink-splatter particles. Picks one of 16 blots per particle and "dries" it
// away with a noise threshold instead of a plain fade.
shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_draw_never, shadows_disabled;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D blot_atlas : source_color, filter_linear_mipmap, repeat_disable;
uniform vec3 ink_color : source_color = vec3(0.028, 0.027, 0.03);
uniform float atlas_size = 4.0;

varying float v_frame;

void vertex() {
	// camera-facing billboard that keeps the particle's scale and spin
	mat4 bb = mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	bb = bb * mat4(vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0), vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0),
			vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0), vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_MATRIX = VIEW_MATRIX * bb;
	v_frame = floor(sumi_hash(vec2(float(INSTANCE_ID), 7.0)) * atlas_size * atlas_size);
}

void fragment() {
	vec2 cell = vec2(mod(v_frame, atlas_size), floor(v_frame / atlas_size));
	vec4 t = texture(blot_atlas, (cell + UV) / atlas_size);
	float life = COLOR.a;
	float coverage = t.a * smoothstep(1.0 - life, 1.0 - life + 0.2, t.b * 0.5 + 0.5 * life);
	ALBEDO = mix(ink_color, ink_color * 0.6, t.g);
	ALPHA = coverage;
}

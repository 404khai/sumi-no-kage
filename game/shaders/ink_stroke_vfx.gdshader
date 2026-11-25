// Brush-stroke ribbon for weapon trails and the Phantom Step streak.
// UV.x: 0 at the newest point (stroke head) -> 1 at the oldest (dry tail).
// UV.y: 0..1 across the ribbon. COLOR.a: per-vertex life (1 new -> 0 expired).
shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_draw_never, shadows_disabled;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D brush_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform vec3 ink_color : source_color = vec3(0.028, 0.027, 0.03);
uniform float opacity : hint_range(0.0, 1.0) = 1.0;
uniform float dry_speed = 1.2;   // how fast the ink breaks up as it ages

void fragment() {
	vec4 b = texture(brush_tex, vec2(UV.x * 0.95 + 0.02, UV.y));
	float life = COLOR.a;
	// as the stroke ages, the bristle gaps open up from the tail toward the head
	float dry = clamp((1.0 - life) * dry_speed, 0.0, 1.0);
	float coverage = clamp(b.a * 1.4, 0.0, 1.0) * smoothstep(dry * 0.9, dry * 0.9 + 0.15, b.g * 0.6 + 0.4 * (1.0 - UV.x));
	ALBEDO = mix(ink_color, SUMI_PAPER, (1.0 - b.r) * 0.12);
	ALPHA = coverage * opacity * smoothstep(0.0, 0.15, life);
}

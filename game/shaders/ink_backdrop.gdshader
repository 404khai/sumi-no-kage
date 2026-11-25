// Haboku mountain layers on wrap-around cylinders. Each layer picks one band of
// mountain_layers.png and fades toward the paper with distance (aerial perspective).
shader_type spatial;
render_mode unshaded, blend_mix, cull_disabled, depth_draw_never, shadows_disabled, fog_disabled;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D layers : source_color, filter_linear_mipmap, repeat_enable;
uniform float band = 0.0;           // 0..3
uniform float repeats = 2.0;
uniform float u_offset = 0.0;
uniform float ink_amount : hint_range(0.0, 1.0) = 0.6;  // 1 = near & dark, low = far & faint
uniform vec3 ink_color : source_color = vec3(0.028, 0.027, 0.03);

void fragment() {
	vec2 uv = vec2(UV.x * repeats + u_offset, (band + clamp(UV.y, 0.002, 0.998)) / 4.0);
	vec4 t = texture(layers, uv);
	vec3 col = mix(SUMI_PAPER, ink_color, t.r * ink_amount);
	ALBEDO = col;
	ALPHA = t.a * smoothstep(0.0, 0.25, t.r * ink_amount + 0.1);
}

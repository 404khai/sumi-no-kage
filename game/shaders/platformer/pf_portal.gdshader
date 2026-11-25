// The rift between the shrine and the far side. Outside: a ragged ring of ink
// being pulled inward. Inside: a window onto the neon zone (gradient, grid
// rushing toward the viewer). `open` grows it from a slit.
shader_type canvas_item;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D wash_noise : filter_linear_mipmap, repeat_enable;
uniform float open : hint_range(0.0, 1.0) = 1.0;
uniform float pulse = 0.0;

void fragment() {
	vec2 p = (UV - 0.5) * vec2(1.0, 1.0);
	p.x *= 1.55;
	float r = length(p);
	float a = atan(p.y, p.x);
	float swirl = texture(wash_noise, vec2(a / 6.2831 + TIME * 0.08 - r * 0.6, r * 1.3 - TIME * 0.25)).r;
	float edge = 0.4 * open + (swirl - 0.5) * 0.09;
	float inside = smoothstep(edge, edge - 0.015, r);
	float ring = smoothstep(edge + 0.11 + swirl * 0.05, edge, r) * (1.0 - inside);
	// inner view: neon dusk + perspective grid
	vec3 inner = mix(vec3(0.07, 0.03, 0.16), vec3(0.95, 0.25, 0.6), smoothstep(0.1, -0.3, p.y));
	float depth = 0.12 / max(0.02, p.y + 0.16);
	vec2 grid = vec2(p.x * depth * 6.0, depth + TIME * 1.5);
	float lines = max(step(0.93, fract(grid.x)), step(0.9, fract(grid.y)));
	inner += vec3(0.3, 0.95, 1.0) * lines * step(-0.15, p.y) * 0.6;
	inner += vec3(0.3, 0.95, 1.0) * smoothstep(0.06, 0.0, abs(r - edge + 0.01)) * (1.2 + pulse);
	vec3 col = mix(SUMI_INK, inner, inside);
	float alpha = max(inside, ring * (0.75 + swirl * 0.25));
	// flecks of ink torn off the rim
	float fleck = step(0.8, texture(wash_noise, UV * 3.0 + vec2(TIME * 0.3, 0.0)).g) * smoothstep(edge + 0.2, edge + 0.05, r);
	alpha = max(alpha, fleck * 0.9 * (1.0 - inside));
	COLOR = vec4(col, alpha * smoothstep(0.0, 0.08, open));
}

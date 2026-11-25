// Paper sky: warm washi with a faint wash bloom and a pale ink moon.
shader_type sky;

#include "res://shaders/ink_common.gdshaderinc"

uniform sampler2D wash_noise : filter_linear_mipmap, repeat_enable;
uniform vec3 moon_dir = vec3(-0.35, 0.42, -0.84);
uniform float moon_size = 0.035;
uniform float wash_strength = 0.06;

void sky() {
	vec3 d = normalize(EYEDIR);
	vec2 uv = vec2(atan(d.x, d.z) / 6.2831853, d.y * 0.5);
	float n = texture(wash_noise, uv * vec2(3.0, 2.0)).r;
	vec3 col = SUMI_PAPER * (1.0 - wash_strength * smoothstep(0.0, 0.6, d.y) * n);
	float m = distance(d, normalize(moon_dir));
	float moon = 1.0 - smoothstep(moon_size, moon_size + 0.004 + 0.004 * n, m);
	float halo = (1.0 - smoothstep(moon_size, moon_size * 4.0, m)) * 0.04;
	col = mix(col, col * 0.86, moon * 0.5 + halo);
	COLOR = col;
}

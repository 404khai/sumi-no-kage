// Shared ink-painting palette and helpers. Values mirror docs/art_bible.md.
const vec3 SUMI_PAPER = vec3(0.92, 0.905, 0.865);   // washi, slightly warm
const vec3 SUMI_INK = vec3(0.028, 0.027, 0.03);     // 焦 burnt ink
const vec3 SUMI_SHU = vec3(0.62, 0.11, 0.08);       // 朱 vermilion

float sumi_hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

// Triplanar single-channel sample (static meshes only: world space swims on skinned meshes).
float sumi_triplanar(sampler2D tex, vec3 world_pos, vec3 world_normal, float scale, int channel) {
	vec3 w = pow(abs(world_normal), vec3(4.0));
	w /= (w.x + w.y + w.z);
	vec4 x = texture(tex, world_pos.zy * scale);
	vec4 y = texture(tex, world_pos.xz * scale);
	vec4 z = texture(tex, world_pos.xy * scale);
	vec4 s = x * w.x + y * w.y + z * w.z;
	return s[channel];
}

// Two-step ink ramp: shadow / half-tone / lit, with soft (bleeding) edges.
float sumi_bands(float x, float b1, float b2, float softness) {
	return 0.5 * smoothstep(b1 - softness, b1 + softness, x)
		+ 0.5 * smoothstep(b2 - softness, b2 + softness, x);
}

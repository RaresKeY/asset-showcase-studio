shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back, wireframe;

uniform vec4 line_color : source_color = vec4(0.12, 0.82, 1.0, 0.34);
uniform float line_offset : hint_range(0.0, 0.02, 0.0001) = 0.0015;

void vertex() {
	// Keep the overlay just above the textured surface without revealing
	// occluded lines. Compensate for the auto-fit transform so line_offset stays
	// approximately world-scale; disabling depth testing would create X-rays.
	float model_scale = max(
		length(MODEL_MATRIX[0].xyz),
		max(length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz))
	);
	VERTEX += NORMAL * (line_offset / max(model_scale, 0.000001));
}

void fragment() {
	ALBEDO = line_color.rgb;
	ALPHA = line_color.a;
	ROUGHNESS = 0.32;
}

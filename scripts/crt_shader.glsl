// CRT / retro TV pixel shader for a GLSL TOP.
//
// Wiring:
//   Text DAT 'crt_shader' -> File: scripts/crt_shader.glsl, Sync to File On
//   GLSL TOP 'crt1'       -> Pixel Shader: crt_shader, input: your video TOP
//
// Optional (for animated noise/rolling bar/flicker): on the GLSL TOP's
// Vectors 1 page set Uniform Name 1 to uTime and give Value 1's x the
// expression absTime.seconds. Without it the effect is static but works.
//
// All the knobs live in the #defines below - edit and save, the DAT syncs.

#define CURVATURE        0.18   // screen bulge; 0 = flat
#define SCAN_INTENSITY   0.22   // darkness of scanlines
#define SCAN_DENSITY     2.0    // higher = more scanlines (2 = twice as many)
#define MASK_INTENSITY   0.12   // RGB phosphor stripe strength (ignored in mono)
#define MONOCHROME       1      // 1 = single-color tube, 0 = full color
#define MONO_TINT        vec3(0.92, 1.0, 0.94)  // subtle green; vec3(1.0) b/w, vec3(1.0,0.7,0.3) amber, vec3(0.75,1.0,0.8) heavy green
#define CONTRAST         1.35   // 1.0 = neutral; higher = punchier blacks/whites
#define ABERRATION       2.0    // color fringing at the edges, in pixels
#define VIGNETTE         0.45   // corner darkening
#define NOISE_AMT        0.05   // static/snow
#define FLICKER_AMT      0.03   // whole-frame brightness flicker
#define ROLLBAR_AMT      0.07   // brightness of the rolling band
#define ROLLBAR_SPEED    0.25   // bands per second traveling up the screen
#define CORNER_RADIUS    0.035  // rounded tube corners (0 = square)

uniform float uTime;

layout(location = 0) out vec4 fragColor;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

vec2 curveUV(vec2 uv) {
	uv = uv * 2.0 - 1.0;
	float r2 = dot(uv, uv);
	uv *= 1.0 + CURVATURE * r2 * 0.5;
	return uv * 0.5 + 0.5;
}

void main() {
	vec2 res = uTD2DInfos[0].res.zw;
	vec2 uv = curveUV(vUV.st);

	// outside the curved tube: black
	if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
		fragColor = TDOutputSwizzle(vec4(0.0, 0.0, 0.0, 1.0));
		return;
	}

	vec2 fromC = uv - 0.5;

	// chromatic aberration, growing toward the edges
	vec2 ab = fromC * ABERRATION * length(fromC) / res;
	float r = texture(sTD2DInputs[0], uv + ab).r;
	float g = texture(sTD2DInputs[0], uv).g;
	float b = texture(sTD2DInputs[0], uv - ab).b;
	vec3 col = vec3(r, g, b);

	// monochrome tube: collapse to luminance, tinted like an old phosphor
	#if MONOCHROME
	float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
	lum = clamp((lum - 0.5) * CONTRAST + 0.5, 0.0, 1.0);
	col = MONO_TINT * lum;
	#else
	col = clamp((col - 0.5) * CONTRAST + 0.5, 0.0, 1.0);
	#endif

	// scanlines
	float scan = 1.0 - SCAN_INTENSITY * (0.5 + 0.5 * cos(uv.y * res.y * 3.14159265 * SCAN_DENSITY));
	col *= scan;

	// RGB phosphor stripes (color mode only - stripes on mono look wrong)
	#if !MONOCHROME
	int idx = int(mod(gl_FragCoord.x, 3.0));
	vec3 mask = vec3(1.0 - MASK_INTENSITY);
	mask[idx] = 1.0 + MASK_INTENSITY * 0.5;
	col *= mask;
	#endif

	// rolling brightness band traveling up the screen
	col *= 1.0 + ROLLBAR_AMT * sin((uv.y - uTime * ROLLBAR_SPEED) * 6.2831853);

	// static / snow
	col += (hash(uv * res + vec2(uTime * 123.0, uTime * 311.0)) - 0.5) * NOISE_AMT;

	// whole-frame flicker
	col *= 1.0 + FLICKER_AMT * (hash(vec2(floor(uTime * 60.0), 3.7)) - 0.5) * 2.0;

	// vignette
	col *= clamp(1.0 - VIGNETTE * dot(fromC, fromC) * 2.5, 0.0, 1.0);

	// rounded tube corners
	vec2 cc = abs(fromC) - (vec2(0.5) - CORNER_RADIUS);
	float cdist = length(max(cc, 0.0));
	col *= 1.0 - smoothstep(CORNER_RADIUS * 0.7, CORNER_RADIUS, cdist);

	fragColor = TDOutputSwizzle(vec4(col, 1.0));
}

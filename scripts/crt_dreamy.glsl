// Dreamy / airy CRT pixel shader for a GLSL TOP.
// A softer, brighter cousin of crt_shader.glsl: light scanlines, lifted blacks,
// pastel wash, gentle bloom-ish glow, soft chromatic aberration. Meant to feel
// hazy and bright rather than dark and heavy.
//
// Wiring:
//   Text DAT 'crt_dreamy' -> File: scripts/crt_dreamy.glsl, Sync to File On
//   GLSL TOP 'crt_dream'  -> Pixel Shader: crt_dreamy, input 0: the crossfaded channel feed
//   (optional) uTime uniform = absTime.seconds  for the animated shimmer

#define CURVATURE       0.08    // very gentle bulge (0 = flat)
#define SCAN_INTENSITY  0.10    // faint scanlines
#define SCAN_DENSITY    1.6
#define ABERRATION      1.4     // soft rgb fringing
#define VIGNETTE        0.12    // barely-there corner shade
#define BLACK_LIFT      0.10    // raise shadows -> airy, hazy
#define BRIGHTNESS      1.08    // gentle overall lift
#define DESAT           0.25    // pull toward pastel (0 = full color, 1 = grey)
#define TINT            vec3(1.03, 0.99, 1.05)   // faint pink/lilac wash
#define GLOW            0.35    // soft bloom of bright areas
#define GLOW_RADIUS     2.5     // px spread of the glow sampling

uniform float uTime;

layout(location = 0) out vec4 fragColor;

vec2 curveUV(vec2 uv){
	uv = uv*2.0 - 1.0;
	uv *= 1.0 + CURVATURE * dot(uv,uv) * 0.5;
	return uv*0.5 + 0.5;
}

vec3 sampleGlow(vec2 uv, vec2 px){
	// cheap 4-tap soft glow of the brighter pixels around this one
	vec3 g = vec3(0.0);
	g += texture(sTD2DInputs[0], uv + vec2( GLOW_RADIUS,0)*px).rgb;
	g += texture(sTD2DInputs[0], uv + vec2(-GLOW_RADIUS,0)*px).rgb;
	g += texture(sTD2DInputs[0], uv + vec2(0, GLOW_RADIUS)*px).rgb;
	g += texture(sTD2DInputs[0], uv + vec2(0,-GLOW_RADIUS)*px).rgb;
	g *= 0.25;
	return max(g - 0.5, 0.0);   // only bright areas bloom
}

void main(){
	vec2 res = uTD2DInfos[0].res.zw;
	vec2 px  = 1.0/res;
	vec2 uv  = curveUV(vUV.st);

	if(uv.x<0.0||uv.x>1.0||uv.y<0.0||uv.y>1.0){
		fragColor = TDOutputSwizzle(vec4(vec3(0.96,0.95,0.98),1.0)); // soft off-white, not black
		return;
	}

	vec2 fromC = uv - 0.5;
	vec2 ab = fromC * ABERRATION * length(fromC) * px;
	vec3 col = vec3(
		texture(sTD2DInputs[0], uv+ab).r,
		texture(sTD2DInputs[0], uv).g,
		texture(sTD2DInputs[0], uv-ab).b);

	// soft glow / bloom
	col += sampleGlow(uv, px) * GLOW;

	// faint scanlines (kept subtle)
	float scan = 1.0 - SCAN_INTENSITY*(0.5+0.5*cos(uv.y*res.y*3.14159265*SCAN_DENSITY));
	col *= scan;

	// airy grade: lift blacks, brighten, desaturate toward pastel, tint
	col = col*(1.0-BLACK_LIFT) + BLACK_LIFT;
	col *= BRIGHTNESS;
	float l = dot(col, vec3(0.2126,0.7152,0.0722));
	col = mix(col, vec3(l), DESAT);
	col *= TINT;

	// whisper of a vignette
	col *= 1.0 - VIGNETTE*dot(fromC,fromC)*2.0;

	fragColor = TDOutputSwizzle(vec4(clamp(col,0.0,1.0),1.0));
}

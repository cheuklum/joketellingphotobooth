// Dreamy / airy CRT pixel shader for a GLSL TOP, now with procedural sparkles.
// Soft scanlines, lifted blacks, pastel wash, gentle glow, soft chromatic
// aberration + twinkling star sparkles.
//
// Wiring:
//   Text DAT 'crt_dreamy' -> File: scripts/crt_dreamy.glsl, Sync to File On
//   GLSL TOP 'crt_dream'  -> Pixel Shader: crt_dreamy, input 0: crossfaded feed
//   Vectors page: Uniform 1 name 'uTime'    value.x = absTime.seconds   (animates)
//   Vectors page: Uniform 2 name 'uSparkle' value.x = sparkle amount 0..1 (optional)
//
// SPARKLES: on out of the box (SPARKLE_BASE = 1). To make sparkles appear only
// during the static burst, set SPARKLE_BASE 0.0 and drive the 'uSparkle' uniform
// with your transition envelope expression (same one on the Cross TOP).

#define CURVATURE       0.08
#define SCAN_INTENSITY  0.10
#define SCAN_DENSITY    1.6
#define ABERRATION      1.4
#define VIGNETTE        0.12
#define BLACK_LIFT      0.10
#define BRIGHTNESS      1.08
#define DESAT           0.25
#define TINT            vec3(1.03, 0.99, 1.05)
#define GLOW            0.35
#define GLOW_RADIUS     2.5

// ---- sparkle controls ----
#define SPARKLE_BASE    1.0            // 0 = only when uSparkle>0 (gate to static); 1 = always on
#define SPARKLE_DENSITY 20.0           // grid cells across the frame (more = more sparkles)
#define SPARKLE_SPARSITY 0.72          // 0..1, higher = fewer cells sparkle
#define SPARKLE_SPEED   3.0            // twinkle rate
#define SPARKLE_SHARP   6.0            // higher = snappier on/off flash
#define SPARKLE_SIZE    0.006          // core/streak thickness
#define SPARKLE_STREAK  9.0            // star-arm falloff (higher = shorter arms)
#define SPARKLE_BRIGHT  0.9            // overall sparkle intensity
#define SPARKLE_TINT    vec3(1.0, 0.93, 1.0)

uniform float uTime;
uniform float uSparkle;

layout(location = 0) out vec4 fragColor;

float hash21(vec2 p){
	p = fract(p*vec2(123.34, 456.21));
	p += dot(p, p+45.32);
	return fract(p.x*p.y);
}

vec2 curveUV(vec2 uv){
	uv = uv*2.0 - 1.0;
	uv *= 1.0 + CURVATURE * dot(uv,uv) * 0.5;
	return uv*0.5 + 0.5;
}

vec3 sampleGlow(vec2 uv, vec2 px){
	vec3 g = vec3(0.0);
	g += texture(sTD2DInputs[0], uv + vec2( GLOW_RADIUS,0)*px).rgb;
	g += texture(sTD2DInputs[0], uv + vec2(-GLOW_RADIUS,0)*px).rgb;
	g += texture(sTD2DInputs[0], uv + vec2(0, GLOW_RADIUS)*px).rgb;
	g += texture(sTD2DInputs[0], uv + vec2(0,-GLOW_RADIUS)*px).rgb;
	g *= 0.25;
	return max(g - 0.5, 0.0);
}

// procedural twinkling star sparkles across the frame
vec3 sparkles(vec2 uv, float aspect, float time){
	vec2 gv = vec2(uv.x*aspect, uv.y) * SPARKLE_DENSITY;
	vec2 id = floor(gv);
	vec2 f  = fract(gv) - 0.5;
	float rnd = hash21(id);
	if (rnd < SPARKLE_SPARSITY) return vec3(0.0);      // only some cells sparkle
	vec2 off = (vec2(hash21(id+1.7), hash21(id+9.1)) - 0.5) * 0.7;
	vec2 p = f - off;
	// twinkle over time, phase offset per cell
	float tw = max(0.0, sin(time*SPARKLE_SPEED + rnd*6.2831));
	tw = pow(tw, SPARKLE_SHARP);
	if (tw < 0.001) return vec3(0.0);
	// star: bright core + two soft cross arms
	float core = SPARKLE_SIZE / (length(p) + 0.004);
	float armX = SPARKLE_SIZE / (abs(p.x)+0.004) * exp(-abs(p.y)*SPARKLE_STREAK);
	float armY = SPARKLE_SIZE / (abs(p.y)+0.004) * exp(-abs(p.x)*SPARKLE_STREAK);
	float s = (core + armX + armY) * tw;
	return s * SPARKLE_TINT;
}

void main(){
	vec2 res = uTD2DInfos[0].res.zw;
	vec2 px  = 1.0/res;
	vec2 uv  = curveUV(vUV.st);

	if(uv.x<0.0||uv.x>1.0||uv.y<0.0||uv.y>1.0){
		fragColor = TDOutputSwizzle(vec4(vec3(0.96,0.95,0.98),1.0));
		return;
	}

	vec2 fromC = uv - 0.5;
	vec2 ab = fromC * ABERRATION * length(fromC) * px;
	vec3 col = vec3(
		texture(sTD2DInputs[0], uv+ab).r,
		texture(sTD2DInputs[0], uv).g,
		texture(sTD2DInputs[0], uv-ab).b);

	col += sampleGlow(uv, px) * GLOW;

	float scan = 1.0 - SCAN_INTENSITY*(0.5+0.5*cos(uv.y*res.y*3.14159265*SCAN_DENSITY));
	col *= scan;

	col = col*(1.0-BLACK_LIFT) + BLACK_LIFT;
	col *= BRIGHTNESS;
	float l = dot(col, vec3(0.2126,0.7152,0.0722));
	col = mix(col, vec3(l), DESAT);
	col *= TINT;

	col *= 1.0 - VIGNETTE*dot(fromC,fromC)*2.0;

	// sparkles on top (additive), gated by SPARKLE_BASE / uSparkle
	float gate = clamp(max(SPARKLE_BASE, uSparkle), 0.0, 1.0);
	if (gate > 0.0){
		float aspect = res.x/res.y;
		col += sparkles(uv, aspect, uTime) * SPARKLE_BRIGHT * gate;
	}

	fragColor = TDOutputSwizzle(vec4(clamp(col,0.0,1.0),1.0));
}

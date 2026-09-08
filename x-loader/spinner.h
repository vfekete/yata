#pragma once

#include <stdbool.h>
#include <stdint.h>

// Animates the small bright highlight that travels around the logo's ring
// in the splash artwork (resources/loader-assets/background_{light,dark}.png).
// NOT a generic reusable spinner widget -- the ring's center/orbit radius
// below are hardcoded to this specific artwork's geometry (measured via
// pixel-scanning during the original design work on this same art, before
// x-loader existed; the ring isn't exactly centered under the wordmark,
// since the decorative squares beside it pull the art's own visual center
// left). Both themes share that geometry, since it's the same layout in
// two colorways -- "two themes" here means two flare colors tuned per
// background, not two different orbits.
typedef struct Spinner Spinner;

Spinner *spinner_create(bool isDark, int imgWidth, int imgHeight);
void spinner_destroy(Spinner *sp);

// t is the animation's progress through one lap, in [0.0, 1.0) -- t=0.0
// and the limit as t->1.0 are visually identical, so a caller can loop t
// forever (e.g. fmod(elapsed_seconds / period_seconds, 1.0)) with no seam.
//
// Blends the flare directly into `pixels` (a packed native-format buffer,
// width*height uint32_t values, channel bit positions given by
// rshift/gshift/bshift -- the same layout effects.c already uses for its
// own blending). Only pixels within the flare's own small radius are
// touched; every other pixel is left exactly as it already was, since the
// background is a static picture and doesn't need touching outside that
// one small moving area (for now -- this doesn't yet account for the
// fade's own current alpha, e.g. a premultiplied-alpha buffer mid fade-in,
// it just blends into whatever's already there).
void spinner_render(Spinner *sp, uint32_t *pixels, int width, int height,
                     int rshift, int gshift, int bshift, double t);

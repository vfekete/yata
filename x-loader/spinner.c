#include "spinner.h"

#include <math.h>
#include <stdlib.h>

// Avoid depending on glibc's M_PI (only visible under certain feature-test
// macros, see main.c's own care around _GNU_SOURCE/accept4) -- trivial to
// just define the one constant this file needs.
#define SPINNER_PI 3.14159265358979323846

// Fractions of the full image (see IMG_WIDTH/IMG_HEIGHT in assets.h) --
// re-derived multiple times across this loader's design history via
// pixel-scanning (convert img.png -crop 1x1+X+Y txt:-) on this exact
// artwork and consistently landing on ~these values: center ~0.47w/0.275h,
// orbit radius ~0.165w. Not re-measured again here per this iteration's
// "don't test, just build the PoC" scope -- if the flare ends up visually
// off-ring, these three constants are the ones to nudge.

// vfe: I had to manually adjust the values to better fit into circle

#define RING_CENTER_X_FRAC 0.464
#define RING_CENTER_Y_FRAC 0.277

#define RING_RADIUS_FRAC   0.165
#define FLARE_RADIUS_FRAC  0.2

struct Spinner {
    double centerX, centerY, orbitRadius, flareRadius;
    int flareR, flareG, flareB;
};

Spinner *spinner_create(bool isDark, int imgWidth, int imgHeight)
{
    Spinner *sp = malloc(sizeof(*sp));
    if (!sp) {
        return NULL;
    }
    sp->centerX = imgWidth * RING_CENTER_X_FRAC;
    sp->centerY = imgHeight * RING_CENTER_Y_FRAC;
    sp->orbitRadius = imgWidth * RING_RADIUS_FRAC;
    sp->flareRadius = imgWidth * FLARE_RADIUS_FRAC;

    // vfe: colors were picked from the moon / sun color, so it will give small
    //      impression that moon / sun is orbiting around
    if (isDark) {
        sp->flareR = 0xe8;
        sp->flareG = 0xdd;
        sp->flareB = 0xcf;
    } else {
        sp->flareR = 0xff;
        sp->flareG = 0xfe;
        sp->flareB = 0xe3;
    }
    return sp;
}

void spinner_destroy(Spinner *sp)
{
    free(sp);
}

void spinner_render(Spinner *sp, uint32_t *pixels, int width, int height,
                     int rshift, int gshift, int bshift, double t)
{
    // Starts at the top of the ring (angle -90deg) purely so the motion
    // has an obvious, consistent "12 o'clock" reference point -- doesn't
    // matter functionally since t loops seamlessly regardless of phase.
    double angle = t * 2.0 * SPINNER_PI - (SPINNER_PI / 2.0);
    double flareX = sp->centerX + sp->orbitRadius * cos(angle);
    double flareY = sp->centerY + sp->orbitRadius * sin(angle);

    int minX = (int)(flareX - sp->flareRadius);
    int maxX = (int)(flareX + sp->flareRadius) + 1;
    int minY = (int)(flareY - sp->flareRadius);
    int maxY = (int)(flareY + sp->flareRadius) + 1;
    if (minX < 0) {
        minX = 0;
    }
    if (minY < 0) {
        minY = 0;
    }
    if (maxX > width) {
        maxX = width;
    }
    if (maxY > height) {
        maxY = height;
    }

    uint32_t channelMask = ((uint32_t)0xFF << rshift) | ((uint32_t)0xFF << gshift) | ((uint32_t)0xFF << bshift);

    for (int y = minY; y < maxY; y++) {
        for (int x = minX; x < maxX; x++) {
            double dx = x - flareX;
            double dy = y - flareY;
            double dist = sqrt(dx * dx + dy * dy);
            if (dist >= sp->flareRadius) {
                continue;
            }

            // Soft radial falloff -- solid-ish at the center, fading to
            // nothing at the edge, rather than a hard-edged disc. Capped
            // short of fully opaque (0.85) so a sliver of the underlying
            // ring art always shows through, even dead-center.
            double fade = 1.0 - (dist / sp->flareRadius);
            double alpha = fade * fade * 0.85;

            uint32_t *px = &pixels[y * width + x];
            uint32_t packed = *px;
            int r = (int)((packed >> rshift) & 0xFF);
            int g = (int)((packed >> gshift) & 0xFF);
            int b = (int)((packed >> bshift) & 0xFF);

            r = (int)(r + (sp->flareR - r) * alpha);
            g = (int)(g + (sp->flareG - g) * alpha);
            b = (int)(b + (sp->flareB - b) * alpha);

            uint32_t newRgb = ((uint32_t)r << rshift) | ((uint32_t)g << gshift) | ((uint32_t)b << bshift);
            // Only overwrite the RGB channels -- leaves whatever's outside
            // channelMask (the alpha channel, on an ARGB visual) untouched.
            *px = (packed & ~channelMask) | (newRgb & channelMask);
        }
    }
}

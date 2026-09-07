#include "effects.h"

#include <stdint.h>
#include <stdlib.h>
#include <time.h>

// Cost check, worked out up front rather than guessed: this splash is
// ~372x929 = ~346,000 pixels. Repacking (a premultiply + shift per
// channel, or a blend + shift in the fallback path) into the display's
// native pixel layout is a handful of integer ops per pixel -- on the
// order of a few million operations per frame, comfortably under 1ms on
// any real CPU against FADE_FRAME_INTERVAL_MS's 16ms (60fps) budget.
// That's why this is a plain scalar loop rather than SIMD or an external
// library: the numbers say it doesn't need it.

typedef enum {
    FADE_IN,      // animating 0->256; input ignored
    FADE_VISIBLE, // holding fully visible; input -> FADE_OUT
    FADE_OUT,     // animating 256->0; input ignored
    FADE_WAITING, // holding fully hidden; input -> FADE_DONE
    FADE_DONE,    // terminal -- fade_is_done() true
} FadeState;

struct FadeEffect {
    Display *display;
    int width, height;
    const unsigned char *rgba;
    bool hasAlphaChannel;

    // Fallback-only: the color to blend toward when there's no real alpha
    // channel to hand a compositor -- the image's own top-left pixel, so
    // it already matches whichever theme's background is in use without
    // this code needing to know light vs dark itself.
    unsigned char bgR, bgG, bgB;

    // This Visual's actual RGB channel bit positions -- not assumed to be
    // a fixed byte order (see main.c's own maskShift reasoning). Alpha, on
    // the 32-bit ARGB visuals X servers offer for compositing, is by
    // universal convention the top 8 bits (shift 24) -- Xlib's Visual
    // struct has no alpha_mask field to read this from otherwise.
    int rshift, gshift, bshift;

    uint32_t *packed; // scratch buffer, reused every frame
    XImage *image;    // wraps `packed`; created once, never recreated

    int durationMs;
    FadeState state;
    struct timespec startTime;
    bool autoClose; // see fade_set_auto_close
};

static long long now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static long long elapsed_ms_since(struct timespec start)
{
    long long startMs = (long long)start.tv_sec * 1000 + start.tv_nsec / 1000000;
    long long elapsed = now_ms() - startMs;
    return elapsed < 0 ? 0 : elapsed;
}

static int maskShift(unsigned long mask)
{
    int shift = 0;
    while (mask && !(mask & 1)) {
        mask >>= 1;
        shift++;
    }
    return shift;
}

FadeEffect *fade_create(Display *display, Visual *visual, int depth,
                         bool hasAlphaChannel,
                         const unsigned char *rgba, int width, int height,
                         int fadeDurationMs)
{
    FadeEffect *fx = calloc(1, sizeof(*fx));
    if (!fx) {
        return NULL;
    }
    fx->display = display;
    fx->width = width;
    fx->height = height;
    fx->rgba = rgba;
    fx->hasAlphaChannel = hasAlphaChannel;
    fx->bgR = rgba[0];
    fx->bgG = rgba[1];
    fx->bgB = rgba[2];
    fx->rshift = maskShift(visual->red_mask);
    fx->gshift = maskShift(visual->green_mask);
    fx->bshift = maskShift(visual->blue_mask);
    fx->durationMs = fadeDurationMs;
    fx->state = FADE_IN;

    fx->packed = malloc((size_t)width * (size_t)height * sizeof(uint32_t));
    if (!fx->packed) {
        free(fx);
        return NULL;
    }
    fx->image = XCreateImage(display, visual, (unsigned int)depth, ZPixmap, 0,
                              (char *)fx->packed, width, height, 32, 0);
    if (!fx->image) {
        free(fx->packed);
        free(fx);
        return NULL;
    }
    return fx;
}

void fade_destroy(FadeEffect *fx)
{
    if (!fx) {
        return;
    }
    if (fx->image) {
        fx->image->f.destroy_image(fx->image); // also frees `packed`
    }
    free(fx);
}

void fade_start_in(FadeEffect *fx)
{
    fx->state = FADE_IN;
    clock_gettime(CLOCK_MONOTONIC, &fx->startTime);
}

void fade_start_out(FadeEffect *fx)
{
    fx->state = FADE_OUT;
    clock_gettime(CLOCK_MONOTONIC, &fx->startTime);
}

void fade_set_auto_close(FadeEffect *fx, bool autoClose)
{
    fx->autoClose = autoClose;
}

void fade_notify_input(FadeEffect *fx)
{
    switch (fx->state) {
    case FADE_VISIBLE:
        fade_start_out(fx);
        break;
    case FADE_WAITING:
        fx->state = FADE_DONE;
        break;
    case FADE_IN:
    case FADE_OUT:
    case FADE_DONE:
        break; // ignored -- see effects.h
    }
}

bool fade_is_done(const FadeEffect *fx)
{
    return fx->state == FADE_DONE;
}

bool fade_is_animating(const FadeEffect *fx)
{
    return fx->state == FADE_IN || fx->state == FADE_OUT;
}

// alpha256: 0 = fully hidden, 256 = fully the source image. May advance
// `fx->state` (a fade completing moves into its own "holding" state) --
// this is the only place that happens on a timer; fade_notify_input is the
// other, driven by input.
static int currentAlpha256(FadeEffect *fx)
{
    switch (fx->state) {
    case FADE_IN: {
        long long elapsed = elapsed_ms_since(fx->startTime);
        if (elapsed >= fx->durationMs) {
            fx->state = FADE_VISIBLE;
            return 256;
        }
        return (int)(elapsed * 256 / fx->durationMs);
    }

    case FADE_VISIBLE:
        return 256;

    case FADE_OUT: {
        long long elapsed = elapsed_ms_since(fx->startTime);
        if (elapsed >= fx->durationMs) {
            fx->state = fx->autoClose ? FADE_DONE : FADE_WAITING;
            return 0;
        }
        return 256 - (int)(elapsed * 256 / fx->durationMs);
    }

    case FADE_WAITING:
    case FADE_DONE:
        return 0;
    }
    return 0;
}

void fade_render(FadeEffect *fx, Window window, GC gc)
{
    int alpha = currentAlpha256(fx);

    size_t pixelCount = (size_t)fx->width * (size_t)fx->height;

    if (fx->hasAlphaChannel) {
        // Real per-pixel alpha for a compositor to blend against whatever
        // is actually behind the window. ARGB32 compositing pictures are
        // expected premultiplied (RGB already scaled by alpha), not
        // straight alpha -- skipping that would make partially-faded
        // frames render too bright/opaque.
        int a8 = (alpha * 255) >> 8; // 0..256 -> 0..255 for the real channel
        for (size_t i = 0; i < pixelCount; i++) {
            int r = fx->rgba[i * 4 + 0];
            int g = fx->rgba[i * 4 + 1];
            int b = fx->rgba[i * 4 + 2];

            int outR = (r * alpha) >> 8;
            int outG = (g * alpha) >> 8;
            int outB = (b * alpha) >> 8;

            fx->packed[i] = ((uint32_t)a8 << 24) |
                            ((uint32_t)outR << fx->rshift) |
                            ((uint32_t)outG << fx->gshift) |
                            ((uint32_t)outB << fx->bshift);
        }
    } else {
        // Fallback: no compositor-capable visual was available -- blend
        // toward a solid backdrop color instead of real transparency.
        for (size_t i = 0; i < pixelCount; i++) {
            int r = fx->rgba[i * 4 + 0];
            int g = fx->rgba[i * 4 + 1];
            int b = fx->rgba[i * 4 + 2];

            int outR = fx->bgR + (((r - fx->bgR) * alpha) >> 8);
            int outG = fx->bgG + (((g - fx->bgG) * alpha) >> 8);
            int outB = fx->bgB + (((b - fx->bgB) * alpha) >> 8);

            fx->packed[i] = ((uint32_t)outR << fx->rshift) |
                            ((uint32_t)outG << fx->gshift) |
                            ((uint32_t)outB << fx->bshift);
        }
    }

    XPutImage(fx->display, window, gc, fx->image, 0, 0, 0, 0, fx->width, fx->height);
    XFlush(fx->display);
}

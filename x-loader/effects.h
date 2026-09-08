#pragma once

#include <X11/Xlib.h>
#include <stdbool.h>

#include "spinner.h"

// CPU-driven fade in/out for a single static image, driven by main.c's own
// non-blocking event loop (a `select()` on the X connection with a timeout,
// not a toolkit animation timer). Deliberately plain scalar C rather than
// an external animation/compositing library or SIMD intrinsics -- the
// workload (repack ~346,000 pixels, once per ~16ms frame) is small enough
// that a straightforward loop comfortably clears the time budget; see
// effects.c's own comment for the actual numbers this was checked against
// before deciding not to reach for a dependency.
//
// Sequence: fade in, then hold fully visible until dismissed, then fade
// out, then (standalone preview only) hold fully hidden until a second
// dismissal, which is when fade_is_done() finally becomes true. Input
// during either fade itself is ignored -- only the "holding" states react
// to it. Two ways to dismiss the first hold: fade_notify_input() (a
// keypress/click, for standalone preview runs) or fade_start_out() called
// directly (main.c's readiness-socket handling, once YATA reports
// 'running' or its wait times out). fade_set_auto_close() controls whether
// the second hold happens at all.
//
// Rendering uses a real ARGB visual + alpha channel when one was found
// (see main.c), so a compositor blends against whatever is actually behind
// the window -- not a fake solid-color crossfade. Falls back to blending
// toward the image's own top-left pixel color if no such visual is
// available (no compositor, or a minimal X setup without one).
typedef struct FadeEffect FadeEffect;

// How often the caller should wake up (via a `select()` timeout) while
// fade_is_animating() is true.
#define FADE_FRAME_INTERVAL_MS 16

// `rgba` must stay valid for the FadeEffect's lifetime (read fresh every
// frame, not copied) -- width*height*4 bytes, RGBA8888. `visual`/`depth`
// are used to pack blended pixels into this display's native format.
// `hasAlphaChannel` says whether `visual`/`depth` is a real 32-bit ARGB
// visual (true alpha compositing) or the display's ordinary opaque one
// (solid-color-blend fallback).
FadeEffect *fade_create(Display *display, Visual *visual, int depth,
                         bool hasAlphaChannel,
                         const unsigned char *rgba, int width, int height,
                         int fadeDurationMs);
void fade_destroy(FadeEffect *fx);

// Starts the fade-in. Fade-out is triggered later by fade_notify_input,
// once the fade-in's own hold state is reached (see the .c file's state
// machine) -- not automatically.
void fade_start_in(FadeEffect *fx);

// Lower-level primitive: skips straight to fading out from whatever's
// currently on screen, without waiting for input. This is what main.c's
// readiness-socket handling calls once YATA reports 'running' (or its
// 2-minute wait times out) instead of fade_notify_input. Assumes it's
// called while already fully visible (i.e. not mid fade-in); that's the
// only case exercised so far.
void fade_start_out(FadeEffect *fx);

// Socket-driven runs (YATA_LOADER_SOCKET set) skip the "hold fully hidden
// until a second click" step entirely -- there's no user to click, so
// fade_is_done() should become true the instant the fade-out finishes.
// Standalone preview runs (run-loader.sh, no socket) leave this false and
// keep the click-to-dismiss hold. Call once, any time before the fade-out
// it should affect actually starts.
void fade_set_auto_close(FadeEffect *fx, bool autoClose);

// Attaches a Spinner (spinner.h) whose highlight fade_render() draws over
// the image every frame it's fully visible (see fade_needs_frequent_wakeups
// below) -- a visual PoC layered on top of the fade, otherwise
// independent of it (its own clock, not tied to fade timing at all). NULL
// (the default) draws nothing extra, unchanged from before this existed.
// Not owned: the caller creates/destroys the Spinner itself.
void fade_set_spinner(FadeEffect *fx, Spinner *sp);

// Call on every KeyPress/ButtonPress. Advances the state machine if (and
// only if) currently in one of the two "holding" states: fully visible ->
// starts fading out; fully hidden -> marks the whole thing done. Ignored
// during either active fade, so a stray keystroke landing mid-animation
// (e.g. the Enter used to launch this from a shell) can't skip a step.
void fade_notify_input(FadeEffect *fx);

// True once the second input (after fade-out's own hold) has been
// received -- the loader's cue to actually quit.
bool fade_is_done(const FadeEffect *fx);

// True while actively animating (fade in or out): the caller should keep
// waking up at a short interval. False means it's safe for the caller to
// block indefinitely on X events instead. (Does NOT account for an
// attached spinner still needing frequent wakeups while holding fully
// visible -- see fade_needs_frequent_wakeups for that.)
bool fade_is_animating(const FadeEffect *fx);

// What main.c's select() loop actually wants to know for choosing its
// timeout: true whenever fade_is_animating() is true, OR a spinner is
// attached and currently fully visible (spinning has nothing to animate
// while the image itself isn't shown, i.e. during either "hold fully
// hidden" state). Kept separate from fade_is_animating() itself so
// existing state-machine logic gated on "is a real fade in progress"
// (e.g. main.c's socket-mode deadline check) isn't affected by whether a
// spinner happens to be attached.
bool fade_needs_frequent_wakeups(const FadeEffect *fx);

// Recomputes the current frame (advancing the fade state as needed) and
// blits it onto `window` via `gc`. Cheap enough to call on every loop
// wake, not just real animation ticks -- also the right thing to call from
// an Expose handler to repaint the current frame with no state change.
void fade_render(FadeEffect *fx, Window window, GC gc);

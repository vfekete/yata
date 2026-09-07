// YATA's startup splash -- pure-X11, no Qt at all.
//
// Why this exists: two earlier Qt-based prototypes (a PySide6 one, then a
// from-scratch C++/QML rewrite against a real Qt6 install, both since
// removed) took 26-53s to show a window even from an -O3+LTO Release C++
// build -- ruling out "unoptimized code" as the cause and pointing at Qt
// itself (library loading, QGuiApplication/QQmlApplicationEngine init, or
// similar) as the actual bottleneck, not anything CPU-bound this program
// does. This version links only Xlib + Xinerama and does nothing at
// startup but open the display and blit pixels -- no interpreter, no UI
// toolkit, no QML engine, no image-decoding library even (the PNGs are
// pre-decoded to raw RGBA at build time by generate_assets.sh and embedded
// as plain byte arrays -- see assets.h). Measured live: ~19ms from process
// start to the window actually appearing on screen, vs. the Qt prototypes'
// 26-53s -- confirms Qt's own init was the real cost, not anything
// specific to this app.
//
// Fades in, holds fully visible until a keypress/mouse click, fades out,
// then holds fully hidden until a second keypress/mouse click, which is
// when it actually exits (see effects.h/effects.c). No process-
// orchestration yet (launching YATA and waiting for a readiness signal,
// the way the removed prototypes did, to trigger the fade-out
// automatically instead of waiting for input) -- this is only the visual
// half of the original design so far. The main loop is non-blocking (a
// `select()` on the X connection with a short timeout while animating)
// specifically so the fade can keep advancing between X events rather
// than sitting blocked in XNextEvent.
//
// Uses a real 32-bit ARGB visual when one is available (XMatchVisualInfo),
// so the fade is genuine per-pixel window transparency composited against
// whatever is actually behind it (needs a compositor -- true by default on
// GNOME/KDE and most modern desktops) rather than a fake solid-color
// crossfade; falls back to blending toward the image's own background
// color if no such visual is found.
//
// Build: `make` (needs libx11-dev + libxinerama-dev). Run: `./x-loader
// [--light|--dark]` (defaults to the desktop's own preference, same
// `gsettings` check the removed Qt prototypes used).
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xinerama.h>

#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>

#include "assets.h"
#include "effects.h"

#define FADE_DURATION_MS 250

static void getPicture(bool isLightTheme, unsigned char **data, size_t *data_size)
{
    if (isLightTheme) {
        *data = light_rgba;
        *data_size = (size_t)light_rgba_len;
        return;
    }
    *data = dark_rgba;
    *data_size = (size_t)dark_rgba_len;
}

// Same desktop-preference check both removed Qt prototypes used, ported
// directly for parity -- falls back to light (false) on any failure, same
// rationale as those: never fail to show at all just
// because the preference couldn't be read.
static bool isDarkMode(void)
{
    FILE *p = popen("gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null", "r");
    if (!p) {
        return false;
    }
    char line[256] = {0};
    if (!fgets(line, sizeof(line), p)) {
        line[0] = '\0';
    }
    pclose(p);
    for (char *c = line; *c; c++) {
        *c = (char)tolower((unsigned char)*c);
    }
    return strstr(line, "dark") != NULL;
}

int main(int argc, char *argv[])
{
    bool light = false;
    bool dark = false;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--light") == 0) {
            light = true;
        } else if (strcmp(argv[i], "--dark") == 0) {
            dark = true;
        }
    }
    bool useDark = light ? false : (dark ? true : isDarkMode());

    unsigned char *rgba = NULL;
    size_t rgbaSize = 0;
    getPicture(!useDark, &rgba, &rgbaSize);
    if (rgbaSize != (size_t)IMG_WIDTH * IMG_HEIGHT * 4) {
        fprintf(stderr, "x-loader: embedded image size mismatch\n");
        return 1;
    }

    Display *display = XOpenDisplay(NULL);
    if (!display) {
        fprintf(stderr, "x-loader: cannot open X display\n");
        return 1;
    }
    int screen = DefaultScreen(display);

    // Center on the first Xinerama monitor (not just DisplayWidth/Height,
    // which spans every monitor combined on a multi-monitor setup and would
    // center on the whole virtual desktop instead of any one screen).
    int monX = 0, monY = 0;
    int monWidth = DisplayWidth(display, screen);
    int monHeight = DisplayHeight(display, screen);
    if (XineramaIsActive(display)) {
        int numScreens = 0;
        XineramaScreenInfo *screens = XineramaQueryScreens(display, &numScreens);
        if (screens && numScreens > 0) {
            monX = screens[0].x_org;
            monY = screens[0].y_org;
            monWidth = screens[0].width;
            monHeight = screens[0].height;
        }
        if (screens) {
            XFree(screens);
        }
    }
    int winX = monX + (monWidth - IMG_WIDTH) / 2;
    int winY = monY + (monHeight - IMG_HEIGHT) / 2;

    // A real 32-bit ARGB TrueColor visual is what X servers offer
    // specifically for compositor-blended windows (RENDER extension) --
    // near-universal on any modern Xorg, but not guaranteed, hence the
    // fallback path in effects.c if this isn't found.
    XVisualInfo visualInfo;
    bool hasAlphaChannel = XMatchVisualInfo(display, screen, 32, TrueColor, &visualInfo) != 0;

    Visual *visual;
    int depth;
    Colormap colormap;
    if (hasAlphaChannel) {
        visual = visualInfo.visual;
        depth = visualInfo.depth;
        colormap = XCreateColormap(display, RootWindow(display, screen), visual, AllocNone);
    } else {
        visual = DefaultVisual(display, screen);
        depth = DefaultDepth(display, screen);
        colormap = DefaultColormap(display, screen);
    }

    XSetWindowAttributes attrs;
    memset(&attrs, 0, sizeof(attrs));
    attrs.override_redirect = True; // bypass the window manager entirely --
                                     // no decorations, no reparenting, no
                                     // WM round-trip before it appears.
    attrs.colormap = colormap;
    attrs.background_pixel = 0; // transparent black (ARGB visual) or plain
                                 // black (fallback) until the first real
                                 // frame is painted just below.
    attrs.border_pixel = 0;
    Window window = XCreateWindow(
        display, RootWindow(display, screen),
        winX, winY, IMG_WIDTH, IMG_HEIGHT, 0,
        depth, InputOutput, visual,
        CWOverrideRedirect | CWColormap | CWBackPixel | CWBorderPixel, &attrs);

    XSelectInput(display, window, ExposureMask | KeyPressMask | ButtonPressMask);

    FadeEffect *fx = fade_create(display, visual, depth, hasAlphaChannel,
                                  rgba, IMG_WIDTH, IMG_HEIGHT, FADE_DURATION_MS);
    if (!fx) {
        fprintf(stderr, "x-loader: out of memory\n");
        return 1;
    }

    GC gc = XCreateGC(display, window, 0, NULL);

    XMapRaised(display, window);
    fade_start_in(fx);

    int xfd = ConnectionNumber(display);

    while (!fade_is_done(fx)) {
        XEvent event;
        while (XPending(display)) {
            XNextEvent(display, &event);
            switch (event.type) {
            case KeyPress:
            case ButtonPress:
                fade_notify_input(fx);
                break;
            default:
                break; // Expose is handled by the unconditional
                       // fade_render() below anyway.
            }
        }

        fade_render(fx, window, gc);
        if (fade_is_done(fx)) {
            // fade_render()/fade_notify_input() just reached the terminal
            // state -- exit now rather than falling into an indefinite
            // select() below waiting for an X event that has no reason to
            // arrive.
            break;
        }

        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(xfd, &fds);
        if (fade_is_animating(fx)) {
            // Wake again in time for the next frame, or sooner if an X
            // event arrives first.
            struct timeval tv = {.tv_sec = 0, .tv_usec = FADE_FRAME_INTERVAL_MS * 1000};
            select(xfd + 1, &fds, NULL, NULL, &tv);
        } else {
            // Holding (fully visible or fully hidden) -- nothing to
            // animate, so block until a real X event (the next input)
            // shows up instead of waking up on a timer for no reason.
            select(xfd + 1, &fds, NULL, NULL, NULL);
        }
    }

    fade_destroy(fx);
    XFreeGC(display, gc);
    XDestroyWindow(display, window);
    if (hasAlphaChannel) {
        XFreeColormap(display, colormap);
    }
    XCloseDisplay(display);
    return 0;
}

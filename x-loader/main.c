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
// Fades in, then either:
//   - standalone (no YATA_LOADER_SOCKET): holds fully visible until a
//     keypress/mouse click, fades out, then holds fully hidden until a
//     second click, which is when it actually exits. This is the
//     run-loader.sh preview path.
//   - socket-driven (YATA_LOADER_SOCKET set, run.sh's normal path): holds
//     fully visible until YATA connects and sends "running\n" over that
//     socket, or 2 minutes pass, or YATA disconnects without ever sending
//     it -- any of those trigger the fade-out, after which it exits
//     immediately (no second-click hold; see fade_set_auto_close). YATA
//     also sends "starting\n" as soon as it connects, but that's currently
//     just a handshake with no effect on the state machine -- a hook for
//     later (e.g. resetting the timeout, or showing progress text).
// See effects.h/effects.c for the state machine itself. The main loop is
// non-blocking (a `select()` across the X connection and the loader
// socket, with a short timeout while animating) so the fade can keep
// advancing, X events get handled, and socket messages get noticed, all
// without sitting blocked in any one of those.
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
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#include "assets.h"
#include "effects.h"

#define FADE_DURATION_MS 250
#define LOADER_TIMEOUT_MS (2 * 60 * 1000)

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

static long long now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static int set_nonblocking(int fd)
{
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

// Binds+listens on the AF_UNIX path YATA_LOADER_SOCKET names, non-blocking
// so the caller's select() loop can poll it alongside the X connection.
// Bound as early in main() as possible (before even XOpenDisplay) so it's
// ready to accept the instant YATA tries to connect, whenever run.sh
// happens to schedule it -- YATA also retries its own connect a little, so
// this isn't load-bearing, just belt and suspenders.
static int create_loader_socket(const char *path)
{
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    if (strlen(path) >= sizeof(addr.sun_path)) {
        close(fd);
        return -1;
    }
    strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
    unlink(path); // clear a stale socket file left by a prior crashed run
    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    if (listen(fd, 1) < 0) {
        close(fd);
        unlink(path);
        return -1;
    }
    set_nonblocking(fd);
    return fd;
}

// Reads whatever is currently available from the loader socket and pulls
// out complete newline-delimited messages, matching against the small
// fixed vocabulary YATA's _send_loader_message() writes. `buf`/`len` is the
// caller's persistent line-accumulation buffer (partial messages carry
// over between calls). Sets *sawRunning true the moment a "running" line
// is seen (sticky -- never cleared) and *disconnected true if the peer
// closed the connection or a real error occurred (EAGAIN/EINTR are not
// errors here, just "nothing to read right now").
static void loader_socket_consume(int fd, char *buf, size_t *len, size_t cap,
                                   bool *sawRunning, bool *disconnected)
{
    char chunk[128];
    ssize_t n = recv(fd, chunk, sizeof(chunk), 0);
    if (n < 0) {
        if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
            *disconnected = true;
        }
        return;
    }
    if (n == 0) {
        *disconnected = true;
        return;
    }
    for (ssize_t i = 0; i < n; i++) {
        char c = chunk[i];
        if (c == '\n' || *len >= cap - 1) {
            buf[*len] = '\0';
            if (strcmp(buf, "running") == 0) {
                *sawRunning = true;
            }
            *len = 0;
        } else {
            buf[(*len)++] = c;
        }
    }
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

    // Bound before anything else (X connection included) so it's listening
    // as early as physically possible -- see create_loader_socket()'s own
    // comment on why that timing matters.
    const char *socketPath = getenv("YATA_LOADER_SOCKET");
    bool socketMode = socketPath != NULL && socketPath[0] != '\0';
    int listenFd = -1;
    if (socketMode) {
        listenFd = create_loader_socket(socketPath);
        if (listenFd < 0) {
            fprintf(stderr, "x-loader: could not set up %s, continuing without it\n", socketPath);
            socketMode = false;
        }
    }

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
    if (socketMode) {
        // No second click to wait for in this mode -- nobody's there to
        // click. See fade_set_auto_close's own comment.
        fade_set_auto_close(fx, true);
    }

    int xfd = ConnectionNumber(display);
    int clientFd = -1;
    char socketBuf[256];
    size_t socketBufLen = 0;
    bool runningReceived = false;
    bool peerGone = false;
    long long deadlineMs = now_ms() + LOADER_TIMEOUT_MS;

    while (!fade_is_done(fx)) {
        XEvent event;
        while (XPending(display)) {
            XNextEvent(display, &event);
            switch (event.type) {
            case KeyPress:
            case ButtonPress:
                // Only standalone preview runs dismiss on input -- a
                // socket-driven run is dismissed by YATA, not the user (see
                // the deadline/message check below).
                if (!socketMode) {
                    fade_notify_input(fx);
                }
                break;
            default:
                break; // Expose is handled by the unconditional
                       // fade_render() below anyway.
            }
        }

        if (socketMode && listenFd >= 0 && clientFd < 0) {
            int accepted = accept(listenFd, NULL, NULL);
            if (accepted >= 0) {
                set_nonblocking(accepted);
                clientFd = accepted;
                close(listenFd);
                unlink(socketPath);
                listenFd = -1;
            }
        }
        if (socketMode && clientFd >= 0) {
            loader_socket_consume(clientFd, socketBuf, &socketBufLen, sizeof(socketBuf),
                                   &runningReceived, &peerGone);
            if (peerGone) {
                close(clientFd);
                clientFd = -1;
            }
        }
        // Fully visible and still holding (the only hold state possible
        // here, since fade_set_auto_close skips the other one) -- dismiss
        // on "running", on YATA disconnecting without ever sending it, or
        // once 2 minutes have passed with neither. A "running" that arrived
        // mid fade-in is still honored, just once FADE_VISIBLE is actually
        // reached (this check runs every iteration).
        if (socketMode && !fade_is_animating(fx) && !fade_is_done(fx)) {
            if (runningReceived || peerGone || now_ms() >= deadlineMs) {
                fade_start_out(fx);
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
        int maxFd = xfd;
        if (socketMode) {
            int watchFd = clientFd >= 0 ? clientFd : listenFd;
            if (watchFd >= 0) {
                FD_SET(watchFd, &fds);
                if (watchFd > maxFd) {
                    maxFd = watchFd;
                }
            }
        }

        if (fade_is_animating(fx)) {
            // Wake again in time for the next frame, or sooner if an X
            // event or socket message arrives first.
            struct timeval tv = {.tv_sec = 0, .tv_usec = FADE_FRAME_INTERVAL_MS * 1000};
            select(maxFd + 1, &fds, NULL, NULL, &tv);
        } else if (socketMode) {
            // Holding fully visible, waiting for "running" or the 2-minute
            // deadline -- wake in time to notice the deadline even if
            // nothing else happens first.
            long long remain = deadlineMs - now_ms();
            if (remain < 0) {
                remain = 0;
            }
            struct timeval tv = {.tv_sec = remain / 1000, .tv_usec = (remain % 1000) * 1000};
            select(maxFd + 1, &fds, NULL, NULL, &tv);
        } else {
            // Standalone preview, holding (fully visible or fully hidden)
            // -- nothing to animate and nothing timed to wait for, so block
            // until a real X event (the next input) shows up instead of
            // waking up on a timer for no reason.
            select(maxFd + 1, &fds, NULL, NULL, NULL);
        }
    }

    fade_destroy(fx);
    XFreeGC(display, gc);
    XDestroyWindow(display, window);
    if (hasAlphaChannel) {
        XFreeColormap(display, colormap);
    }
    XCloseDisplay(display);
    if (clientFd >= 0) {
        close(clientFd);
    }
    if (listenFd >= 0) {
        close(listenFd);
        unlink(socketPath);
    }
    return 0;
}

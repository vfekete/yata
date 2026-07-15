"""Keep the main window stacked below other app windows, on X11.

Qt's own `Qt.WindowStaysOnBottomHint` was tried first and rejected (see
CHANGELOG 0.1.1): on GNOME/Mutter it maps to `_NET_WM_WINDOW_TYPE_DESKTOP`,
which Mutter stacks below the desktop icons layer itself, making the window
invisible instead of merely "beneath other app windows, above icons".

Sending `_NET_WM_STATE_BELOW` directly via a raw EWMH client message, while
leaving the window's type as the default NORMAL, gets the actually-wanted
stacking: below other app windows, above the desktop background -- and,
per EWMH-compliant window manager behavior, it stays there even once the
window has keyboard focus (e.g. via focus-follows-mouse).
"""
from __future__ import annotations

from PySide6.QtGui import QGuiApplication, QWindow

_NET_WM_STATE_ADD = 1


def enable_always_below(window: QWindow) -> None:
    """No-op outside X11 -- Wayland gives ordinary apps no stacking control."""
    if QGuiApplication.platformName() != "xcb":
        return

    _send_below_state(window)
    # Not confirmed necessary on Mutter, but not ruled out either: reassert
    # on every activation so the window can never end up raised just
    # because hover-to-focus gave it keyboard focus.
    window.activeChanged.connect(lambda: _send_below_state(window))


def _send_below_state(window: QWindow) -> None:
    from Xlib import X, display
    from Xlib.protocol import event

    d = display.Display()
    try:
        root = d.screen().root
        xwindow = d.create_resource_object("window", int(window.winId()))

        net_wm_state = d.intern_atom("_NET_WM_STATE")
        net_wm_state_below = d.intern_atom("_NET_WM_STATE_BELOW")

        data = (_NET_WM_STATE_ADD, net_wm_state_below, 0, 1, 0)
        client_event = event.ClientMessage(
            window=xwindow, client_type=net_wm_state, data=(32, data)
        )
        mask = X.SubstructureRedirectMask | X.SubstructureNotifyMask
        root.send_event(client_event, event_mask=mask)
        d.flush()
    finally:
        d.close()

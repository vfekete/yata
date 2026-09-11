from __future__ import annotations

from PySide6.QtGui import QGuiApplication, QWindow

_NET_WM_STATE_ADD = 1


def enable_always_below(window: QWindow) -> None:
    if QGuiApplication.platformName() != "xcb":
        return

    _send_below_state(window)
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

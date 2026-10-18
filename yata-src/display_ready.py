"""Waits for the graphical session to be fully up before anything starts.

When YATA is autostarted at login it can race GNOME's own startup:
Xwayland (started on demand by mutter), its RandR monitor layout, the
session D-Bus, gnome-shell and the X11 scale (gsd-xsettings' Xft.dpi,
which it can only compute once mutter's org.gnome.Mutter.X11 is up) may
not all be ready yet, and the x-loader splash (pure Xlib) and Qt's xcb
platform plugin both fall over in odd ways when they aren't. Starting
before the scale is final is worse than a crash: Qt picks a device pixel
ratio of 1, the scale then flips to 2 under it, and every window's saved
geometry gets reinterpreted (and persisted) at half size. wait_for_display() polls every capability we depend on
until they all answer, for up to WAIT_TIMEOUT seconds, and logs to the
journal (via syslog) if they never do.

Deliberately Qt-free -- it runs before QGuiApplication exists, and run.sh
also runs it as a script before launching the loader:

    python display_ready.py --shell   # prints `export VAR=...` lines

Set YATA_SKIP_DISPLAY_WAIT=1 to bypass it entirely.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import syslog
import time
from typing import Callable

WAIT_TIMEOUT = 120.0
POLL_INTERVAL = 1.0
# Once the session only *became* ready while we were waiting, require it to
# stay ready -- with an unchanged monitor layout and scale -- for this many
# consecutive polls before trusting it; the shell is still busy bringing
# things up at that point.
SETTLE_POLLS = 3

# Variables a GNOME session exports into the systemd user manager's
# environment once it has set them up; an autostarted process can be
# spawned with a snapshot taken before they existed.
SESSION_ENV_VARS = ("XDG_RUNTIME_DIR", "DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY")


def _log(priority: int, message: str) -> None:
    syslog.openlog("yata", syslog.LOG_PID, syslog.LOG_USER)
    syslog.syslog(priority, message)
    print(f"yata: {message}", file=sys.stderr)


def parse_systemd_environment(text: str) -> dict[str, str]:
    env = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if not sep:
            continue
        # `systemctl show-environment` shell-quotes values with special chars.
        if value.startswith(("'", "$'")):
            try:
                parts = shlex.split(value.lstrip("$"))
                value = parts[0] if parts else ""
            except ValueError:
                pass
        env[key] = value
    return env


def _import_session_env(environ: dict) -> list[str]:
    missing = [name for name in SESSION_ENV_VARS if not environ.get(name)]
    if not missing or not shutil.which("systemctl"):
        return []
    try:
        out = subprocess.run(
            ["systemctl", "--user", "show-environment"],
            capture_output=True, text=True, timeout=3,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    session_env = parse_systemd_environment(out)
    imported = []
    for name in missing:
        if session_env.get(name):
            environ[name] = session_env[name]
            imported.append(name)
    return imported


def _check_runtime_dir(environ) -> str | None:
    runtime_dir = environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        return "XDG_RUNTIME_DIR is not set"
    if not os.path.isdir(runtime_dir):
        return f"XDG_RUNTIME_DIR {runtime_dir} does not exist"
    return None


def _check_wayland(environ) -> str | None:
    name = environ.get("WAYLAND_DISPLAY")
    if not name:
        return None
    path = name if os.path.isabs(name) else os.path.join(environ.get("XDG_RUNTIME_DIR", ""), name)
    if not os.path.exists(path):
        return f"Wayland socket {path} does not exist"
    return None


def _is_gnome(environ) -> bool:
    return "GNOME" in environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")


def parse_xft_dpi(resource_manager: str) -> str | None:
    for line in resource_manager.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "Xft.dpi":
            return value.strip() or None
    return None


def _read_x11_state(d) -> tuple[str | None, str | None, tuple]:
    """(problem, Xft.dpi, monitor layout) for an open python-xlib display."""
    from Xlib import Xatom

    if not d.has_extension("RANDR"):
        return "X server has no RANDR extension yet", None, ()
    root = d.screen().root
    monitors = root.xrandr_get_monitors(is_active=True).monitors
    if not monitors:
        return "X server reports no active monitors yet", None, ()
    layout = tuple(sorted((m.x, m.y, m.width_in_pixels, m.height_in_pixels) for m in monitors))
    prop = root.get_full_property(d.intern_atom("RESOURCE_MANAGER"), Xatom.STRING)
    value = prop.value if prop else b""
    dpi = parse_xft_dpi(value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value))
    return None, dpi, layout


def _with_display(environ, fn):
    from Xlib import display

    try:
        d = display.Display(environ["DISPLAY"])
    except Exception as exc:  # Xlib raises a zoo of error types here
        return f"cannot open X display {environ['DISPLAY']}: {exc}", None
    try:
        return None, fn(d)
    except Exception as exc:
        return f"X server query failed: {exc}", None
    finally:
        try:
            d.close()
        except Exception:
            pass


def _check_x11(environ) -> str | None:
    if not environ.get("DISPLAY"):
        return "DISPLAY is not set (Xwayland not started yet?)"
    try:
        import Xlib  # noqa: F401
    except ImportError:
        return None

    def query(d):
        problem, dpi, _ = _read_x11_state(d)
        if problem or not _is_gnome(environ):
            return problem, dpi
        if not d.get_selection_owner(d.intern_atom("_XSETTINGS_S0")):
            return "no XSETTINGS manager yet (gsd-xsettings not running)", dpi
        if dpi is None:
            return "Xft.dpi not published yet (X11 scale unknown)", dpi
        return None, dpi

    problem, result = _with_display(environ, query)
    if problem:
        return problem
    problem, dpi = result
    if problem:
        return problem
    if _is_gnome(environ) and shutil.which("gdbus"):
        # gsd-xsettings derives the X11 scale from mutter's X11 interface;
        # until that exists it publishes a fallback scale.
        for name in ("org.gnome.Mutter.X11", "org.gnome.SettingsDaemon.XSettings"):
            if _gdbus_call("--method", "org.freedesktop.DBus.NameHasOwner", name) != "(true,)":
                return f"{name} is not on the session bus yet"
        # ...and even once both exist, the fallback Xft.dpi can linger for a
        # moment before gsd-xsettings republishes the real one. Presence
        # isn't enough; the value has to match what mutter says.
        expected = expected_xft_dpi(_mutter_x11_scale(), _text_scaling_factor())
        if expected is not None and not xft_dpi_matches(dpi, expected):
            return (f"Xft.dpi is {dpi}, mutter's X11 scale implies {expected} "
                    "(gsd-xsettings hasn't published the real scale yet)")
    return None


def expected_xft_dpi(ui_scale: int | None, text_scaling: float) -> int | None:
    """gsd-xsettings publishes Xft.dpi = 96 * text-scaling-factor * UI scale."""
    if not ui_scale:
        return None
    return round(96 * text_scaling * ui_scale)


def xft_dpi_matches(dpi: str | None, expected: int) -> bool:
    try:
        return abs(float(dpi) - expected) <= 1
    except (TypeError, ValueError):
        return False


def parse_gdbus_int_variant(reply: str | None) -> int | None:
    # Properties.Get replies e.g. "(<2>,)" or "(<int32 2>,)".
    if not reply:
        return None
    inner = reply.strip().strip("(),").strip().strip("<>")
    try:
        return int(inner.split()[-1])
    except (IndexError, ValueError):
        return None


def _mutter_x11_scale() -> int | None:
    try:
        result = subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.gnome.Mutter.X11",
             "--object-path", "/org/gnome/Mutter/X11",
             "--method", "org.freedesktop.DBus.Properties.Get",
             "org.gnome.Mutter.X11", "UiScalingFactor"],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_gdbus_int_variant(result.stdout) if result.returncode == 0 else None


def _text_scaling_factor() -> float:
    if not shutil.which("gsettings"):
        return 1.0
    try:
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "text-scaling-factor"],
            capture_output=True, text=True, timeout=3,
        ).stdout
        return float(out.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return 1.0


def session_fingerprint(environ=os.environ):
    """Monitor layout + X11 scale; must stay unchanged while settling."""
    if not _needs_x11(environ) or not environ.get("DISPLAY"):
        return None
    try:
        import Xlib  # noqa: F401
    except ImportError:
        return None
    _, result = _with_display(environ, lambda d: _read_x11_state(d)[1:])
    return result


def _gdbus_call(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.freedesktop.DBus",
             "--object-path", "/org/freedesktop/DBus", *args],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _check_dbus(environ) -> str | None:
    if not shutil.which("gdbus"):
        return None
    if _gdbus_call("--method", "org.freedesktop.DBus.GetId") is None:
        return "session D-Bus is not reachable"
    if _is_gnome(environ):
        reply = _gdbus_call("--method", "org.freedesktop.DBus.NameHasOwner", "org.gnome.Shell")
        if reply != "(true,)":
            return "gnome-shell is not on the session bus yet"
    return None


def _needs_x11(environ) -> bool:
    # main.py defaults QT_QPA_PLATFORM to "xcb;wayland" and the loader is
    # pure Xlib; only an explicit non-X platform (e.g. offscreen) skips X.
    return "xcb" in environ.get("QT_QPA_PLATFORM", "xcb")


def check_session(environ=os.environ) -> list[str]:
    """Returns the reasons the session isn't ready yet (empty = ready)."""
    checks = [_check_runtime_dir, _check_wayland, _check_dbus]
    if _needs_x11(environ):
        checks.append(_check_x11)
    return [problem for check in checks if (problem := check(environ))]


def wait_for_display(
    *,
    timeout: float = WAIT_TIMEOUT,
    interval: float = POLL_INTERVAL,
    settle_polls: int = SETTLE_POLLS,
    probe: Callable[[], list[str]] | None = None,
    fingerprint: Callable[[], object] | None = None,
    environ=None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[int, str], None] = _log,
) -> bool:
    """Blocks until the session is ready; False if it wasn't within timeout."""
    environ = os.environ if environ is None else environ
    if environ.get("YATA_SKIP_DISPLAY_WAIT"):
        return True
    probe_is_default = probe is None
    if probe is None:
        def probe():
            imported = _import_session_env(environ)
            if imported:
                log(syslog.LOG_INFO, "picked up " + ", ".join(imported)
                    + " from the systemd user session environment")
            return check_session(environ)
    if fingerprint is None:
        fingerprint = (lambda: session_fingerprint(environ)) if probe_is_default else (lambda: None)

    start = clock()
    problems = probe()
    if not problems:
        state = fingerprint()
        if state is not None:
            log(syslog.LOG_INFO, f"graphical session ready (monitors/Xft.dpi: {state!r})")
        return True

    log(syslog.LOG_INFO, "graphical session not ready, waiting up to "
        f"{timeout:.0f}s: " + "; ".join(problems))
    consecutive_ok = 0
    settled_state = None
    while True:
        if clock() - start >= timeout:
            log(syslog.LOG_ERR, f"graphical session still not ready after {timeout:.0f}s, "
                "not starting YATA: " + "; ".join(problems))
            return False
        sleep(interval)
        current = probe()
        if current:
            problems = current
            consecutive_ok = 0
            continue
        state = fingerprint()
        if consecutive_ok and state != settled_state:
            log(syslog.LOG_INFO, f"monitor layout/scale changed while settling: {state!r}")
            consecutive_ok = 0
        settled_state = state
        consecutive_ok += 1
        if consecutive_ok >= settle_polls:
            log(syslog.LOG_INFO, f"graphical session ready after {clock() - start:.1f}s"
                + (f" (monitors/Xft.dpi: {state!r})" if state is not None else ""))
            return True


def main(argv: list[str]) -> int:
    if not wait_for_display():
        return 1
    if "--shell" in argv:
        for name in SESSION_ENV_VARS:
            if os.environ.get(name):
                print(f"export {name}={shlex.quote(os.environ[name])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Waits for the graphical session to be fully up before anything starts.

When YATA is autostarted at login it can race GNOME's own startup:
Xwayland (started on demand by mutter), its RandR monitor layout, the
session D-Bus and gnome-shell may not all be ready yet, and the x-loader
splash (pure Xlib) and Qt's xcb platform plugin both fall over in odd ways
when they aren't. wait_for_display() polls every capability we depend on
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
# stay ready for this many consecutive polls before trusting it -- the shell
# is still busy bringing things up at that point.
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


def _check_x11(environ) -> str | None:
    if not environ.get("DISPLAY"):
        return "DISPLAY is not set (Xwayland not started yet?)"
    try:
        from Xlib import display
    except ImportError:
        return None
    try:
        d = display.Display(environ["DISPLAY"])
    except Exception as exc:  # Xlib raises a zoo of error types here
        return f"cannot open X display {environ['DISPLAY']}: {exc}"
    try:
        if not d.has_extension("RANDR"):
            return "X server has no RANDR extension yet"
        monitors = d.screen().root.xrandr_get_monitors(is_active=True).monitors
        if not monitors:
            return "X server reports no active monitors yet"
    except Exception as exc:
        return f"X server query failed: {exc}"
    finally:
        try:
            d.close()
        except Exception:
            pass
    return None


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
    if "GNOME" in environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":"):
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
    environ=None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[int, str], None] = _log,
) -> bool:
    """Blocks until the session is ready; False if it wasn't within timeout."""
    environ = os.environ if environ is None else environ
    if environ.get("YATA_SKIP_DISPLAY_WAIT"):
        return True
    if probe is None:
        def probe():
            imported = _import_session_env(environ)
            if imported:
                log(syslog.LOG_INFO, "picked up " + ", ".join(imported)
                    + " from the systemd user session environment")
            return check_session(environ)

    start = clock()
    problems = probe()
    if not problems:
        return True

    log(syslog.LOG_INFO, "graphical session not ready, waiting up to "
        f"{timeout:.0f}s: " + "; ".join(problems))
    consecutive_ok = 0
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
        consecutive_ok += 1
        if consecutive_ok >= settle_polls:
            log(syslog.LOG_INFO, f"graphical session ready after {clock() - start:.1f}s")
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

import syslog

from display_ready import (
    check_session,
    expected_xft_dpi,
    parse_gdbus_int_variant,
    parse_systemd_environment,
    parse_xft_dpi,
    wait_for_display,
    xft_dpi_matches,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def _run(probe_results, *, timeout=120.0, environ=None, fingerprints=None):
    clock = FakeClock()
    results = iter(probe_results)
    states = iter(fingerprints) if fingerprints is not None else None
    logs = []
    ok = wait_for_display(
        timeout=timeout, interval=1.0, settle_polls=3,
        probe=lambda: next(results),
        fingerprint=(lambda: next(states)) if states else None,
        environ=environ or {},
        clock=clock, sleep=clock.sleep, log=lambda prio, msg: logs.append((prio, msg)),
    )
    return ok, clock.now, logs


def test_ready_immediately_does_not_wait_or_log():
    ok, elapsed, logs = _run([[]])
    assert ok and elapsed == 0 and logs == []


def test_waits_until_ready_then_settles():
    ok, elapsed, logs = _run([["no X"], ["no X"], [], [], []])
    assert ok
    assert elapsed == 4.0
    assert logs[-1][0] == syslog.LOG_INFO and "ready after" in logs[-1][1]


def test_flapping_readiness_restarts_settle_count():
    ok, elapsed, _ = _run([["no X"], [], [], ["no RANDR"], [], [], []])
    assert ok and elapsed == 6.0


def test_gives_up_after_timeout_with_journal_error():
    ok, elapsed, logs = _run(iter(lambda: ["DISPLAY is not set"], None), timeout=120.0)
    assert not ok
    assert elapsed == 120.0
    prio, msg = logs[-1]
    assert prio == syslog.LOG_ERR
    assert "DISPLAY is not set" in msg and "120s" in msg


def test_skip_env_var_bypasses_everything():
    ok, elapsed, logs = _run([], environ={"YATA_SKIP_DISPLAY_WAIT": "1"})
    assert ok and elapsed == 0 and logs == []


def test_check_session_reports_missing_runtime_dir_and_display():
    problems = check_session({"QT_QPA_PLATFORM": "xcb;wayland"})
    assert any("XDG_RUNTIME_DIR" in p for p in problems)
    assert any("DISPLAY" in p for p in problems)


def test_check_session_skips_x11_for_non_x_platform(tmp_path):
    problems = check_session({"QT_QPA_PLATFORM": "offscreen", "XDG_RUNTIME_DIR": str(tmp_path)})
    assert problems == [] or all("DISPLAY" not in p for p in problems)


def test_check_session_reports_missing_wayland_socket(tmp_path):
    problems = check_session({
        "QT_QPA_PLATFORM": "offscreen",
        "XDG_RUNTIME_DIR": str(tmp_path),
        "WAYLAND_DISPLAY": "wayland-9",
    })
    assert any("wayland-9" in p for p in problems)


def test_parse_systemd_environment_handles_quoting():
    env = parse_systemd_environment(
        "DISPLAY=:0\n"
        "XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.ABC\n"
        "WEIRD=$'a b\\nc'\n"
        "garbage-line\n"
    )
    assert env["DISPLAY"] == ":0"
    assert env["XAUTHORITY"] == "/run/user/1000/.mutter-Xwaylandauth.ABC"
    assert "garbage-line" not in env
    assert env["WEIRD"].startswith("a b")


def test_scale_change_while_settling_restarts_settle_count():
    # Regression: Xft.dpi flipped 96 -> 192 right after gsd-xsettings came
    # up; starting in between halved every saved window geometry.
    ok, elapsed, logs = _run(
        [["no Xft.dpi"], [], [], [], [], []],
        fingerprints=["96", "96", "192", "192", "192"],
    )
    assert ok and elapsed == 5.0
    assert any("changed while settling" in msg for _, msg in logs)


def test_parse_xft_dpi():
    assert parse_xft_dpi("Xft.antialias:\t1\nXft.dpi:\t192\nXft.hinting:\t1\n") == "192"
    assert parse_xft_dpi("Xft.antialias:\t1\n") is None
    assert parse_xft_dpi("") is None


def test_gnome_x11_checks_skipped_for_non_x_platform(tmp_path):
    problems = check_session({
        "QT_QPA_PLATFORM": "offscreen",
        "XDG_RUNTIME_DIR": str(tmp_path),
        "XDG_CURRENT_DESKTOP": "ubuntu:GNOME",
    })
    assert not any("Xft.dpi" in p or "XSETTINGS" in p or "Mutter.X11" in p for p in problems)


def test_parse_gdbus_int_variant():
    assert parse_gdbus_int_variant("(<2>,)\n") == 2
    assert parse_gdbus_int_variant("(<int32 1>,)") == 1
    assert parse_gdbus_int_variant("") is None
    assert parse_gdbus_int_variant("garbage") is None


def test_fallback_xft_dpi_does_not_match_real_scale():
    # Regression (2026-10-18): gsd-xsettings first publishes a scale-1
    # fallback (96) before mutter's X11 interface exists; the gate passed on
    # its mere presence, Qt started at DPR 1, then the switch to 192
    # halved every saved window.
    expected = expected_xft_dpi(2, 1.0)
    assert expected == 192
    assert not xft_dpi_matches("96", expected)
    assert xft_dpi_matches("192", expected)
    assert xft_dpi_matches("192.5", expected)


def test_expected_xft_dpi_includes_text_scaling():
    assert expected_xft_dpi(2, 1.25) == 240
    assert expected_xft_dpi(1, 1.0) == 96
    assert expected_xft_dpi(None, 1.0) is None

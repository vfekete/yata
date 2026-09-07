import os
import stat
from unittest.mock import MagicMock, patch

import pytest

from main import (
    APP_VERSION,
    _compute_exec_cmd,
    _ensure_desktop_entry,
    _maybe_launch_bundled_loader,
    _version_tuple,
)

FAKE_EXEC = "/home/user/apps/yata"
ALT_EXEC = "/mnt/repo/run.sh"


def test_version_tuple_parses_normal():
    assert _version_tuple("0.9.30") == (0, 9, 30)
    assert _version_tuple("1.2.3") == (1, 2, 3)
    assert _version_tuple("10.0.0") == (10, 0, 0)


def test_version_tuple_invalid_returns_zero():
    assert _version_tuple("bad") == (0,)
    assert _version_tuple("") == (0,)


def _mock_qfile(data=b"PNG"):
    qf = MagicMock()
    qf.open.return_value = True
    qf.readAll.return_value = data
    return qf


@pytest.fixture
def home(tmp_path):
    return tmp_path


def test_installs_when_no_entry_exists(home):
    with patch("main.QFile", return_value=_mock_qfile()):
        _ensure_desktop_entry("1.0.0", home=home, exec_cmd=FAKE_EXEC)

    desktop = home / ".local/share/applications/yata.desktop"
    assert desktop.exists()
    content = desktop.read_text()
    assert "X-AppVersion=1.0.0" in content
    assert f"Exec={FAKE_EXEC}" in content
    assert "Name=YATA" in content
    assert "StartupWMClass=yata" in content

    icon = home / ".local/share/icons/hicolor/256x256/apps/yata.png"
    assert icon.exists()
    assert icon.read_bytes() == b"PNG"


def test_no_op_when_same_version_and_same_exec(home):
    desktop = home / ".local/share/applications/yata.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text(f"[Desktop Entry]\nExec={FAKE_EXEC}\nX-AppVersion=1.0.0\n")
    mtime = desktop.stat().st_mtime

    with patch("main.QFile") as mock_cls:
        _ensure_desktop_entry("1.0.0", home=home, exec_cmd=FAKE_EXEC)
        mock_cls.assert_not_called()

    assert desktop.stat().st_mtime == mtime


def test_no_op_when_newer_version_and_same_exec(home):
    desktop = home / ".local/share/applications/yata.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text(f"[Desktop Entry]\nExec={FAKE_EXEC}\nX-AppVersion=99.0.0\n")
    mtime = desktop.stat().st_mtime

    with patch("main.QFile") as mock_cls:
        _ensure_desktop_entry("1.0.0", home=home, exec_cmd=FAKE_EXEC)
        mock_cls.assert_not_called()

    assert desktop.stat().st_mtime == mtime


def test_updates_when_older_version_installed(home):
    desktop = home / ".local/share/applications/yata.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text(f"[Desktop Entry]\nExec={FAKE_EXEC}\nX-AppVersion=0.1.0\n")

    with patch("main.QFile", return_value=_mock_qfile()):
        _ensure_desktop_entry("1.0.0", home=home, exec_cmd=FAKE_EXEC)

    content = desktop.read_text()
    assert "X-AppVersion=1.0.0" in content
    assert "X-AppVersion=0.1.0" not in content


def test_updates_when_exec_changed(home):
    """Switching from run.sh to compiled binary (or vice versa) triggers reinstall."""
    desktop = home / ".local/share/applications/yata.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text(f"[Desktop Entry]\nExec={ALT_EXEC}\nX-AppVersion=1.0.0\n")

    with patch("main.QFile", return_value=_mock_qfile()):
        _ensure_desktop_entry("1.0.0", home=home, exec_cmd=FAKE_EXEC)

    content = desktop.read_text()
    assert f"Exec={FAKE_EXEC}" in content
    assert f"Exec={ALT_EXEC}" not in content
    assert "X-AppVersion=1.0.0" in content


def test_installs_when_version_key_missing(home):
    desktop = home / ".local/share/applications/yata.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text(f"[Desktop Entry]\nName=YATA\nExec={FAKE_EXEC}\n")

    with patch("main.QFile", return_value=_mock_qfile()):
        _ensure_desktop_entry("1.0.0", home=home, exec_cmd=FAKE_EXEC)

    assert "X-AppVersion=1.0.0" in desktop.read_text()


def _make_executable(path):
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_compute_exec_cmd_packaged_binary_points_at_itself(tmp_path, monkeypatch):
    """build.sh's packaged binary launches its own splash sibling
    internally (_maybe_launch_bundled_loader) rather than needing a
    separate Exec= target for it, so a desktop entry generated from a
    compiled binary's own perspective (source_dir has no run.sh -- i.e.
    not a source checkout) should just point at the binary itself."""
    source_dir = tmp_path / "fake-src"
    source_dir.mkdir()
    binary = tmp_path / "yata-1.2.3"
    _make_executable(binary)

    monkeypatch.setattr("main.sys.argv", [str(binary)])
    assert _compute_exec_cmd(source_dir=source_dir) == str(binary)


def test_maybe_launch_bundled_loader_noop_when_not_compiled(tmp_path, monkeypatch):
    monkeypatch.setattr("main._IS_COMPILED", False)
    monkeypatch.delenv("YATA_LOADER_SOCKET", raising=False)
    monkeypatch.setattr("main.builtins.__nuitka_binary_dir", str(tmp_path), raising=False)
    (tmp_path / "x-loader-loader").write_text("#!/bin/sh\n")

    with patch("main.subprocess.Popen") as popen:
        _maybe_launch_bundled_loader()
        popen.assert_not_called()
    assert "YATA_LOADER_SOCKET" not in os.environ


def test_maybe_launch_bundled_loader_noop_when_socket_already_set(tmp_path, monkeypatch):
    """run.sh's own dev-mode orchestration already set the env var --
    launching a second loader on top of it would just orphan an extra
    splash window."""
    monkeypatch.setattr("main._IS_COMPILED", True)
    monkeypatch.setenv("YATA_LOADER_SOCKET", "/tmp/already-set.sock")
    monkeypatch.setattr("main.builtins.__nuitka_binary_dir", str(tmp_path), raising=False)
    (tmp_path / "x-loader-loader").write_text("#!/bin/sh\n")

    with patch("main.subprocess.Popen") as popen:
        _maybe_launch_bundled_loader()
        popen.assert_not_called()


def test_maybe_launch_bundled_loader_noop_when_binary_dir_missing(monkeypatch):
    """A dev-mode `uv run` process never gets the "__nuitka_binary_dir"
    builtin Nuitka injects at all -- _IS_COMPILED already guards that case,
    but this pins the (belt-and-suspenders) getattr default too."""
    monkeypatch.setattr("main._IS_COMPILED", True)
    monkeypatch.delenv("YATA_LOADER_SOCKET", raising=False)
    monkeypatch.delattr("main.builtins.__nuitka_binary_dir", raising=False)

    with patch("main.subprocess.Popen") as popen:
        _maybe_launch_bundled_loader()
        popen.assert_not_called()


def test_maybe_launch_bundled_loader_noop_when_bundled_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("main._IS_COMPILED", True)
    monkeypatch.delenv("YATA_LOADER_SOCKET", raising=False)
    monkeypatch.setattr("main.builtins.__nuitka_binary_dir", str(tmp_path), raising=False)
    # Deliberately no "x-loader-loader" file extracted into binary_dir.

    with patch("main.subprocess.Popen") as popen:
        _maybe_launch_bundled_loader()
        popen.assert_not_called()


def test_maybe_launch_bundled_loader_launches_extracted_file_and_sets_env(tmp_path, monkeypatch):
    monkeypatch.setattr("main._IS_COMPILED", True)
    monkeypatch.delenv("YATA_LOADER_SOCKET", raising=False)
    monkeypatch.setattr("main.builtins.__nuitka_binary_dir", str(tmp_path), raising=False)
    loader = tmp_path / "x-loader-loader"
    loader.write_text("#!/bin/sh\n")  # deliberately NOT chmod +x -- the
    # function must fix that itself (Nuitka's onefile extraction doesn't
    # promise the source file's own exec bit survived).

    with patch("main.subprocess.Popen") as popen:
        _maybe_launch_bundled_loader()
        popen.assert_called_once()
        args, kwargs = popen.call_args
        assert args[0] == [str(loader)]
        assert os.access(loader, os.X_OK)
        socket_path = kwargs["env"]["YATA_LOADER_SOCKET"]
        assert socket_path

    assert os.environ.pop("YATA_LOADER_SOCKET") == socket_path


def test_app_version_constant_is_set():
    assert APP_VERSION
    parts = APP_VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)

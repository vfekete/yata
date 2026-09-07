import stat
from unittest.mock import MagicMock, patch

import pytest

from main import APP_VERSION, _compute_exec_cmd, _ensure_desktop_entry, _version_tuple

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


def test_compute_exec_cmd_packaged_app_binary_points_at_loader_sibling(tmp_path, monkeypatch):
    """build.sh's packaged layout: dist/yata-X.Y.Z (the loader) and
    dist/yata-X.Y.Z-app (this binary) sit side by side. A desktop entry
    generated from the app binary's own perspective (source_dir has no
    run.sh -- i.e. not a source checkout) must still point at the loader,
    not skip straight to the app and bypass the splash entirely."""
    source_dir = tmp_path / "fake-src"
    source_dir.mkdir()
    app_binary = tmp_path / "yata-1.2.3-app"
    loader_binary = tmp_path / "yata-1.2.3"
    _make_executable(app_binary)
    _make_executable(loader_binary)

    monkeypatch.setattr("main.sys.argv", [str(app_binary)])
    assert _compute_exec_cmd(source_dir=source_dir) == str(loader_binary)


def test_compute_exec_cmd_falls_back_to_self_when_no_loader_sibling(tmp_path, monkeypatch):
    source_dir = tmp_path / "fake-src"
    source_dir.mkdir()
    app_binary = tmp_path / "yata-1.2.3-app"
    _make_executable(app_binary)
    # Deliberately no sibling "yata-1.2.3" file at all.

    monkeypatch.setattr("main.sys.argv", [str(app_binary)])
    assert _compute_exec_cmd(source_dir=source_dir) == str(app_binary)


def test_compute_exec_cmd_ignores_non_executable_loader_sibling(tmp_path, monkeypatch):
    source_dir = tmp_path / "fake-src"
    source_dir.mkdir()
    app_binary = tmp_path / "yata-1.2.3-app"
    loader_binary = tmp_path / "yata-1.2.3"
    _make_executable(app_binary)
    loader_binary.write_text("#!/bin/sh\n")  # not chmod +x

    monkeypatch.setattr("main.sys.argv", [str(app_binary)])
    assert _compute_exec_cmd(source_dir=source_dir) == str(app_binary)


def test_compute_exec_cmd_plain_binary_without_app_suffix_is_unaffected(tmp_path, monkeypatch):
    """A binary not named "*-app" (e.g. someone runs build.sh's app binary
    under a custom name, or this convention doesn't apply) must resolve to
    itself exactly as before this feature existed."""
    source_dir = tmp_path / "fake-src"
    source_dir.mkdir()
    binary = tmp_path / "yata-1.2.3"
    _make_executable(binary)

    monkeypatch.setattr("main.sys.argv", [str(binary)])
    assert _compute_exec_cmd(source_dir=source_dir) == str(binary)


def test_app_version_constant_is_set():
    assert APP_VERSION
    parts = APP_VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)

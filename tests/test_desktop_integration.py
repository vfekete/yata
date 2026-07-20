from unittest.mock import MagicMock, patch

import pytest

from main import APP_VERSION, _ensure_desktop_entry, _version_tuple

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


def test_app_version_constant_is_set():
    assert APP_VERSION
    parts = APP_VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)

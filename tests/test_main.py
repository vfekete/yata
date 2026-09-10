"""Regression tests for main.py's startup logic (not the full app entry
point, which needs a real QGuiApplication/QML engine — just the pure
window-selection logic factored out into _windows_to_restore())."""
import re
import zipfile
from pathlib import Path

import pytest

from main import APP_VERSION, _create_backup, _unique_backup_path, _windows_to_restore
from window_registry import DEFAULT_TAG, DEFAULT_WINDOW_ID, WindowRegistry


def test_app_version_matches_pyproject_version():
    """Regression test: main.py's APP_VERSION (gates desktop-entry/icon-
    cache resync on upgrade, see _ensure_desktop_entry) has drifted from
    pyproject.toml's own version before (fixed once already, in 0.38.4) —
    build.sh's own version-match check only catches this at build time,
    not at every commit. This is the same field build.sh itself reads via
    `grep -m1 '^version = '`."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    match = re.search(r'^version = "(.*)"$', pyproject.read_text(), re.MULTILINE)
    assert match, "could not find version = \"...\" in pyproject.toml"
    assert APP_VERSION == match.group(1), (
        f"main.py's APP_VERSION ({APP_VERSION!r}) doesn't match "
        f"pyproject.toml's version ({match.group(1)!r}) -- bump APP_VERSION "
        "to match (see build.sh's own version-match check)."
    )


@pytest.fixture(autouse=True)
def isolated_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))


def test_restores_every_window_not_just_default(tmp_path):
    """Regression test for the bug where restarting the app only ever
    reopened the original/default window — any additional window created
    via YATAS+ADD was silently never shown again after a restart, even
    though its data was still safely on disk."""
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    second_id = registry.add("Personal")
    third_id = registry.add("Work")

    restored_ids = {e["id"] for e in _windows_to_restore(registry)}

    assert restored_ids == {DEFAULT_WINDOW_ID, second_id, third_id}


def test_restores_default_only_on_first_run(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))

    restored = _windows_to_restore(registry)

    assert [e["id"] for e in restored] == [DEFAULT_WINDOW_ID]


def test_closed_windows_are_not_restored(tmp_path):
    """A window closed via YatasView's SHOW toggle stays closed across a
    restart, same as the user left it."""
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    kept_open = registry.add("Personal")
    closed = registry.add("Work")
    registry.set_open(closed, False)

    restored_ids = {e["id"] for e in _windows_to_restore(registry)}

    assert restored_ids == {DEFAULT_WINDOW_ID, kept_open}


def test_reopens_everything_if_every_window_was_closed(tmp_path):
    """Edge case: every window was individually closed — startup must still
    show something rather than launch with zero windows and no way to reach
    YATAS to reopen one."""
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    registry.set_open(DEFAULT_WINDOW_ID, False)

    restored = _windows_to_restore(registry)

    assert [e["id"] for e in restored] == [DEFAULT_WINDOW_ID]
    # And it's actually persisted, not just returned in-memory.
    assert registry.list() == restored


def test_deleted_windows_are_never_restored(tmp_path):
    """A soft-deleted window (YatasView's DELETED category — see
    WindowManager.deleteWindow) never gets restored at startup, even if its
    "open" field somehow still says True."""
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    kept = registry.add("Personal")
    deleted = registry.add("Work")
    registry.set_deleted(deleted, True)

    restored_ids = {e["id"] for e in _windows_to_restore(registry)}

    assert restored_ids == {DEFAULT_WINDOW_ID, kept}


def test_reopen_everything_fallback_excludes_deleted_windows(tmp_path):
    """Every non-deleted window was individually closed, and one other
    window is soft-deleted — the "reopen everything" fallback must restore
    the closed-but-live one without resurrecting the deleted one."""
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    registry.set_open(DEFAULT_WINDOW_ID, False)
    deleted = registry.add("Work")
    registry.set_deleted(deleted, True)

    restored = _windows_to_restore(registry)

    assert [e["id"] for e in restored] == [DEFAULT_WINDOW_ID]


def test_seeds_a_fresh_window_if_every_entry_is_deleted(tmp_path):
    """Edge case: the user soft-deleted every window, including "default" —
    startup should seed and show a fresh one rather than resurrecting a
    deleted entry or launching with zero windows."""
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    registry.set_deleted(DEFAULT_WINDOW_ID, True)

    restored = _windows_to_restore(registry)

    assert len(restored) == 1
    assert restored[0]["tag"] == DEFAULT_TAG
    assert restored[0]["id"] != DEFAULT_WINDOW_ID  # never resurrects the deleted one
    assert restored[0]["deleted"] is False


def test_seeds_a_fresh_window_if_registry_is_completely_empty(tmp_path):
    """Edge case: the user deleted every window, including "default" —
    startup should still show something rather than launch with zero
    windows and nothing to interact with."""
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    registry.remove(DEFAULT_WINDOW_ID)
    assert registry.list() == []

    restored = _windows_to_restore(registry)

    assert len(restored) == 1
    assert restored[0]["tag"] == DEFAULT_TAG
    assert restored[0]["id"] != DEFAULT_WINDOW_ID  # never resurrects the reserved id
    # And it's actually persisted, not just returned in-memory.
    assert registry.list() == restored


def test_create_backup_zips_config_and_data_dirs(tmp_path):
    # isolated_xdg (autouse) already points XDG_CONFIG_HOME/XDG_DATA_HOME at
    # tmp_path/config and tmp_path/data — populate those directly.
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    (config_home / "yata").mkdir(parents=True)
    (config_home / "yata" / "yata.conf").write_text("[General]\n")
    (data_home / "yata" / "instances" / "abc").mkdir(parents=True)
    (data_home / "yata" / "tasks.json").write_text("[]")
    (data_home / "yata" / "instances" / "abc" / "tasks.json").write_text("{}")

    dest_dir = tmp_path / "backups"
    dest_dir.mkdir()
    backup_path = _create_backup(dest_dir)

    assert backup_path.parent == dest_dir
    assert backup_path.name.startswith("yb-")
    with zipfile.ZipFile(backup_path) as zf:
        names = set(zf.namelist())
    assert "config/yata.conf" in names
    assert "data/tasks.json" in names
    assert "data/instances/abc/tasks.json" in names


def test_unique_backup_path_appends_incrementing_number_on_collision(tmp_path):
    stamp = "2026-08-26-18-23"
    (tmp_path / f"yb-{stamp}.zip").touch()
    (tmp_path / f"yb-{stamp}-1.zip").touch()

    result = _unique_backup_path(tmp_path, stamp)

    assert result == tmp_path / f"yb-{stamp}-2.zip"


def test_unique_backup_path_no_collision(tmp_path):
    stamp = "2026-08-26-18-23"

    result = _unique_backup_path(tmp_path, stamp)

    assert result == tmp_path / f"yb-{stamp}.zip"

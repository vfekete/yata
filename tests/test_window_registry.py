import os

import pytest

from window_registry import (
    DEFAULT_TAG,
    DEFAULT_WINDOW_ID,
    WindowRegistry,
    settings_path_for,
    tasks_path_for,
)


@pytest.fixture(autouse=True)
def isolated_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))


def test_first_run_seeds_default_window(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    assert registry.list() == [{"id": DEFAULT_WINDOW_ID, "tag": DEFAULT_TAG, "open": True}]


def test_add_creates_unique_ids_with_given_tag(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    a = registry.add("Work")
    b = registry.add("Work")
    assert a != b
    tags = {e["id"]: e["tag"] for e in registry.list()}
    assert tags[a] == "Work"
    assert tags[b] == "Work"


def test_rename_updates_tag(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_id = registry.add("Work")
    registry.rename(window_id, "Personal")
    assert registry.get_tag(window_id) == "Personal"


def test_remove_deletes_entry(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_id = registry.add("Work")
    registry.remove(window_id)
    assert registry.get_tag(window_id) == ""
    assert all(e["id"] != window_id for e in registry.list())


def test_deleting_default_does_not_resurrect_on_restart(tmp_path):
    path = str(tmp_path / "windows.json")
    registry = WindowRegistry(path=path)
    registry.remove(DEFAULT_WINDOW_ID)

    restarted = WindowRegistry(path=path)
    assert all(e["id"] != DEFAULT_WINDOW_ID for e in restarted.list())


def test_registry_persists_across_instances(tmp_path):
    path = str(tmp_path / "windows.json")
    registry = WindowRegistry(path=path)
    window_id = registry.add("Work")

    restarted = WindowRegistry(path=path)
    assert restarted.get_tag(window_id) == "Work"


def test_next_available_tag_unchanged_when_not_taken(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    registry.remove(DEFAULT_WINDOW_ID)
    assert registry.next_available_tag("YATA") == "YATA"


def test_next_available_tag_appends_dash_2_for_first_duplicate(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    assert registry.next_available_tag(DEFAULT_TAG) == "YATA - 2"


def test_next_available_tag_increments_past_the_highest_existing_suffix(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    registry.add("YATA - 2")
    registry.add("YATA - 5")  # gap left by e.g. a manual rename elsewhere
    assert registry.next_available_tag(DEFAULT_TAG) == "YATA - 6"


def test_next_available_tag_ignores_unrelated_tags(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    registry.remove(DEFAULT_WINDOW_ID)
    registry.add("YATA - work")  # non-numeric suffix, not a real dedup match
    registry.add("Something else")
    assert registry.next_available_tag("YATA") == "YATA"


def test_default_window_uses_legacy_paths():
    assert tasks_path_for(DEFAULT_WINDOW_ID) is None
    assert settings_path_for(DEFAULT_WINDOW_ID) is None


def test_new_windows_default_to_open(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_id = registry.add("Work")
    assert next(e for e in registry.list() if e["id"] == window_id)["open"] is True


def test_set_open_persists_across_instances(tmp_path):
    path = str(tmp_path / "windows.json")
    registry = WindowRegistry(path=path)
    window_id = registry.add("Work")

    registry.set_open(window_id, False)

    restarted = WindowRegistry(path=path)
    assert next(e for e in restarted.list() if e["id"] == window_id)["open"] is False


def test_entries_written_before_open_field_existed_default_to_open(tmp_path):
    """Regression guard: upgrading users' windows.json predates the "open"
    field entirely — those windows must still show up as open, not silently
    vanish from restart just because the key is missing."""
    import json

    path = tmp_path / "windows.json"
    path.write_text(json.dumps([{"id": "legacy-id", "tag": "Legacy"}]))

    registry = WindowRegistry(path=str(path))
    assert registry.list() == [{"id": "legacy-id", "tag": "Legacy", "open": True}]


def test_other_windows_get_dedicated_paths(tmp_path):
    window_id = "abc123"
    tasks_path = tasks_path_for(window_id)
    settings_path = settings_path_for(window_id)

    assert tasks_path is not None
    assert settings_path is not None
    assert window_id in tasks_path
    assert window_id in settings_path
    assert os.path.isdir(os.path.dirname(tasks_path))
    assert os.path.isdir(os.path.dirname(settings_path))

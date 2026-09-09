import json

from plugin_data import read_compatible, write_block


def test_read_compatible_returns_none_for_missing_file(tmp_path):
    path = str(tmp_path / "data.json")
    assert read_compatible(path, model_version="1.0", api_version="1.0") is None


def test_write_then_read_round_trips_data(tmp_path):
    path = str(tmp_path / "data.json")
    write_block(path, "simple_task_list", "1.0", "1.0", {"tasks": ["a"]})

    assert read_compatible(path, model_version="1.0", api_version="1.0") == {"tasks": ["a"]}


def test_write_updates_existing_block_with_same_floors(tmp_path):
    path = str(tmp_path / "data.json")
    write_block(path, "simple_task_list", "1.0", "1.0", {"tasks": ["a"]})
    write_block(path, "simple_task_list", "1.0", "1.0", {"tasks": ["a", "b"]})

    doc = json.loads((tmp_path / "data.json").read_text())
    assert len(doc["blocks"]) == 1
    assert read_compatible(path, model_version="1.0", api_version="1.0") == {"tasks": ["a", "b"]}


def test_incompatible_block_is_skipped_not_used(tmp_path):
    """A block whose floors are higher than what's currently running (e.g.
    written by a newer plugin, then downgraded) must never be handed back —
    the caller isn't equipped to understand its shape."""
    path = str(tmp_path / "data.json")
    write_block(path, "simple_task_list", "2.0", "1.0", {"new_shape": True})

    assert read_compatible(path, model_version="1.0", api_version="1.0") is None


def test_downgrade_still_finds_older_compatible_block(tmp_path):
    """Writing a newer-floor block must never remove or touch an
    older-floor block already on disk — a later downgrade needs it."""
    path = str(tmp_path / "data.json")
    write_block(path, "simple_task_list", "1.0", "1.0", {"tasks": ["a"]})
    write_block(path, "simple_task_list", "2.0", "1.0", {"new_shape": True})

    # Still running the old model version: only sees its own old block.
    assert read_compatible(path, model_version="1.0", api_version="1.0") == {"tasks": ["a"]}
    doc = json.loads((tmp_path / "data.json").read_text())
    assert len(doc["blocks"]) == 2


def test_read_picks_newest_compatible_block_when_several_qualify(tmp_path):
    path = str(tmp_path / "data.json")
    write_block(path, "simple_task_list", "1.0", "1.0", {"gen": 1})
    write_block(path, "simple_task_list", "1.1", "1.0", {"gen": 2})

    assert read_compatible(path, model_version="1.1", api_version="1.0") == {"gen": 2}


def test_write_block_upgrades_a_pre_envelope_bare_list_file(tmp_path):
    """Regression guard: a file predating this envelope entirely (e.g. a
    plain JSON array, as tasks.json used to be) must not crash write_block
    — it should just be replaced by a fresh envelope on the first save."""
    path = tmp_path / "data.json"
    path.write_text(json.dumps([{"legacy": True}]))

    write_block(path, "simple_task_list", "1.0", "1.0", {"tasks": ["a"]})

    assert read_compatible(path, model_version="1.0", api_version="1.0") == {"tasks": ["a"]}


def test_incompatible_api_version_is_also_skipped(tmp_path):
    path = str(tmp_path / "data.json")
    write_block(path, "simple_task_list", "1.0", "2.0", {"data": "needs newer host"})

    assert read_compatible(path, model_version="1.0", api_version="1.0") is None

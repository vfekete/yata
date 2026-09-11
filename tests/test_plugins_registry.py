from plugin_api import API_VERSION, Plugin
from plugins_registry import AVAILABLE_PLUGINS, build_registry, get


def _fake_plugin(plugin_id, min_api_version):
    return Plugin(
        id=plugin_id,
        display_name=plugin_id,
        min_api_version=min_api_version,
        create_content=lambda *a: None,
        copyright="(C) 2026, Test, MIT License",
    )


def test_simple_task_list_is_available_by_default():
    assert "simple_task_list" in AVAILABLE_PLUGINS


def test_get_returns_the_registered_plugin():
    plugin = get("simple_task_list")
    assert plugin.id == "simple_task_list"


def test_build_registry_includes_a_plugin_whose_min_api_version_is_satisfied():
    plugin = _fake_plugin("compatible", "1.0")
    registry = build_registry([plugin], api_version="1.0")
    assert "compatible" in registry


def test_build_registry_excludes_a_plugin_needing_a_newer_api(tmp_path):
    too_new = _fake_plugin("too_new", "999.0")
    registry = build_registry([too_new], api_version="1.0")
    assert "too_new" not in registry


def test_build_registry_keeps_other_plugins_when_one_is_incompatible():
    ok = _fake_plugin("ok", "1.0")
    too_new = _fake_plugin("too_new", "999.0")
    registry = build_registry([ok, too_new], api_version="1.0")
    assert set(registry) == {"ok"}


def test_all_registered_plugins_satisfy_the_current_api_version():
    from plugins_registry import ALL_PLUGINS

    for plugin in ALL_PLUGINS:
        assert plugin.id in AVAILABLE_PLUGINS, (
            f"{plugin.id} declares min_api_version={plugin.min_api_version} "
            f"but this build's API_VERSION is {API_VERSION}"
        )

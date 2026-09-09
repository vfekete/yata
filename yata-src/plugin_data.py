"""Versioned data-block envelope for plugin-owned files (r-9.md).

A plugin-owned file (e.g. a plugin's tasks.json) is never a single blob
that gets overwritten wholesale — it's a small envelope of independent
*blocks*, one per (model_version, api_version) floor pair a plugin has ever
written with:

    {"plugin_id": "...", "blocks": [
        {"model_version": "1.0", "api_version": "1.0", "data": {...}},
        ...
    ]}

model_version/api_version on a block are FLOORS, not the writing plugin's
own current version: "the oldest plugin data-model version, and oldest host
API version, that can still correctly read this block." A plugin reads the
newest block whose floors it satisfies, and only ever writes the block
matching its own current floors — every other block (left behind by an
older or newer plugin/API version) is preserved untouched. This lets a
plugin get downgraded later and still find data it can use, instead of
losing it to an incompatible overwrite.
"""
from __future__ import annotations

import json
import os


def _version_tuple(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def _load(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_compatible(path: str, model_version: str, api_version: str):
    """Returns the `data` of the newest block whose model_version and
    api_version floors are both satisfied (<=) by the given current
    versions, or None if the file doesn't exist or has no compatible block
    yet (e.g. every block on disk requires a newer plugin/API than this)."""
    doc = _load(path)
    if doc is None:
        return None
    my_model = _version_tuple(model_version)
    my_api = _version_tuple(api_version)
    candidates = [
        b for b in doc.get("blocks", [])
        if _version_tuple(b["model_version"]) <= my_model
        and _version_tuple(b["api_version"]) <= my_api
    ]
    if not candidates:
        return None
    newest = max(
        candidates,
        key=lambda b: (_version_tuple(b["model_version"]), _version_tuple(b["api_version"])),
    )
    return newest["data"]


def write_block(path: str, plugin_id: str, model_version: str, api_version: str, data) -> None:
    """Writes/updates the block matching exactly (model_version,
    api_version), appending it if no block with those floors exists yet.
    Every other block already in the file is left exactly as-is —
    incompatible blocks are never touched, let alone deleted, by a write."""
    doc = _load(path) or {"plugin_id": plugin_id, "blocks": []}
    blocks = doc.setdefault("blocks", [])
    for block in blocks:
        if block["model_version"] == model_version and block["api_version"] == api_version:
            block["data"] = data
            break
    else:
        blocks.append({"model_version": model_version, "api_version": api_version, "data": data})
    doc["plugin_id"] = plugin_id
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)

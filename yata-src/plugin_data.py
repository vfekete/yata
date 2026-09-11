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
    existing = _load(path)
    doc = existing if isinstance(existing, dict) else {"plugin_id": plugin_id, "blocks": []}
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

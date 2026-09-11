"""Small, framework-level QML↔Python interop helpers shared by the host
and every plugin — kept separate from plugin_api.py (that module's own
docstring: "nothing here talks to Qt/QML directly", the contract shape
only) since this one deliberately does.
"""
from __future__ import annotations

from PySide6.QtQml import QJSValue


def unwrap_qvariant(value):
    """QML calls a "QVariant"-typed Slot with a JS object/array literal,
    which PySide hands over as a QJSValue — NOT auto-converted to a
    plain Python dict/list. Must be unwrapped via toVariant() first, or
    dict()/list() calls on it raise. Direct Python callers (tests, or one
    plugin calling another's Python API) already pass a plain dict/list/
    None, so this only converts when actually needed. Same gotcha
    WindowManager.createWindow() and TimesheetModel's own summary()/
    exportPdf() all independently ran into — worth using here instead of
    re-deriving it a third time.
    """
    if isinstance(value, QJSValue):
        return value.toVariant()
    return value

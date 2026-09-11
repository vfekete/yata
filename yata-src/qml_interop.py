from __future__ import annotations

from PySide6.QtQml import QJSValue


def unwrap_qvariant(value):
    if isinstance(value, QJSValue):
        return value.toVariant()
    return value

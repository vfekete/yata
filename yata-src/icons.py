"""Recolors embedded SVG icons for QML.

QML's own XMLHttpRequest refuses to read qrc:/ resources unless the
process-wide QML_XHR_ALLOW_FILE_READ=1 escape hatch is set (a broader
security opt-out than we want just for this), so the raw-SVG-plus-color-
substitution trick lives here in Python instead, reusing the same QFile-based
resource read main.py already uses for the app icon.
"""
from urllib.parse import quote

from PySide6.QtCore import QFile, QIODevice, QObject, Slot


class IconProvider(QObject):
    """Exposed to QML as a context property; not a QQuickImageProvider."""

    @Slot(str, str, result=str)
    def coloredSvgUri(self, name: str, color_hex: str) -> str:
        """Return a data: URI for :/icons/<name>.svg with %FILLCOLOR% replaced."""
        qf = QFile(f":/icons/{name}.svg")
        if not qf.open(QIODevice.OpenModeFlag.ReadOnly):
            return ""
        raw = bytes(qf.readAll()).decode("utf-8")
        qf.close()
        colored = raw.replace("%FILLCOLOR%", color_hex)
        return "data:image/svg+xml;utf8," + quote(colored)

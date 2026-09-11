from urllib.parse import quote

from PySide6.QtCore import QFile, QIODevice, QObject, Slot


class IconProvider(QObject):
    @Slot(str, str, result=str)
    def coloredSvgUri(self, name: str, color_hex: str) -> str:
        qf = QFile(f":/icons/{name}.svg")
        if not qf.open(QIODevice.OpenModeFlag.ReadOnly):
            return ""
        raw = bytes(qf.readAll()).decode("utf-8")
        qf.close()
        colored = raw.replace("%FILLCOLOR%", color_hex)
        return "data:image/svg+xml;utf8," + quote(colored)

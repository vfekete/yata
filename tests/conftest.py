import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yata-src"))
# Repo root, so `plugins.simple_task_list...` (r-9.md) is importable
# alongside yata-src's own flat-imported modules above.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PySide6.QtGui import QGuiApplication


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    app = QGuiApplication.instance() or QGuiApplication([])
    yield app

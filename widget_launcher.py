import sys
import os

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor


class JarvisWebPage(QWebEnginePage):
    """Pipes JS console messages to terminal for debugging."""
    def javaScriptConsoleMessage(self, level, message, line, sourceID):
        icons = {0: "ℹ️", 1: "⚠️", 2: "❌"}
        print(f"{icons.get(level, '🖥️')} Widget JS [{line}]: {message}")


class JarvisWidget(QMainWindow):
    def __init__(self, html_path: str):
        super().__init__()

        # ── Window flags: frameless, always-on-top, no taskbar entry ──
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("JARVIS")

        # ── WebView setup ──────────────────────────────────────────────
        self.browser = QWebEngineView(self)
        self.browser.setPage(JarvisWebPage(self.browser))

        # Transparent background — must match CSS `background: transparent`
        self.browser.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.browser.setStyleSheet("background: transparent;")

        # CRITICAL: allow the local file:// page to call http://localhost:8000
        self.browser.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )

        # Load widget.html as a local file — no Vite dependency!
        url = QUrl.fromLocalFile(html_path)
        print(f"📡 JARVIS Widget: Loading {url.toString()}")
        self.browser.setUrl(url)
        self.browser.loadFinished.connect(self._on_load_finished)
        self.setCentralWidget(self.browser)

        # ── Size & position — top-right corner ────────────────────────
        self.resize(420, 530)
        screen = QApplication.desktop().screenGeometry()
        self.move(screen.width() - 450, 40)

        self._drag_pos = None

    def _on_load_finished(self, ok: bool):
        if ok:
            print("✅ JARVIS Widget: UI loaded successfully.")
        else:
            print("❌ JARVIS Widget: UI failed to load. Check widget.html exists.")

    # ── Drag to reposition ─────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


def launch():
    # Resolve widget.html relative to this script's directory
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "widget.html")

    if not os.path.exists(html_path):
        print(f"❌ JARVIS Widget: widget.html not found at {html_path}")
        sys.exit(1)

    app = QApplication(sys.argv)
    widget = JarvisWidget(html_path)
    widget.show()
    widget.raise_()
    widget.activateWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    launch()

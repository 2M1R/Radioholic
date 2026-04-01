import os
from typing import cast

from PySide6.QtCore import QByteArray, QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

_SVG_PATH = os.path.join(os.path.dirname(__file__), "UI", "gfx", "tray.svg")
_SVG_TEMPLATE: str | None = None


def _svg_template() -> str:
    """Read and cache the raw SVG text (read once, reused on every re-render)."""
    global _SVG_TEMPLATE
    if _SVG_TEMPLATE is None:
        with open(_SVG_PATH, encoding="utf-8") as f:
            _SVG_TEMPLATE = f.read()
    return _SVG_TEMPLATE


def _make_icon(size: int = 16) -> QIcon:
    """Render tray.svg with the current palette's WindowText colour.

    Replaces 'currentColor' in the SVG source with the actual hex colour so
    that the icon follows KDE Plasma's active colour scheme (light or dark).
    Qt's QSvgRenderer does not support CSS media-queries or CSS variables, so
    palette injection at render time is the only reliable approach.
    """
    color = QGuiApplication.palette().color(QPalette.ColorRole.WindowText)
    svg_data = _svg_template().replace("currentColor", color.name())

    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


class SystemTray(QSystemTrayIcon):
    """System tray icon with tooltip showing the currently playing station.

    Usage:
        tray = SystemTray(window, player)
        tray.show()

        # when a station starts playing:
        tray.update_station("Radio Zet")
    """

    _DEFAULT_TOOLTIP = "Radioholic"

    def __init__(self, window, player, url="", parent=None):
        super().__init__(_make_icon(), parent)

        self._window = window
        self._player = player
        self._url = url

        self._menu = QMenu()
        self._action_toggle = self._menu.addAction("Pokaż / Ukryj")
        self._menu.addSeparator()
        self._action_start = self._menu.addAction(" ▶️  Start")
        self._action_stop = self._menu.addAction("⏹  Stop")
        self._menu.addSeparator()
        self._action_quit = self._menu.addAction("Zakończ")

        self._action_toggle.triggered.connect(self._toggle_window)
        self._action_start.triggered.connect(lambda: self._player.play(self._url))
        self._action_stop.triggered.connect(player.stop)
        self._action_quit.triggered.connect(QApplication.quit)

        self.setContextMenu(self._menu)
        self.setToolTip(self._DEFAULT_TOOLTIP)
        self.activated.connect(self._on_activated)

        app = cast(QGuiApplication, QGuiApplication.instance())
        app.paletteChanged.connect(self._on_palette_changed)

        self._event_filter = _WindowEventFilter(self)
        window.installEventFilter(self._event_filter)

    def set_station(self, url: str) -> None:
        """Update the URL used by the Start action in the context menu."""
        self._url = url

    def update_streaminfo(self, track: str, station_name: str) -> None:
        """Update the tray tooltip with the currently playing track and station name."""
        self.setToolTip(
            f"🎵{track} \n" + f"📻 {station_name}"
            if track and station_name
            else self._DEFAULT_TOOLTIP
        )

    def _toggle_window(self) -> None:
        if self._window.isVisible():
            self._window.hide()
        else:
            self._window.setWindowState(
                self._window.windowState() & ~Qt.WindowState.WindowMinimized
            )
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window()

    def _on_palette_changed(self, _palette: QPalette) -> None:
        """Re-render the tray icon whenever KDE Plasma switches colour scheme."""
        self.setIcon(_make_icon())


class _WindowEventFilter(QObject):
    """Intercepts window minimize events and redirects them to the tray."""

    def __init__(self, tray: SystemTray) -> None:
        super().__init__(tray)

    def eventFilter(self, obj, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowStateChange:
            if obj.windowState() & Qt.WindowState.WindowMinimized:
                # Defer hide() to the next event-loop tick to avoid
                # re-entrant state-change handling.
                QTimer.singleShot(0, obj.hide)
                return True
        return super().eventFilter(obj, event)

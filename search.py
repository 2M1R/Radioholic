import shiboken6
from pyradios import RadioBrowser
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


class FaviconLoader(QObject):
    """Asynchronously downloads station favicons and sets them as icons on name column items."""

    ICON_SIZE = 16

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)

    def load(self, item: QTableWidgetItem, url: str) -> None:
        """Start downloading the favicon at *url* and set it on *item* when done.

        Does nothing if *url* is empty.
        """
        if not url:
            return
        reply = self._nam.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(lambda: self._on_finished(reply, item))

    def _on_finished(self, reply: QNetworkReply, item: QTableWidgetItem) -> None:
        """Called when a favicon download completes."""
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return
            if not shiboken6.isValid(item):
                # The table was cleared before the download finished — skip silently.
                return
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled = pixmap.scaled(
                    self.ICON_SIZE,
                    self.ICON_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                item.setIcon(QIcon(scaled))
        finally:
            reply.deleteLater()


def get_countries(rb: RadioBrowser) -> list[str]:
    """Fetch list of countries from RadioBrowser API."""
    countries = rb.countries()
    country_list = [""]
    for c in countries:
        country_list.append(c.get("name"))
    return country_list


def get_tags(rb: RadioBrowser) -> list[str]:
    """Fetch list of tags from RadioBrowser API."""
    tags = rb.tags()
    tag_list = [""]
    for t in tags:
        tag_list.append(t.get("name").lstrip("#"))
    return tag_list


def search_stations(rb: RadioBrowser, name: str, country: str, tags: str) -> list[dict]:
    """Search for radio stations using the given filters.

    Returns a list of station dicts from the RadioBrowser API.
    """
    return rb.search(name=name, country=country, tag_list=tags)


def populate_table(table: QTableWidget, stations: list[dict]) -> None:
    """Clear the table and fill it with the given stations.

    Column layout:
        0 – Country
        1 – Name     (favicon shown as icon, fetched asynchronously)
        2 – Tags
        3 – Codec
        4 – Bitrate
        5 – Homepage
        6 – UUID     (hidden)

    A FaviconLoader instance is stored on the table as ``_favicon_loader`` to
    keep it alive and replace the previous one on subsequent searches.
    """
    table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
    table.setRowCount(0)
    table.setRowCount(len(stations))

    loader = FaviconLoader()
    table._favicon_loader = loader  # type: ignore[attr-defined]

    for row, station in enumerate(stations):
        name_item = QTableWidgetItem(station.get("name", "").strip())
        loader.load(name_item, station.get("favicon", ""))

        table.setItem(row, 0, QTableWidgetItem(station.get("country", "").strip()))
        table.setItem(row, 1, name_item)
        table.setItem(row, 2, QTableWidgetItem(station.get("tags", "").strip()))
        table.setItem(row, 3, QTableWidgetItem(station.get("codec", "").strip()))
        table.setItem(row, 4, QTableWidgetItem(str(station.get("bitrate", "")).strip()))
        table.setItem(row, 5, QTableWidgetItem(station.get("homepage", "").strip()))
        table.setItem(row, 6, QTableWidgetItem(station.get("stationuuid", "").strip()))

    table.setColumnWidth(0, 120)
    table.setColumnWidth(1, 200)
    table.setColumnWidth(2, 180)
    table.setColumnWidth(3, 80)
    table.setColumnWidth(4, 80)
    table.setColumnWidth(5, 220)

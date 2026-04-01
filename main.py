import sys

import mpv
from pyradios import RadioBrowser
from PySide6.QtCore import QFile, QObject, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy

from search import get_countries, get_tags, populate_table, search_stations
from tray import SystemTray

player = mpv.MPV(ytdl=False, video=False)
rb = RadioBrowser()
stations = []
station_name = ""
url = ""


def on_search():
    global stations
    name = window.linSearch.text()
    country = window.cbCountry.currentText()
    tags = window.cbTags.currentText()

    stations = search_stations(rb, name=name, country=country, tags=tags)
    populate_table(window.tabStationsList, stations)


def change_title(name, value):
    global track
    track = ""

    if value:
        artist = value.get("artist")
        title = value.get("icy-title") or value.get("title")

        if artist:
            track = f"{artist} - {title}"

        else:
            track = f"{title}"

    window.statusBar().showMessage(f"🎵Now playing: {track} on 📻{station_name}")
    tray.update_streaminfo(track, station_name)


def start():
    global station_name
    global url

    row = window.tabStationsList.currentRow()

    for s in stations:
        if s.get("stationuuid").strip() == window.tabStationsList.item(row, 6).text():
            station_name = s.get("name").strip()
            url = s.get("url_resolved").strip()
            break
    player.play(url)
    tray.set_station(url)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ui_file = QFile("UI/playerwindow.ui")
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()

    window.tabStationsList.setColumnHidden(6, True)
    window.cbCountry.addItems(get_countries(rb))
    window.cbTags.addItems(get_tags(rb))

    status_label = QLabel()
    status_label.setText("")
    status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    window.statusBar().addWidget(status_label, 1)

    tray = SystemTray(window, player, url)
    tray.show()

    player.observe_property("metadata", change_title)

    window.btnSearch.clicked.connect(on_search)
    window.linSearch.returnPressed.connect(on_search)
    window.cbCountry.lineEdit().returnPressed.connect(on_search)
    window.cbTags.lineEdit().returnPressed.connect(on_search)
    window.btnPlay.clicked.connect(start)
    window.btnStop.clicked.connect(player.stop)
    window.show()

    sys.exit(app.exec())

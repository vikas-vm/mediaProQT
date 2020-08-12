from PyQt5.QtWidgets import QApplication, QWidget, QSlider, QPushButton, QHBoxLayout, QVBoxLayout, QStyle, QLabel, \
    QFileDialog, QStyleOptionSlider, QDialog, QToolButton, QSizePolicy, QSizeGrip, QMainWindow, QAbstractItemView, \
    QListView
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl, QFileInfo, QAbstractListModel, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QMouseEvent, QPalette, QColor, QPixmap, QKeySequence
import os

MOD_MASK = (Qt.CTRL | Qt.ALT | Qt.SHIFT | Qt.META)


class WindowsInhibitor:
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x80000002

    def __init__(self):
        pass

    def inhibit(self):
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(WindowsInhibitor.ES_CONTINUOUS |
                                                       WindowsInhibitor.ES_SYSTEM_REQUIRED)

    def uninhibit(self):
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(
            WindowsInhibitor.ES_CONTINUOUS)


def show_small():
    box.showMinimized()


class TitleBar(QDialog):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        css = """
        QWidget{
            Background: rbg(53, 53, 53);
            color:white;
            font:18px ;
            border-radius: 1px;
            height: 18px;
        }
        QToolButton{
            Background:rbg(53, 53, 53);
        }
        """
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Highlight)
        self.setStyleSheet(css)
        self.minimize = QToolButton(self)
        self.minimize.setIcon(QIcon('icon_png/minimize.png'))
        self.maximize = QToolButton(self)
        self.maximize.setIcon(QIcon('icon_png/maximize.png'))
        close = QToolButton(self)
        close.setIcon(QIcon('icon_png/close.png'))
        self.minimize.setMinimumHeight(10)
        close.setMinimumHeight(20)
        self.maximize.setMinimumHeight(10)

        title_pix = QLabel()
        title_pix.setText("")
        title_pix.setPixmap(QPixmap("icon_png/media_player.png"))
        self.label = QLabel(self)
        self.label.setContentsMargins(5, 5, 0, 0)
        title_pix.setContentsMargins(10, 5, 0, 0)
        h_box = QHBoxLayout(self)
        h_box.addWidget(title_pix, 0)
        h_box.addWidget(self.label, 1)
        h_box.addWidget(self.minimize)
        h_box.addWidget(self.maximize)
        h_box.addWidget(close)
        h_box.setContentsMargins(0, 0, 10, 2)
        h_box.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.maxNormal = False
        close.clicked.connect(self.close)
        self.minimize.clicked.connect(show_small)
        self.maximize.clicked.connect(self.show_max_restore)

    def show_max_restore(self):
        if self.maxNormal:
            box.showNormal()
            self.maxNormal = False
            self.maximize.setIcon(QIcon('icon_png/maximize.png'))
        else:
            box.showMaximized()
            self.maxNormal = True
            self.maximize.setIcon(QIcon('icon_png/restore-down.png'))

    def close(self):
        box.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            box.moving = True
            box.offset = event.pos()

    def mouseMoveEvent(self, event):
        if box.moving:
            box.move(event.globalPos() - box.offset)


h = 0


def hhmmss(ms):
    global h
    total = ms / 1000
    if total > 3600:
        total_time = total % 3600
        h = total // 3600
    else:
        total_time = total
    minute = total_time // 60
    sec = total_time % 60
    if total > 3600:
        return "%02d:%02d:%02d" % (h, minute, sec)
    else:
        return "%02d:%02d" % (minute, sec)


class ViewerWindow(QMainWindow):
    state = pyqtSignal(bool)

    def closeEvent(self, e):
        self.state.emit(False)


class PlaylistModel(QAbstractListModel):
    def __init__(self, playlist, *args, **kwargs):
        super(PlaylistModel, self).__init__(*args, **kwargs)
        self.playlist = playlist

    def data(self, index, role):
        if role == Qt.DisplayRole:
            media = self.playlist.media(index.row())
            return media.canonicalUrl().fileName()

    def rowCount(self, index):
        return self.playlist.mediaCount()


class Slider(QSlider):
    def mousePressEvent(self, event):
        super(Slider, self).mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            val = self.pixel_pos_to_range_value(event.pos())
            self.setValue(val)

    def pixel_pos_to_range_value(self, pos):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        sr = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self)

        if self.orientation() == Qt.Horizontal:
            slider_length = sr.width()
            slider_min = gr.x()
            slider_max = gr.right() - slider_length + 1
        else:
            slider_length = sr.height()
            slider_min = gr.y()
            slider_max = gr.bottom() - slider_length + 1
        pr = pos - sr.center() + sr.topLeft()
        p = pr.x() if self.orientation() == Qt.Horizontal else pr.y()
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), p - slider_min,
                                              slider_max - slider_min, opt.upsideDown)


class MainWindow(QWidget):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.playlistView = QListView()
        self.switch_status = 2
        self.video_widget = QVideoWidget()
        self.playlist = QMediaPlaylist()
        self.model = PlaylistModel(self.playlist)
        self.titleBar = TitleBar(self)
        self.currentTimeLabel = QLabel()
        self.timeSlider = QSlider()
        self.totalTimeLabel = QLabel()
        self.mediaPlayer = QMediaPlayer()
        self.open_btn = QPushButton('Open File')
        self.play_btn = QPushButton()
        self.prev_btn = QPushButton()
        self.stop_btn = QPushButton()
        self.next_btn = QPushButton()
        self.switch_media_widgets_btn = QPushButton()
        self.pseudo_label = QLabel()

        self.vol_label = QLabel()
        self.volume_slider = Slider(Qt.Horizontal)
        self.gui()
        self.set_children_focus_policy(Qt.NoFocus)

    def gui(self):
        self.currentTimeLabel.setMinimumSize(QSize(80, 0))
        self.currentTimeLabel.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)

        self.timeSlider.setOrientation(Qt.Horizontal)
        self.totalTimeLabel.setMinimumSize(QSize(80, 0))
        self.totalTimeLabel.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignVCenter)

        self.playlistView.setAcceptDrops(True)
        self.playlistView.setProperty("showDropIndicator", True)
        self.playlistView.setDragDropMode(QAbstractItemView.DropOnly)
        self.playlistView.setAlternatingRowColors(True)
        self.playlistView.setUniformItemSizes(True)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle('Media Player')
        self.titleBar.label.setText('Media Player')
        self.setWindowIcon(QIcon('icon_png/media_player.png'))

        self.setGeometry(600, 200, 850, 600)
        self.timeSlider.setRange(0, 0)
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.prev_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.next_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.switch_media_widgets_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.vol_label.setText("")
        self.vol_label.setPixmap(QPixmap("icon_png/speaker-volume.png"))
        self.currentTimeLabel.setText("00:00")
        self.totalTimeLabel.setText("00:00")
        self.volume_slider.setValue(self.mediaPlayer.volume())
        self.mediaPlayer.setVideoOutput(self.video_widget)
        self.mediaPlayer.setPlaylist(self.playlist)
        self.playlistView.setModel(self.model)
        self.video_widget.hide()

        sizegrip = QSizeGrip(self)

        self.setAcceptDrops(True)

        inner_h_box = QHBoxLayout()
        inner_h_box.addWidget(self.prev_btn)
        inner_h_box.addWidget(self.stop_btn)
        inner_h_box.addWidget(self.next_btn)

        vol_h_box = QHBoxLayout()
        vol_h_box.addWidget(self.vol_label, 0)
        vol_h_box.addWidget(self.volume_slider, 1)

        h_box = QHBoxLayout()
        h_box.addWidget(self.open_btn)
        h_box.addWidget(self.play_btn, 0)
        h_box.addLayout(inner_h_box, 0)
        h_box.addWidget(self.switch_media_widgets_btn, 0)
        h_box.addWidget(self.pseudo_label, 1)
        h_box.addLayout(vol_h_box, 0)
        h_box.addWidget(sizegrip, 0, Qt.AlignBottom | Qt.AlignRight)

        video_slider_h_box = QHBoxLayout()
        video_slider_h_box.addWidget(self.currentTimeLabel)
        video_slider_h_box.addWidget(self.timeSlider)
        video_slider_h_box.addWidget(self.totalTimeLabel)

        v_box = QVBoxLayout()
        v_box.addWidget(self.titleBar, 0)
        v_box.addWidget(self.video_widget, 1)
        v_box.addWidget(self.playlistView, 1)
        v_box.addLayout(video_slider_h_box, 0)
        v_box.addLayout(h_box, 0)

        inner_h_box.setContentsMargins(20, 0, 10, 0)
        vol_h_box.setContentsMargins(0, 0, 20, 0)
        h_box.setContentsMargins(20, 0, 0, 0)
        v_box.setContentsMargins(0, 0, 0, 0)
        video_slider_h_box.setSpacing(10)
        h_box.setSpacing(0)
        v_box.setSpacing(0)

        self.setLayout(v_box)
        self.enabler()

        # connections
        self.open_btn.clicked.connect(self.open_file)
        self.play_btn.clicked.connect(self.play_media)
        self.stop_btn.clicked.connect(self.stop_media)

        self.prev_btn.pressed.connect(self.play_prev)
        self.next_btn.pressed.connect(self.play_next)
        self.switch_media_widgets_btn.pressed.connect(self.switch_media)

        self.playlist.currentIndexChanged.connect(self.playlist_position_changed)
        selection_model = self.playlistView.selectionModel()
        selection_model.selectionChanged.connect(self.playlist_selection_changed)

        self.mediaPlayer.durationChanged.connect(self.update_duration)
        self.mediaPlayer.positionChanged.connect(self.update_position)
        self.timeSlider.valueChanged.connect(self.mediaPlayer.setPosition)

        self.mediaPlayer.stateChanged.connect(self.media_state)

        self.mediaPlayer.volumeChanged.connect(self.volume_changed)
        self.volume_slider.valueChanged.connect(self.set_volume)

    def set_children_focus_policy(self, policy):
        def recursive_set_child_focus_policy(parent_q_widget):
            for childQWidget in parent_q_widget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursive_set_child_focus_policy(childQWidget)

        recursive_set_child_focus_policy(self)

    def enabler(self, state=False):
        if state is False:
            self.play_btn.setEnabled(False)
            self.prev_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
        else:
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)

    def switch_media(self):
        if self.switch_status == 0:
            self.video_widget.hide()
            self.playlistView.show()
            self.switch_status = 1
            self.switch_media_widgets_btn.setEnabled(True)
        elif self.switch_status == 1:
            self.video_widget.show()
            self.playlistView.hide()
            self.switch_status = 0
            self.switch_media_widgets_btn.setEnabled(True)
        else:
            self.video_widget.hide()
            self.playlistView.show()
            self.switch_media_widgets_btn.setEnabled(False)

    def play_media(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
        self.ui_handler()

    def ui_handler(self):
        if not self.playlist.isEmpty():
            self.enabler(True)
        file_path = QFileInfo(self.mediaPlayer.currentMedia().canonicalUrl().toString()).fileName()
        ext = os.path.splitext(file_path)[-1].lower()
        audio_ext = ['.flac', '.mp3']
        video_ext = ['.mp4', '.m4a', '.mov', '.flv', 'avi', '3gp', '.mkv', '.wmv']

        if ext in audio_ext:
            self.switch_status = 2
            self.switch_media()
            if self.isFullScreen():
                self.fullscreen()
        elif ext in video_ext:
            self.switch_status = 1
            self.switch_media()
        self.setWindowTitle(file_path + ' - Media Player')
        self.titleBar.label.setText(file_path + ' - Media Player')

    def stop_media(self):
        if self.mediaPlayer.state() != QMediaPlayer.StoppedState:
            self.mediaPlayer.stop()
            self.setWindowTitle('Media Player')
            self.titleBar.label.setText('Media Player')

    def fullscreen(self):
        if self.switch_status == 2 or self.isFullScreen():
            self.titleBar.show()
            self.timeSlider.show()
            self.currentTimeLabel.show()
            self.totalTimeLabel.show()
            self.volume_slider.show()
            self.open_btn.show()
            self.play_btn.show()
            self.prev_btn.show()
            self.stop_btn.show()
            self.next_btn.show()
            self.switch_media_widgets_btn.show()
            self.pseudo_label.show()
            self.vol_label.show()
            self.showNormal()
        else:
            self.titleBar.hide()
            self.timeSlider.hide()
            self.currentTimeLabel.hide()
            self.totalTimeLabel.hide()
            self.volume_slider.hide()
            self.open_btn.hide()
            self.play_btn.hide()
            self.prev_btn.hide()
            self.stop_btn.hide()
            self.next_btn.hide()
            self.switch_media_widgets_btn.hide()
            self.pseudo_label.hide()
            self.vol_label.hide()
            self.showFullScreen()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        event.accept()
        if event.button() == Qt.LeftButton:
            self.fullscreen()

    def media_state(self):

        os_sleep = WindowsInhibitor()
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            if os.name == 'nt':
                os_sleep = WindowsInhibitor()
                os_sleep.inhibit()
        else:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            if os_sleep:
                os_sleep.uninhibit()

    def play_next(self):
        self.playlist.next()

    def media_seek(self, seek):
        if not self.playlist.isEmpty():
            player = self.mediaPlayer
            if (player.duration() - seek) > player.position():
                player.setPosition(player.position() + seek)

    def play_prev(self):
        self.playlist.previous()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            ext = os.path.splitext(url.fileName())[-1].lower()
            allowed_ext = ['.flac', '.mp3', '.mp4', '.m4a', '.mov', '.flv', 'avi', '3gp', '.mkv', '.wmv']
            if ext in allowed_ext:
                self.playlist.addMedia(
                    QMediaContent(url)
                )

        self.model.layoutChanged.emit()

        if self.mediaPlayer.state() != QMediaPlayer.PlayingState:
            i = self.playlist.mediaCount() - len(e.mimeData().urls())
            self.playlist.setCurrentIndex(i)
            if not self.playlist.isEmpty():
                self.play_media()

    def open_file(self):
        filter_files = "Media (*.mp3 *.mp4 *.mkv);; Videos files (*.mp4 *.mkv);; Music Files(*.mp3)"
        paths, _ = QFileDialog.getOpenFileNames(self, "Open file", "", filter_files)

        if paths:
            self.mediaPlayer.pause()
            for path in paths:
                self.playlist.addMedia(
                    QMediaContent(
                        QUrl.fromLocalFile(path)
                    )
                )
            i = self.playlist.mediaCount() - len(paths)
            self.playlist.setCurrentIndex(i)
            self.play_media()

        self.model.layoutChanged.emit()

    def update_duration(self, duration):
        self.mediaPlayer.duration()

        self.timeSlider.setMaximum(duration)

        if duration >= 0:
            self.totalTimeLabel.setText(hhmmss(duration))

    def update_position(self, position):
        if position >= 0:
            self.currentTimeLabel.setText(hhmmss(position))

        self.timeSlider.blockSignals(True)
        self.timeSlider.setValue(position)
        self.timeSlider.blockSignals(False)

    def playlist_selection_changed(self, ix):
        i = ix.indexes()[0].row()
        self.playlist.setCurrentIndex(i)
        self.ui_handler()

    def playlist_position_changed(self, i):
        if i > -1:
            ix = self.model.index(i)
            self.playlistView.setCurrentIndex(ix)

    def set_volume(self, value):
        self.mediaPlayer.setVolume(value)

    def volume_changed(self, value):
        self.volume_slider.setValue(value)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = int(event.modifiers())
        if (modifiers and modifiers & MOD_MASK == modifiers and
                key > 0 and key != Qt.Key_Shift and key != Qt.Key_Alt and
                key != Qt.Key_Control and key != Qt.Key_Meta):
            key_name = QKeySequence(modifiers + key).toString()
            if key_name == 'Ctrl+Right':
                self.media_seek(30000)
            elif key_name == 'Ctrl+Left':
                self.media_seek(-30000)
            elif key_name == 'Ctrl+Up':
                self.mediaPlayer.setVolume(self.mediaPlayer.volume() + 5)
            elif key_name == 'Ctrl+Down':
                self.mediaPlayer.setVolume(self.mediaPlayer.volume() - 5)
            elif key_name == 'Ctrl+O':
                self.open_file()

        else:
            if event.key() == Qt.Key_Space:
                self.play_media()
            elif event.key() == Qt.Key_MediaPlay:
                self.play_media()
            elif event.key() == Qt.Key_MediaNext:
                self.play_next()
            elif event.key() == Qt.Key_MediaPrevious:
                self.play_prev()
            elif event.key() == Qt.Key_Escape:
                self.close()
            elif event.key() == Qt.Key_F:
                self.fullscreen()
            elif event.key() == Qt.Key_Right:
                self.media_seek(5000)
            elif event.key() == Qt.Key_Left:
                self.media_seek(-5000)


if __name__ == '__main__':
    app = QApplication([])
    app.setApplicationName("Test Media")
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")

    box = MainWindow()
    box.show()
    app.exec_()

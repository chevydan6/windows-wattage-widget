#!/usr/bin/python3
"""Local Linux port of chevydan6/windows-wattage-widget (MIT)."""
import json
import os
from pathlib import Path
import sys

from PyQt6.QtCore import QLockFile, QPointF, QSettings, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPolygonF, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget


def read_power(root=Path('/sys/class/power_supply')):
    found = False
    draw = charge = False
    invalid = False
    total = 0.0
    for battery in root.glob('*'):
        try:
            if (battery / 'type').read_text().strip() != 'Battery':
                continue
            if (battery / 'present').exists() and (battery / 'present').read_text().strip() == '0':
                continue
            found = True
            status = (battery / 'status').read_text().strip()
            if status not in ('Discharging', 'Charging'):
                continue
            draw |= status == 'Discharging'
            charge |= status == 'Charging'
            try:
                if (battery / 'power_now').exists():
                    watts = abs(float((battery / 'power_now').read_text())) / 1_000_000
                else:
                    current = float((battery / 'current_now').read_text())
                    voltage = float((battery / 'voltage_now').read_text())
                    watts = abs(current * voltage) / 1_000_000_000_000
                if not 0 <= watts < 1000:
                    raise ValueError('Invalid battery sensor reading')
                total += watts if status == 'Discharging' else -watts
            except (OSError, ValueError):
                invalid = True
        except OSError:
            continue
    if draw or charge:
        net_draw = draw and (not charge or total >= 0)
        return {'mode': 'BATTERY DRAW' if net_draw else 'BATTERY CHARGE',
                'detail': 'On battery' if net_draw else 'Charging',
                'watts': None if invalid else abs(total)}
    return {'mode': 'AC POWER' if found else 'POWER',
            'detail': 'Draw unavailable' if found else 'Sensor unavailable', 'watts': None}


def lightning(color):
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in
                                 [(18, 1), (5, 18), (14, 18), (11, 31), (28, 12), (19, 12)]]))
    painter.end()
    return QIcon(pixmap)


class Widget(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle('Wattage Widget')
        self.setObjectName('wattage-widget')
        self.setFixedSize(96, 96)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.settings = QSettings('WattageWidget', 'WattageWidget')
        self.reading = read_power()
        self.display_on = self.settings.value('visible', True, type=bool)
        self.on_icon, self.off_icon = lightning('#4ade80'), lightning('#f87171')
        self.setWindowIcon(self.on_icon)
        self.menu = QMenu()
        self.show_action = self.menu.addAction('Show wattage display')
        self.show_action.setCheckable(True)
        self.show_action.triggered.connect(self.set_display)
        self.menu.addAction('Move to upper-right corner', self.set_corner)
        self.menu.addSeparator()
        self.menu.addAction('Exit', QApplication.instance().quit)
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.on_icon if self.display_on else self.off_icon)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.tray_clicked)
        self.tray.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self.set_display(self.display_on)
        self.set_corner()

    def value(self):
        watts = self.reading['watts']
        return '\u2014' if watts is None else f'{watts:.1f} W'

    def set_display(self, visible):
        self.display_on = bool(visible)
        self.setVisible(self.display_on)
        self.show_action.setChecked(self.display_on)
        self.tray.setIcon(self.on_icon if self.display_on else self.off_icon)
        self.settings.setValue('visible', self.display_on)
        self.refresh()

    def tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.set_display(not self.display_on)

    def set_corner(self):
        screen = self.screen() or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 7, area.top() + 8)
        # Native Wayland positions are managed by KWin. A targeted window rule
        # supplies initial placement when the surface is mapped again.
        if QApplication.platformName() == 'wayland' and self.isVisible():
            self.hide()
            self.show()

    def refresh(self):
        self.reading = read_power()
        state = 'ON' if self.display_on else 'OFF'
        self.tray.setToolTip(f'Wattage {state}: {self.value()} — {self.reading["detail"]}')
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#19222d'))
        painter.setPen(QColor('#465261'))
        painter.drawRect(0, 0, 95, 95)
        for text, y, height, pixels, color, bold in [
            (self.reading['mode'], 7, 19, 9, '#b7c5d4', False),
            (self.value(), 28, 39, 25, '#a9edbb', True),
            (self.reading['detail'], 70, 18, 10, '#b7c5d4', False),
        ]:
            font = QFont('sans-serif')
            font.setPixelSize(pixels)
            font.setBold(bold)
            painter.setFont(font)
            painter.setPen(QColor(color))
            painter.drawText(2, y, 92, height, Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemMove()

    def contextMenuEvent(self, event):
        self.menu.exec(event.globalPos())


def main():
    if '--check' in sys.argv:
        print(json.dumps(read_power(), indent=2))
        return 0
    app = QApplication(sys.argv)
    app.setApplicationName('wattage-widget')
    app.setDesktopFileName('wattage-widget')
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(Path(os.environ['XDG_RUNTIME_DIR']) / 'wattage-widget.lock'))
    if not lock.tryLock(0):
        return 0
    widget = Widget()
    app.aboutToQuit.connect(widget.tray.hide)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

from ._shared import *

class CircleSlider(QWidget):
    """A compact slider with a circular handle, snapping, and optional value bubble.

    - Supports mouse drag, click-to-jump, and keyboard adjustment.
    - Can smooth transitions toward a target value.
    - Emits `valueChanged(int)` whenever the current value updates.

    Usage
    -----
        slider = CircleSlider(parent=some_widget, min_val=0, max_val=500, value=120)
        slider.setSnapStep(5)
        slider.valueChanged.connect(lambda v: print(v))
    """

    valueChanged = Signal(int)

    def __init__(self, parent=None, min_val=0, max_val=100, value=0, snap_step=1, label=True):
        super().__init__(parent)
        self._min = int(min_val)
        self._max = int(max_val)
        self._value = int(value)
        self._target_value = int(value)
        self._snap = max(1, int(snap_step))
        self._dragging = False
        self._hovered = False
        self._key_adjust = False
        self._drag_offset = 0
        self._track_h = 8
        self._margin = 6
        self._max_handle_radius = 8
        self._smoothing = True
        self._show_label = bool(label)
        self._label = QLabel(self) if self._show_label else None
        if self._label is not None:
            self._label.setStyleSheet(
                "QLabel { background: #2e2e2e; color: #FFFFFF; border-radius: 6px; padding: 2px 6px; border: none; }"
            )
            self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self._label.hide()

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedHeight(self._max_handle_radius * 2 + 4)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def _geom_radius(self):
        return self._max_handle_radius

    def sizeHint(self):
        return QSize(140, self._max_handle_radius * 2 + 4)

    def minimumSizeHint(self):
        return QSize(80, self._max_handle_radius * 2 + 4)

    def setRange(self, min_val, max_val):
        self._min = int(min_val)
        self._max = int(max_val)
        self.setValue(self._value)

    def setSnapStep(self, step):
        self._snap = max(1, int(step))

    def value(self):
        return int(self._value)

    def setValue(self, v):
        v = int(v)
        v = max(self._min, min(self._max, v))
        if v == self._value:
            return
        self._value = v
        self._target_value = v
        self.valueChanged.emit(self._value)
        self.update()
        self._position_label()

    def _handle_radius(self):
        if self._dragging:
            return self._max_handle_radius
        if self._hovered:
            return max(6, self._max_handle_radius - 1)
        return max(5, self._max_handle_radius - 2)

    def _usable_width(self):
        r = self._geom_radius()
        return max(1, self.width() - 2 * self._margin - 2 * r)


    def _value_to_x(self, value):
        if self._max <= self._min:
            return self._margin
        t = (value - self._min) / float(self._max - self._min)
        r = self._handle_radius()
        return self._margin + r + t * self._usable_width()


    def _x_to_value(self, x):
        x = max(self._margin, min(self._margin + self._usable_width(), x))
        t = (x - self._margin) / float(self._usable_width())
        raw = self._min + t * (self._max - self._min)
        snapped = int(round(raw / self._snap) * self._snap)
        return max(self._min, min(self._max, snapped))

    def _handle_rect(self):
        r = self._max_handle_radius
        cx = self._value_to_x(self._value)
        cy = self.height() // 2
        return QRectF(cx - r, cy - r, r * 2, r * 2)

    def _paint_handle_rect(self):
        r = self._handle_radius()
        cx = self._value_to_x(self._value)
        cy = self.height() // 2
        return QRectF(cx - r, cy - r, r * 2, r * 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        track_y = (self.height() - self._track_h) // 2
        track_rect = QRect(self._margin, track_y, self._usable_width(), self._track_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#6a6a6a"))
        painter.drawRoundedRect(track_rect, self._track_h // 2, self._track_h // 2)

        filled_rect = QRect(self._margin, track_y, int(self._value_to_x(self._value) - self._margin), self._track_h)
        painter.setBrush(QColor("#8a8a8a"))
        painter.drawRoundedRect(filled_rect, self._track_h // 2, self._track_h // 2)

        color = QColor("#d0d0d0")
        if self._dragging:
            color = QColor("#c8c8c8")
        elif self._hovered:
            color = QColor("#d8d8d8")
        painter.setBrush(color)
        painter.drawEllipse(self._paint_handle_rect())
        painter.end()

    def _position_label(self):
        if self._label is None or not self._label.isVisible():
            return
        self._label.setText(str(self._value))
        self._label.adjustSize()
        cx = int(self._value_to_x(self._value))
        x = max(0, min(self.width() - self._label.width(), cx - self._label.width() // 2))
        y = max(0, self.height() // 2 - self._max_handle_radius - self._label.height() - 6)
        self._label.move(QPoint(x, y))

    def _tick(self):
        if not self._smoothing:
            self._timer.stop()
            return
        if self._value == self._target_value:
            self._timer.stop()
            return
        delta = self._target_value - self._value
        step = max(1, int(abs(delta) * 0.35))
        if delta < 0:
            step = -step
        new_val = self._value + step
        if (step > 0 and new_val > self._target_value) or (step < 0 and new_val < self._target_value):
            new_val = self._target_value
        self._value = new_val
        self.valueChanged.emit(self._value)
        self.update()
        self._position_label()

    def _set_target_value(self, v):
        v = max(self._min, min(self._max, int(v)))
        self._target_value = v
        if not self._smoothing:
            self.setValue(v)
            return
        if not self._timer.isActive():
            self._timer.start()

    def _show_value_label(self):
        if self._label is None:
            return
        self._label.show()
        self._position_label()

    def _hide_value_label(self):
        if self._label is None:
            return
        self._label.hide()

    def enterEvent(self, event):
        self._hovered = True
        self.setCursor(Qt.PointingHandCursor)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if not self._dragging:
            self.unsetCursor()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            hr = self._handle_rect()
            if hr.contains(e.position()):
                self._dragging = True
                self._drag_offset = e.position().x() - hr.center().x()
            else:
                self._dragging = True
                self._drag_offset = 0
            self.setCursor(Qt.ClosedHandCursor)
            new_val = self._x_to_value(e.position().x() - self._drag_offset)
            self._set_target_value(new_val)
            self._show_value_label()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging:
            new_val = self._x_to_value(e.position().x() - self._drag_offset)
            self._set_target_value(new_val)
            self._show_value_label()
            e.accept()
            return
        hr = self._handle_rect()
        hovered = hr.contains(e.position())
        if hovered != self._hovered:
            self._hovered = hovered
            if self._hovered:
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.unsetCursor()
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = False
            if self._hovered:
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.unsetCursor()
            self._hide_value_label()
            self.update()
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Left, Qt.Key_Right):
            base = 1
            if e.modifiers() & Qt.ShiftModifier:
                base = 10
            if e.modifiers() & Qt.ControlModifier:
                base = 50
            delta = base if e.key() == Qt.Key_Right else -base
            self._set_target_value(self._value + delta)
            self._key_adjust = True
            self._show_value_label()
            e.accept()
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if self._key_adjust and e.key() in (Qt.Key_Left, Qt.Key_Right):
            self._key_adjust = False
            self._hide_value_label()
            self.update()
            e.accept()
            return
        super().keyReleaseEvent(e)


from ._shared import *

class CircleScrollBar(QScrollBar):
    """A minimal scrollbar that uses a circular drag handle.

    - Optimized for compact vertical scroll areas.
    - Supports direct handle dragging with hover/pressed visuals.
    - Hides the default QScrollBar look and paints only the knob.

    Usage
    -----
        bar = CircleScrollBar(Qt.Vertical, parent=scroll_area)
        scroll_area.setVerticalScrollBar(bar)
    """

    def __init__(self, orientation=Qt.Vertical, parent=None,
                 handle_d=10, margin_top=12, margin_bottom=12, margin_right=6, track_w=10):
        super().__init__(orientation, parent)
        self._handle_d = int(handle_d)
        self._margin_top = int(margin_top)
        self._margin_bottom = int(margin_bottom)
        self._margin_right = int(margin_right)
        self._track_w = int(track_w)
        self._dragging = False
        self._drag_offset = 0
        self._hovered = False
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        if self.orientation() == Qt.Vertical:
            self.setFixedWidth(self._track_w + self._margin_right)

    def _handle_rect(self):
        h = self.height()
        min_v = self.minimum()
        max_v = self.maximum()

        usable_h = max(0, h - self._margin_top - self._margin_bottom - self._handle_d)
        if max_v <= min_v or usable_h == 0:
            y = self._margin_top
        else:
            t = (self.value() - min_v) / float(max_v - min_v)
            y = self._margin_top + t * usable_h

        x = max(0, self.width() - self._margin_right - self._track_w)
        return QRectF(x, y, self._handle_d, self._handle_d)

    def paintEvent(self, event):
        if self.orientation() != Qt.Vertical:
            return super().paintEvent(event)

        if self._dragging:
            color = QColor("#9a9a9a")
        elif self._hovered:
            color = QColor("#8f8f8f")
        else:
            color = QColor("#808080")

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(self._handle_rect())
        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        if not self._dragging:
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
            hr = self._handle_rect()
            if hr.contains(e.pos()):
                self._dragging = True
                self._drag_offset = e.pos().y() - hr.top()
                self.setCursor(Qt.ClosedHandCursor)
                self.update()
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging:
            h = self.height()
            min_v = self.minimum()
            max_v = self.maximum()

            usable_h = max(
                1,
                h - self._margin_top - self._margin_bottom - self._handle_d
            )

            new_y = e.pos().y() - self._drag_offset
            new_y = max(self._margin_top,
                        min(self._margin_top + usable_h, new_y))

            t = (new_y - self._margin_top) / float(usable_h)
            new_val = min_v + t * (max_v - min_v)

            self.setValue(int(new_val))
            e.accept()
            return

        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = False
            if self._hovered:
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.unsetCursor()
            self.update()
        super().mouseReleaseEvent(e)


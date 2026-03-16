from ._shared import *

class ArrowHorizontalScrollBar(QScrollBar):
    """A custom horizontal scrollbar with clickable arrow zones and a pill handle.

    - Draws its own track, handle, and left/right arrow icons.
    - Supports dragging the handle, clicking arrows for single-step movement,
      and clicking the track for page-step movement.
    - Keeps handle size proportional to `pageStep()` with a minimum width.

    Usage
    -----
        hbar = ArrowHorizontalScrollBar(parent=some_widget)
        hbar.setRange(0, 240)
        hbar.setPageStep(80)
        hbar.valueChanged.connect(on_scroll)
    """

    def __init__(self, parent=None, arrow_color="#E6E6E6",
                 track_color="#4A4A4A", handle_color="#8A8A8A",
                 handle_hover_color="#9A9A9A", handle_pressed_color="#A6A6A6",
                 arrow_area_width=16, bar_height=9, margin=2, min_handle_width=26):
        super().__init__(Qt.Horizontal, parent)
        self._arrow_color = arrow_color
        self._track_color = track_color
        self._handle_color = handle_color
        self._handle_hover_color = handle_hover_color
        self._handle_pressed_color = handle_pressed_color
        self._arrow_area_w = int(arrow_area_width)
        self._bar_h = int(bar_height)
        self._margin = int(margin)
        self._min_handle_w = int(min_handle_width)
        self._dragging = False
        self._drag_offset = 0.0
        self._hover_part = None  # "left", "right", "handle", "track", None

        self.setMouseTracking(True)
        self.setFixedHeight(max(self._bar_h + 2 * self._margin, self._arrow_area_w))
        self.setSingleStep(20)
        self.setStyleSheet("""
        QScrollBar {
            background: transparent;
            border: none;
        }
        """)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def set_colors(self, arrow_color=None, track_color=None, handle_color=None,
                   handle_hover_color=None, handle_pressed_color=None):
        if arrow_color is not None:
            self._arrow_color = arrow_color
        if track_color is not None:
            self._track_color = track_color
        if handle_color is not None:
            self._handle_color = handle_color
        if handle_hover_color is not None:
            self._handle_hover_color = handle_hover_color
        if handle_pressed_color is not None:
            self._handle_pressed_color = handle_pressed_color
        self.update()

    def _draw_arrow(self, painter, cx, cy, size, pointing_right: bool):
        """Draw a crisp anti-aliased triangle arrow centred at (cx, cy)."""
        h = size * 0.55      # height of triangle
        hw = size * 0.5      # half-base width
        color = QColor(self._arrow_color)
        if not color.isValid():
            color = QColor("#E6E6E6")
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        path = QPainterPath()
        if pointing_right:
            path.moveTo(cx + h / 2, cy)
            path.lineTo(cx - h / 2, cy - hw)
            path.lineTo(cx - h / 2, cy + hw)
        else:
            path.moveTo(cx - h / 2, cy)
            path.lineTo(cx + h / 2, cy - hw)
            path.lineTo(cx + h / 2, cy + hw)
        path.closeSubpath()
        painter.drawPath(path)

    def _left_button_rect(self):
        return QRectF(0, 0, self._arrow_area_w, self.height())

    def _right_button_rect(self):
        return QRectF(self.width() - self._arrow_area_w, 0, self._arrow_area_w, self.height())

    def _track_rect(self):
        x = self._arrow_area_w + self._margin
        w = max(0, self.width() - (2 * self._arrow_area_w) - (2 * self._margin))
        y = (self.height() - self._bar_h) / 2.0
        return QRectF(x, y, w, self._bar_h)

    def _handle_rect(self):
        tr = self._track_rect()
        if tr.width() <= 0:
            return QRectF()

        min_v = self.minimum()
        max_v = self.maximum()
        page = max(1, self.pageStep())
        rng = max(0, max_v - min_v)
        total = rng + page
        ratio = 1.0 if total <= 0 else (page / float(total))
        handle_w = max(self._min_handle_w, tr.width() * ratio)
        handle_w = min(tr.width(), handle_w)

        usable = max(0.0, tr.width() - handle_w)
        if rng <= 0 or usable <= 0:
            x = tr.left()
        else:
            t = (self.value() - min_v) / float(rng)
            t = max(0.0, min(1.0, t))
            x = tr.left() + t * usable

        return QRectF(x, tr.top(), handle_w, tr.height())

    def _set_value_from_handle_x(self, x_left):
        tr = self._track_rect()
        hr = self._handle_rect()
        min_v = self.minimum()
        max_v = self.maximum()
        rng = max_v - min_v
        usable = max(0.0, tr.width() - hr.width())
        if rng <= 0 or usable <= 0:
            self.setValue(min_v)
            return

        min_x = tr.left()
        max_x = tr.left() + usable
        x_left = max(min_x, min(max_x, x_left))

        # Explicit edge snaps avoid visual/value oscillation at boundaries.
        if x_left <= min_x + 0.5:
            self.setValue(min_v)
            return
        if x_left >= max_x - 0.5:
            self.setValue(max_v)
            return

        t = (x_left - min_x) / usable
        value = min_v + t * rng
        self.setValue(int(round(value)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        tr = self._track_rect()
        hr = self._handle_rect()

        track_color = QColor(self._track_color)
        if track_color.alpha() > 0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(track_color)
            painter.drawRoundedRect(tr, tr.height() / 2.0, tr.height() / 2.0)

        if self._dragging:
            handle_col = QColor(self._handle_pressed_color)
        elif self._hover_part == "handle":
            handle_col = QColor(self._handle_hover_color)
        else:
            handle_col = QColor(self._handle_color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(handle_col)
        painter.drawRoundedRect(hr, hr.height() / 2.0, hr.height() / 2.0)

        # Draw arrows as crisp painted triangles
        arrow_size = max(6, min(self._arrow_area_w - 4, self.height() - 4))
        cy = self.height() / 2.0
        lcx = self._left_button_rect().center().x()
        rcx = self._right_button_rect().center().x()
        self._draw_arrow(painter, lcx, cy, arrow_size, pointing_right=False)
        self._draw_arrow(painter, rcx, cy, arrow_size, pointing_right=True)

        painter.end()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)

        pos = e.position()
        hr = self._handle_rect()
        if hr.contains(pos):
            self._dragging = True
            self._drag_offset = pos.x() - hr.left()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return

        if self._left_button_rect().contains(pos):
            self.setValue(max(self.minimum(), self.value() - self.singleStep()))
            e.accept()
            return
        if self._right_button_rect().contains(pos):
            self.setValue(min(self.maximum(), self.value() + self.singleStep()))
            e.accept()
            return

        tr = self._track_rect()
        if tr.contains(pos):
            if pos.x() < hr.left():
                self.setValue(max(self.minimum(), self.value() - self.pageStep()))
            elif pos.x() > hr.right():
                self.setValue(min(self.maximum(), self.value() + self.pageStep()))
            e.accept()
            return

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._dragging:
            self._set_value_from_handle_x(pos.x() - self._drag_offset)
            e.accept()
            return

        if self._left_button_rect().contains(pos):
            self._hover_part = "left"
        elif self._right_button_rect().contains(pos):
            self._hover_part = "right"
        elif self._handle_rect().contains(pos):
            self._hover_part = "handle"
        elif self._track_rect().contains(pos):
            self._hover_part = "track"
        else:
            self._hover_part = None
        self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, event):
        self._hover_part = None
        if not self._dragging:
            self.unsetCursor()
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = False
            self.unsetCursor()
            self.update()
        super().mouseReleaseEvent(e)
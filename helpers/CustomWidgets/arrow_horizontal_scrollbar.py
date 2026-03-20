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
                 arrow_area_width=16, bar_height=9, margin=2, min_handle_width=26,
                 arrow_width_factor=1.3, arrow_corner_radius=1.5):
        """
        Parameters
        ----------
        arrow_width_factor : float
            Horizontal stretch multiplier for the arrow shape (>1 makes it wider).
            Default 1.3 gives a slightly elongated look. Analogous to how
            CustomDropdown lets you set ``icon_base_size`` vs ``icon_compact_size``.
        arrow_corner_radius : float
            Radius (px) of the rounded corners on the arrow tip and base corners.
            0 = sharp triangle (original behaviour). Default 1.5 for a subtle rounding.
        """
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
        self._arrow_width_factor = float(arrow_width_factor)
        self._arrow_corner_radius = float(arrow_corner_radius)
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

    def set_arrow_style(self, width_factor=None, corner_radius=None):
        """Adjust arrow shape at runtime.

        Parameters
        ----------
        width_factor : float, optional
            Horizontal stretch (>1 = wider arrow).
        corner_radius : float, optional
            Rounded-corner radius on the arrow shape in px.
        """
        if width_factor is not None:
            self._arrow_width_factor = float(width_factor)
        if corner_radius is not None:
            self._arrow_corner_radius = float(corner_radius)
        self.update()

    def _draw_arrow(self, painter, cx, cy, size, pointing_right: bool):
        """Draw a rounded-corner chevron arrow centred at (cx, cy).

        The horizontal span is scaled by ``_arrow_width_factor`` relative to the
        original triangle, while vertical height stays the same — matching the
        CustomDropdown pattern of keeping height fixed and only stretching width.
        Corner rounding is controlled by ``_arrow_corner_radius``.
        """
        # height (horizontal extent along travel axis) and half-width (vertical)
        h  = size * 0.55 * self._arrow_width_factor
        hw = size * 0.5

        color = QColor(self._arrow_color)
        if not color.isValid():
            color = QColor("#E6E6E6")

        cr = max(0.0, min(self._arrow_corner_radius, hw * 0.8, h * 0.8))

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)

        # Build the three triangle vertices then construct a rounded path between them.
        if pointing_right:
            tip  = QPointF(cx + h / 2, cy)           # rightmost point
            top  = QPointF(cx - h / 2, cy - hw)       # top-left
            bot  = QPointF(cx - h / 2, cy + hw)       # bottom-left
        else:
            tip  = QPointF(cx - h / 2, cy)            # leftmost point
            top  = QPointF(cx + h / 2, cy - hw)       # top-right
            bot  = QPointF(cx + h / 2, cy + hw)       # bottom-right

        if cr <= 0.0:
            # Fast path — plain triangle (original behaviour)
            path = QPainterPath()
            path.moveTo(tip)
            path.lineTo(top)
            path.lineTo(bot)
            path.closeSubpath()
            painter.drawPath(path)
            return

        # Rounded triangle: use arcTo at each vertex.
        # We move to the midpoint of each edge and draw arcs at corners.
        def _lerp(a: QPointF, b: QPointF, t: float) -> QPointF:
            return QPointF(a.x() + (b.x() - a.x()) * t,
                           a.y() + (b.y() - a.y()) * t)

        def _dist(a: QPointF, b: QPointF) -> float:
            dx, dy = b.x() - a.x(), b.y() - a.y()
            return (dx*dx + dy*dy) ** 0.5

        verts = [tip, top, bot]
        n = len(verts)
        path = QPainterPath()
        first = True
        for i in range(n):
            prev_v = verts[(i - 1) % n]
            curr_v = verts[i]
            next_v = verts[(i + 1) % n]

            d_in  = _dist(prev_v, curr_v)
            d_out = _dist(curr_v, next_v)
            t_in  = min(cr / d_in,  0.5) if d_in  > 0 else 0.0
            t_out = min(cr / d_out, 0.5) if d_out > 0 else 0.0

            p_in  = _lerp(prev_v, curr_v, 1.0 - t_in)
            p_out = _lerp(curr_v, next_v, t_out)

            if first:
                path.moveTo(p_in)
                first = False
            else:
                path.lineTo(p_in)
            path.quadTo(curr_v, p_out)

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
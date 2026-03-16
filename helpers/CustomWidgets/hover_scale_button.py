from ._shared import *

class HoverScaleButton(QPushButton):
    """A QPushButton variant that scales on hover/press with rounded-style control.

    - Animates geometry for hover grow and press shrink interactions.
    - Preserves a base geometry so layout recalculations remain stable.
    - Allows forcing border radius/text color while keeping caller stylesheets.

    Usage
    -----
        btn = HoverScaleButton("Run", parent=some_widget, border_radius=12)
        btn.set_text_color("#FFFFFF")
        btn.clicked.connect(do_work)
    """

    def __init__(
        self,
        text="",
        parent=None,
        scale_factor=1.05,
        duration=140,
        click_scale_factor=0.97,
        border_radius=None,
        text_color=None,
    ):
        super().__init__(text, parent)
        # Force stylesheet-based rendering so border-radius is respected on all platforms.
        self.setFlat(True)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._forced_border_radius = None
        self._forced_text_color = None
        self._raw_stylesheet = ""
        self._scale_factor = scale_factor
        self._click_scale_factor = click_scale_factor
        self._duration = duration
        self._base_geometry = QRect()
        self._pressed = False
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(self._duration)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.set_border_radius(border_radius)
        self.set_text_color(text_color)

    def setStyleSheet(self, styleSheet):
        self._raw_stylesheet = styleSheet or ""
        super().setStyleSheet(self._compose_stylesheet())

    def setGeometry(self, *args):
        super().setGeometry(*args)
        if not self.underMouse():
            self._base_geometry = QRect(self.geometry())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def event(self, event):
        if event.type() in (QEvent.StyleChange, QEvent.Polish, QEvent.PaletteChange):
            self.update()
        if event.type() == QEvent.Enter:
            if self._pressed:
                return super().event(event)
            if self._base_geometry.isNull():
                self._base_geometry = QRect(self.geometry())
            self._animate_to(self._scaled_rect())
        elif event.type() == QEvent.Leave:
            if self._pressed:
                return super().event(event)
            if not self._base_geometry.isNull():
                self._animate_to(self._base_geometry)
        return super().event(event)

    def _scaled_rect(self):
        base = self._base_geometry if not self._base_geometry.isNull() else self.geometry()
        w = int(round(base.width() * self._scale_factor))
        h = int(round(base.height() * self._scale_factor))
        x = base.x() - (w - base.width()) // 2
        y = base.y() - (h - base.height()) // 2
        return QRect(x, y, w, h)

    def _pressed_rect(self):
        base = self._base_geometry if not self._base_geometry.isNull() else self.geometry()
        w = int(round(base.width() * self._click_scale_factor))
        h = int(round(base.height() * self._click_scale_factor))
        x = base.x() - (w - base.width()) // 2
        y = base.y() - (h - base.height()) // 2
        return QRect(x, y, w, h)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            if self._base_geometry.isNull():
                self._base_geometry = QRect(self.geometry())
            self._animate_to(self._pressed_rect())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = False
            target = self._scaled_rect() if self.underMouse() else self._base_geometry
            if not target.isNull():
                self._animate_to(target, QEasingCurve.OutBack)
        super().mouseReleaseEvent(event)

    def _animate_to(self, target, easing=None):
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(target)
        self._anim.setEasingCurve(easing if easing is not None else QEasingCurve.OutCubic)
        self._anim.start()

    def set_border_radius(self, radius):
        if radius is None:
            self._forced_border_radius = None
            super().setStyleSheet(self._compose_stylesheet())
            self.update()
            return
        try:
            self._forced_border_radius = float(radius)
        except Exception:
            self._forced_border_radius = None
            super().setStyleSheet(self._compose_stylesheet())
            self.update()
            return
        super().setStyleSheet(self._compose_stylesheet())
        self.update()

    def border_radius(self):
        return self._forced_border_radius

    def _rounded_path(self):
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self._forced_border_radius, self._forced_border_radius, Qt.AbsoluteSize)
        return path

    def _selector_block(self, selector):
        if not self._raw_stylesheet:
            return ""
        pattern = rf"{re.escape(selector)}\s*\{{([^}}]*)\}}"
        m = re.search(pattern, self._raw_stylesheet, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        return m.group(1)

    def _css_value(self, selector, prop):
        block = self._selector_block(selector)
        if not block:
            return None
        m = re.search(rf"{re.escape(prop)}\s*:\s*([^;]+);?", block, flags=re.IGNORECASE)
        if not m:
            return None
        return m.group(1).strip()

    def _resolve_color(self, value, fallback):
        if not value:
            return QColor(fallback)
        c = QColor(value)
        return c if c.isValid() else QColor(fallback)

    def _resolve_border(self, selector):
        border = self._css_value(selector, "border")
        if not border:
            return 0.0, None
        m = re.search(
            r"([0-9]+(?:\.[0-9]+)?)px\s+(?:solid|dashed|dotted|double)?\s*([#A-Za-z0-9(),.\s]+)",
            border,
            flags=re.IGNORECASE,
        )
        if not m:
            return 0.0, None
        try:
            width = float(m.group(1))
        except Exception:
            width = 0.0
        color = QColor(m.group(2).strip())
        if not color.isValid():
            return width, None
        return width, color

    def set_text_color(self, color):
        if color is None:
            self._forced_text_color = None
            self.update()
            return
        q = QColor(color)
        self._forced_text_color = q if q.isValid() else None
        self.update()

    def text_color(self):
        return QColor(self._forced_text_color) if self._forced_text_color is not None else None

    def _compose_stylesheet(self):
        base = self._raw_stylesheet or ""
        if self._forced_border_radius is None:
            return base
        r = max(0.0, float(self._forced_border_radius))
        forced = (
            f"\nQPushButton {{ border-radius: {r}px; }}"
            f"\nQPushButton:hover {{ border-radius: {r}px; }}"
            f"\nQPushButton:pressed {{ border-radius: {r}px; }}"
            f"\nQPushButton:checked {{ border-radius: {r}px; }}"
        )
        return base + forced

    def paintEvent(self, event):
        if self._forced_border_radius is None or self.width() <= 0 or self.height() <= 0:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        path = self._rounded_path()

        normal_bg = self._resolve_color(self._css_value("QPushButton", "background-color"), self.palette().button().color())
        hover_bg = self._resolve_color(self._css_value("QPushButton:hover", "background-color"), normal_bg.lighter(105))
        pressed_bg = self._resolve_color(self._css_value("QPushButton:pressed", "background-color"), hover_bg.darker(108))
        checked_bg = self._resolve_color(self._css_value("QPushButton:checked", "background-color"), hover_bg)

        normal_fg = self._resolve_color(self._css_value("QPushButton", "color"), self.palette().buttonText().color())
        hover_fg = self._resolve_color(self._css_value("QPushButton:hover", "color"), normal_fg)
        pressed_fg = self._resolve_color(self._css_value("QPushButton:pressed", "color"), hover_fg)
        checked_fg = self._resolve_color(self._css_value("QPushButton:checked", "color"), hover_fg)

        if not self.isEnabled():
            bg = QColor(normal_bg)
            fg = QColor(normal_fg)
            bg.setAlpha(max(60, bg.alpha() // 2))
            fg.setAlpha(max(80, fg.alpha() // 2))
            bw, bc = self._resolve_border("QPushButton")
        elif self.isDown():
            bg = pressed_bg
            fg = pressed_fg
            bw, bc = self._resolve_border("QPushButton:pressed")
            if bw <= 0:
                bw, bc = self._resolve_border("QPushButton")
        elif self.isChecked():
            bg = checked_bg
            fg = checked_fg
            bw, bc = self._resolve_border("QPushButton:checked")
            if bw <= 0:
                bw, bc = self._resolve_border("QPushButton")
        elif self.underMouse():
            bg = hover_bg
            fg = hover_fg
            bw, bc = self._resolve_border("QPushButton:hover")
            if bw <= 0:
                bw, bc = self._resolve_border("QPushButton")
        else:
            bg = normal_bg
            fg = normal_fg
            bw, bc = self._resolve_border("QPushButton")

        if bw > 0 and bc is not None:
            # Fill-based border: outer border color + inner background color.
            # This avoids stroke-centric AA artifacts that make side borders look heavier.
            outer_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            outer_r = max(0.0, float(self._forced_border_radius))
            outer_path = QPainterPath()
            outer_path.addRoundedRect(outer_rect, outer_r, outer_r, Qt.AbsoluteSize)
            painter.fillPath(outer_path, bc)

            inset = float(bw)
            inner_rect = outer_rect.adjusted(inset, inset, -inset, -inset)
            if inner_rect.width() > 0.0 and inner_rect.height() > 0.0:
                inner_r = max(0.0, outer_r - inset)
                inner_path = QPainterPath()
                inner_path.addRoundedRect(inner_rect, inner_r, inner_r, Qt.AbsoluteSize)
                painter.fillPath(inner_path, bg)
            else:
                painter.fillPath(outer_path, bg)
        else:
            painter.fillPath(path, bg)

        painter.setFont(self.font())
        if self._forced_text_color is not None:
            painter.setPen(self._forced_text_color)
        else:
            painter.setPen(fg)
        painter.setBrush(Qt.NoBrush)
        painter.drawText(self.rect(), Qt.AlignCenter | Qt.TextSingleLine, self.text())
        painter.end()


# RoundedFrame: draws a pill with configurable corner radii and optional border


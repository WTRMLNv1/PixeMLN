from ._shared import *

class RoundedFrame(QFrame):
    """A QFrame that paints configurable rounded corners, border, and right-arrow zone.

    - Supports per-corner radii and optional anti-aliased border rendering.
    - Can paint a dedicated arrow background strip on the right.
    - Arrow indicator supports either pixmap icons or vector chevron drawing.

    Usage
    -----
        frame = RoundedFrame(parent=some_widget, tl=16, tr=16, br=16, bl=16)
        frame.set_bg_color("#303030")
        frame.set_arrow_style(size=(12, 10), angle=0)
    """

    def __init__(self, parent=None, tl=20, tr=20, br=20, bl=20,
                 make_border=True, border_color=None, border_width=1, border_opacity=1.0,
                 arrow_bg_color="#505050", bg_color="#303030"):
        super().__init__(parent)
        self.r = (tl, tr, br, bl)

        self.make_border = make_border
        self.border_width = border_width
        self.border_opacity = border_opacity
        self._border_color = border_color

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._bg_color = QColor(bg_color)
        # width of a painted arrow-area on the right (0 = none)
        self.arrow_w = 0
        self.arrow_bg_color = arrow_bg_color
        self._arrow_icon_pix = None
        self._arrow_icon_width = 13
        self._arrow_icon_height = 12
        self._arrow_icon_angle = 0.0
        self._arrow_icon_offset_y = 0
        self._arrow_icon_color = QColor("#B0B0B0")
        self._arrow_use_pixmap = False

    def set_bg_color(self, color):
        self._bg_color = QColor(color)
        self.update()

    def set_arrow_icon(self, pixmap):
        self._arrow_icon_pix = pixmap
        self.update()

    def set_arrow_style(self, size=None, angle=None, offset_y=None):
        if size is not None:
            if isinstance(size, QSize):
                self._arrow_icon_width = max(1, int(size.width()))
                self._arrow_icon_height = max(1, int(size.height()))
            elif isinstance(size, (tuple, list)) and len(size) == 2:
                self._arrow_icon_width = max(1, int(size[0]))
                self._arrow_icon_height = max(1, int(size[1]))
            else:
                s = max(1, int(size))
                self._arrow_icon_width = s
                self._arrow_icon_height = s
        if angle is not None:
            self._arrow_icon_angle = float(angle)
        if offset_y is not None:
            self._arrow_icon_offset_y = int(offset_y)
        self.update()

    def set_arrow_color(self, color):
        self._arrow_icon_color = QColor(color)
        self.update()

    def set_arrow_use_pixmap(self, use_pixmap):
        self._arrow_use_pixmap = bool(use_pixmap)
        self.update()

    def _path(self):
        w, h = self.width(), self.height()
        tl, tr, br, bl = self.r

        # clamp so radii never explode
        tl = min(tl, w // 2, h // 2)
        tr = min(tr, w // 2, h // 2)
        br = min(br, w // 2, h // 2)
        bl = min(bl, w // 2, h // 2)

        path = QPainterPath()
        path.moveTo(tl, 0)
        path.lineTo(w - tr, 0)
        path.quadTo(w, 0, w, tr)
        path.lineTo(w, h - br)
        path.quadTo(w, h, w - br, h)
        path.lineTo(bl, h)
        path.quadTo(0, h, 0, h - bl)
        path.lineTo(0, tl)
        path.quadTo(0, 0, tl, 0)

        return path

    def _inset_path(self, inset):
        path = self._path()
        rect = QRectF(
            float(inset),
            float(inset),
            max(0.0, float(self.width()) - 2.0 * float(inset)),
            max(0.0, float(self.height()) - 2.0 * float(inset))
        )

        tl, tr, br, bl = self.r
        tl = max(0, tl - inset)
        tr = max(0, tr - inset)
        br = max(0, br - inset)
        bl = max(0, bl - inset)

        p = QPainterPath()
        p.moveTo(rect.left() + tl, rect.top())
        p.lineTo(rect.right() - tr, rect.top())
        p.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + tr)
        p.lineTo(rect.right(), rect.bottom() - br)
        p.quadTo(rect.right(), rect.bottom(), rect.right() - br, rect.bottom())
        p.lineTo(rect.left() + bl, rect.bottom())
        p.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - bl)
        p.lineTo(rect.left(), rect.top() + tl)
        p.quadTo(rect.left(), rect.top(), rect.left() + tl, rect.top())
        return p

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        main_path = self._path()

        # main pill
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawPath(main_path)

        # arrow background (right side) if requested
        try:
            aw = int(self.arrow_w)
        except Exception:
            aw = 0

        if aw > 0 and aw < self.width():
            arrow_rect = QRect(self.width() - aw, 0, aw, self.height())
            arrow_path = QPainterPath()
            arrow_path.addRoundedRect(
                arrow_rect,
                self.r[1],  # top-right radius
                self.r[2]   # bottom-right radius
            )
            painter.fillPath(arrow_path, QColor(self.arrow_bg_color))
            icon_w = max(1, int(self._arrow_icon_width))
            icon_h = max(1, int(self._arrow_icon_height))
            cx = float(arrow_rect.center().x())
            cy = float(arrow_rect.center().y() + self._arrow_icon_offset_y)
            if self._arrow_use_pixmap and self._arrow_icon_pix is not None and not self._arrow_icon_pix.isNull():
                painter.save()
                painter.translate(cx, cy)
                painter.rotate(float(self._arrow_icon_angle))
                painter.translate(-cx, -cy)
                fitted = self._arrow_icon_pix.size().scaled(icon_w, icon_h, Qt.KeepAspectRatio)
                draw_w = max(1, fitted.width())
                draw_h = max(1, fitted.height())
                draw_x = int(round(cx - draw_w / 2.0))
                draw_y = int(round(cy - draw_h / 2.0))
                target = QRect(draw_x, draw_y, draw_w, draw_h)
                painter.drawPixmap(target, self._arrow_icon_pix)
                painter.restore()
            else:
                half_w = icon_w / 2.0
                half_h = icon_h / 2.0
                stroke_w = max(1.5, min(icon_w, icon_h) / 6.0)

                painter.save()
                painter.translate(cx, cy)
                painter.rotate(float(self._arrow_icon_angle))
                painter.translate(-cx, -cy)

                pen = QPen(self._arrow_icon_color)
                pen.setWidthF(stroke_w)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)

                # Use a taller chevron profile so it doesn't look vertically compressed.
                top_y = cy - (half_h * 0.65)
                bottom_y = cy + (half_h * 0.65)
                path = QPainterPath()
                path.moveTo(cx - half_w, top_y)
                path.lineTo(cx, bottom_y)
                path.lineTo(cx + half_w, top_y)
                painter.drawPath(path)
                painter.restore()

        if self.make_border and self.border_width > 0:
            inset = self.border_width / 2
            border_path = self._inset_path(inset)

            pen = painter.pen()
            pen_color = QColor(self._border_color) if self._border_color else self.palette().mid().color()
            pen_color.setAlphaF(self.border_opacity)
            pen.setColor(pen_color)
            pen.setWidthF(self.border_width)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            painter.drawPath(border_path)

        painter.end()


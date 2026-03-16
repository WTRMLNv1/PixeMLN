import os
from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton
from PySide6.QtGui import QFont, QPainterPath, QRegion, QPainter, QColor, QPixmap, QIcon, QTransform
from PySide6.QtCore import Qt, QRect, QSize, QPropertyAnimation, QObject, Property, QEasingCurve

#───class <RoundedFrame(parent, corner radii: tl | tr | br | bl, make_border, border_color, border_width, border_opacity)───#
class RoundedFrame(QFrame):
    def __init__(self, parent=None, tl=20, tr=20, br=20, bl=20,
                 make_border=True, border_color=None, border_width=1, border_opacity=1.0):
        super().__init__(parent)
        self.r = (tl, tr, br, bl)

        self.make_border = make_border
        self.border_width = border_width
        self.border_opacity = border_opacity
        self._border_color = border_color

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        # width of a painted arrow-area on the right (0 = none)
        self.arrow_w = 0

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
        rect = QRect(
            inset,
            inset,
            self.width() - 2 * inset,
            self.height() - 2 * inset
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
        path = self._path()
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # main pill
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().window())
        painter.drawPath(self._path())

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
            painter.fillPath(arrow_path, QColor("#505050"))

        if self.make_border and self.border_width > 0:
            inset = self.border_width / 2
            border_path = self._inset_path(inset)

            pen = painter.pen()
            pen_color = QColor(self._border_color) if self._border_color else self.palette().mid().color()
            pen_color.setAlphaF(self.border_opacity)
            pen.setColor(pen_color)
            pen.setWidthF(self.border_width)
            painter.setPen(pen)

            painter.drawPath(border_path)

        painter.end()

#───class <CustomDropdown>(parent, items, x, y, width)───#

class CustomDropdown(QWidget):
    def __init__(self, parent, items, x, y, width=361):
        super().__init__(parent)
        self.option_buttons = []
        self.items = items
        self.selected = None
        self.setGeometry(x, y, width, 22)
        self.arrow_open = False

        # ── closed box ──────────────────────────────
        # main pill (draws its own border)
        self.box = RoundedFrame(self, tl=20, tr=20, br=20, bl=20,
                                make_border=False)#, border_color="#707070", border_width=1, border_opacity=1.0)
        self.box.setGeometry(0, 0, width, 22)
        self.box.setStyleSheet("""
            QFrame {
                background-color: #3e3e3e;
            }
        """)

        # placeholder / selected text
        self.label = QLabel("Choose graph name", self.box)
        self.label.setGeometry(10, 0, width - 50, 22)
        f = QFont()
        f.setPointSize(12)
        self.label.setFont(f)
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.label.setStyleSheet("""
            QLabel {
                color: #808080;
                background: transparent;
                border: none;
            }
        """)

        # arrow button (icon if available). Background is painted by `self.box`.
        self.arrow = QPushButton(self.box)
        self.arrow.setGeometry(width - 33, 0, 33, 22)
        self.arrow.setFlat(True)
        self.arrow.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: white; }
            QPushButton:hover { background-color: rgba(255,255,255,0.03); }
        """)
        # tell the rounded frame to paint an arrow-area of this width
        try:
            self.box.arrow_w = 33
        except Exception:
            pass

        # try to load BASE_DIR/dropdown_arrow.png (several fallbacks)
        base_try_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'dropdown_arrow.png'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'dropdown_arrow.png'),
            os.path.join(os.path.dirname(__file__), '..', 'assets', 'dropdown_arrow.png'),
        ]
        icon_set = False
        self._orig_arrow_pix = None
        for p in base_try_paths:
            p = os.path.normpath(p)
            if os.path.exists(p):
                pix = QPixmap(p)
                if not pix.isNull():
                    icon = QIcon(pix)
                    self.arrow.setIcon(icon)
                    self.arrow.setIconSize(QSize(12, 12))
                    self._orig_arrow_pix = pix
                    icon_set = True
                    break

        if not icon_set:
            # render the arrow character into a pixmap so we can rotate it smoothly
            px = QPixmap(16, 16)
            px.fill(Qt.transparent)
            p = QPainter(px)
            p.setRenderHint(QPainter.Antialiasing)
            fnt = QFont()
            fnt.setPointSize(12)
            p.setFont(fnt)
            p.setPen(QColor("white"))
            p.drawText(px.rect(), Qt.AlignCenter, "▾")
            p.end()
            self._orig_arrow_pix = px
            self.arrow.setIcon(QIcon(self._orig_arrow_pix))
            self.arrow.setIconSize(QSize(12, 12))

        # prepare animator that will call back with angle updates
        class _AngleAnimator(QObject):
            def __init__(self, cb):
                super().__init__()
                self._angle = 0.0
                self._cb = cb

            def _get(self):
                return self._angle

            def _set(self, v):
                self._angle = float(v)
                try:
                    self._cb(self._angle)
                except Exception:
                    pass

            angle = Property(float, _get, _set)

        self._angle_obj = _AngleAnimator(self._update_arrow_angle)
        self._angle_anim = QPropertyAnimation(self._angle_obj, b'angle')
        self._angle_anim.setDuration(100)
        self._angle_anim.setEasingCur1ve(QEasingCurve.OutCubic)

        self.arrow.clicked.connect(self.toggle_dropdown)

        # ensure initial icon angle
        if self._orig_arrow_pix is not None:
            self._update_arrow_angle(0)

        # ── dropdown ────────────────────────────────
        # dropdown uses RoundedFrame so clipping and borders are real
        self.dropdown = RoundedFrame(parent, tl=20, tr=20, br=20, bl=20,
                                     make_border=True, border_color=None, border_width=1, border_opacity=1.0)
        self.row_h = 30
        drop_h = self.row_h * len(items)
        self.dropdown.setGeometry(x, y + 26, width, drop_h)
        self.dropdown.setStyleSheet("""
            QFrame {
                background-color: #3e3e3e;
            }
        """)
        self.dropdown.hide()

        # watch parent clicks to close dropdown when clicking outside
        try:
            parent.installEventFilter(self)
        except Exception:
            pass

        for i, text in enumerate(items):
            btn = QPushButton(text, self.dropdown)
            btn.setGeometry(16, i * self.row_h, width - 32, self.row_h)

            bf = QFont()
            bf.setPointSize(12)
            btn.setFont(bf)

            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding-left: 8px;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)

            btn.clicked.connect(lambda checked=False, b=btn, t=text: self.select(b, t))
            self.option_buttons.append(btn)


            # divider
            if i < len(items) - 1:
                div = QFrame(self.dropdown)
                div.setGeometry(16, (i + 1) * self.row_h - 1, width - 32, 1)
                div.setStyleSheet("background-color: rgba(144,144,144,128);")

    # ── behavior ──────────────────────────────────
    def toggle_dropdown(self):
        if self.arrow_open:
            self._close_dropdown()
        else:
            self._open_dropdown()

    def _open_dropdown(self):
        try:
            self.dropdown.show()
            self.dropdown.raise_()
            self._angle_anim.stop()
            self._angle_anim.setStartValue(0)
            self._angle_anim.setEndValue(180)
            self._angle_anim.start()
            self.arrow_open = True
        except Exception:
            pass

    def _close_dropdown(self):
        try:
            self._angle_anim.stop()
            self._angle_anim.setStartValue(180)
            self._angle_anim.setEndValue(0)
            # hide when finished
            def _on_finished():
                try:
                    self.dropdown.hide()
                except Exception:
                    pass
                try:
                    self._angle_anim.finished.disconnect(_on_finished)
                except Exception:
                    pass

            try:
                self._angle_anim.finished.connect(_on_finished)
            except Exception:
                pass

            self._angle_anim.start()
            self.arrow_open = False
        except Exception:
            pass

    def eventFilter(self, obj, event):
        # close dropdown if visible and click occurs outside it
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.MouseButtonPress and self.dropdown.isVisible():
            # event.pos() is in coordinate space of obj
            try:
                gpos = event.globalPos()
                # map global pos to dropdown parent coords
                parent_widget = self.dropdown.parent()
                local = parent_widget.mapFromGlobal(gpos)
                if not self.dropdown.geometry().contains(local):
                    # animate-close so arrow rotates back
                    try:
                        self._close_dropdown()
                    except Exception:
                        self.dropdown.hide()
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def select(self, button, text):
        self.selected = text

        # reset all buttons
        for btn in self.option_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding-left: 8px;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)

        button.setStyleSheet("""
            QPushButton {
                color: #1e1e1e;
                background-color: #5BF69F;
                border: none;
                text-align: left;
                padding-left: 8px;
                border-radius: 15px;
            }
        """)

        # update label
        self.label.setText(text)
        self.label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)

        # animate-close the dropdown so the arrow rotates back
        try:
            self._close_dropdown()
        except Exception:
            self.dropdown.hide()



    def value(self):
        return self.selected

    def _update_arrow_angle(self, angle):
        # rotate the original pixmap by `angle` degrees and set as icon
        try:
            if not self._orig_arrow_pix:
                return
            transform = QTransform()
            transform.rotate(angle)
            rotated = self._orig_arrow_pix.transformed(transform, Qt.SmoothTransformation)
            self.arrow.setIcon(QIcon(rotated))
            # keep icon size consistent
            self.arrow.setIconSize(QSize(12, 12))
        except Exception:
            pass

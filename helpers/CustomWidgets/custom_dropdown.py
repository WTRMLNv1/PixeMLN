from ._shared import *
from .rounded_frame import RoundedFrame
from .circle_scrollbar import CircleScrollBar
from PySide6.QtWidgets import QApplication

class CustomDropdown(QWidget):
    """A rounded custom dropdown with animated open/close and theme-aware selection.

    - Uses a trigger pill plus a separate rounded popup list.
    - Supports arrow flip behavior, hover states, and outside-click close.
    - Exposes selected value via `value()` / `set_value()` and optional callback.

    Usage
    -----
        dd = CustomDropdown(
            parent=some_widget,
            items=["A", "B", "C"],
            x=20,
            y=20,
            on_select=lambda text: print(text),
        )
        dd.set_value("B")
    """

    def __init__(self, parent, items, x, y, width=361, placeholder="Choose graph name",
                 icon_path=None, rotate_icon=True, icon_base_size=12, icon_compact_size=6, on_select=None,
                 dropdown_color="#3e3e3e", arrow_button_color=None, arrow_color="#646464",
                 box_color=None, arrow_type="large"):
        super().__init__(parent)
        self.option_buttons = []
        self.items = items
        self.selected = None
        self.rotate_icon = bool(rotate_icon)
        self._on_select_cb = on_select
        self._icon_base_size = int(icon_base_size)
        self._icon_compact_size = int(icon_compact_size)
        self._icon_current_size = self._icon_base_size
        self._theme = get_theme()
        self._dropdown_color = dropdown_color
        self._arrow_color = arrow_color
        self._box_color = box_color if box_color is not None else dropdown_color
        self._arrow_button_color = self._box_color if arrow_button_color is None else arrow_button_color
        self._trigger_hover_color = "#4a4a4a"
        self._trigger_hovered = False
        self._large_hover_scale = 0.95
        self._large_arrow_extra_px = 2
        self.arrow_type = str(arrow_type).strip().lower()
        if self.arrow_type not in ("large", "small"):
            self.arrow_type = "large"
        self._small_arrow_hovered = False
        self._small_arrow_shift_px = 1
        self._small_arrow_offset_y = 0.0
        self._small_offset_obj = None
        self._small_offset_anim = None

        if self.arrow_type == "small":
            self._icon_current_size = self._icon_compact_size

        self._enable_flip_animation = self.rotate_icon and self.arrow_type == "large"
        self.setGeometry(x, y, width, 22)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)
        self.arrow_open = False
        self._arrow_angle = 0.0

        # main pill (draws its own border)
        self.box = RoundedFrame(self, tl=20, tr=20, br=20, bl=20,
                                make_border=True, border_color="#8c8c8c", border_width=1, border_opacity=1.0)
        self.box.setGeometry(0, 0, width, 22)
        self.box.setMouseTracking(True)
        self.box.setAttribute(Qt.WA_Hover, True)
        self.box.set_bg_color(self._box_color)
        self._vector_arrow_base_w = int(self.box._arrow_icon_width)
        self._vector_arrow_base_h = int(self.box._arrow_icon_height)

        # placeholder / selected text
        self.label = QLabel(placeholder, self.box)
        self.label.setGeometry(10, 0, width - 50, 22)
        self.label.setMouseTracking(True)
        self.label.setAttribute(Qt.WA_Hover, True)
        mono_family = "Roboto Mono"
        app = QApplication.instance()
        if app is not None:
            try:
                mono_family = app.property("pixemln_font_mono") or mono_family
            except Exception:
                pass
        f = QFont(mono_family)
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

        try:
            self.box.installEventFilter(self)
            self.label.installEventFilter(self)
        except Exception:
            pass
        # tell the rounded frame to paint an arrow-area of this width
        try:
            self.box.arrow_w = 33
            self.box.arrow_bg_color = self._arrow_button_color
        except Exception:
            pass
        self._apply_trigger_background()

        # try to load provided icon or BASE_DIR/dropdown_arrow.png (several fallbacks)
        base_try_paths = [
            icon_path,
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dropdown_arrow.png'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'dropdown_arrow.png'),
            os.path.join(os.path.dirname(__file__), '..', 'assets', 'dropdown_arrow.png'),
        ]
        icon_set = False
        self._orig_arrow_pix = None
        self._arrow_source_pix = None
        self._use_custom_arrow_icon = False
        for p in base_try_paths:
            if not p:
                continue
            p = os.path.normpath(p)
            if os.path.exists(p):
                pix = QPixmap(p)
                if not pix.isNull():
                    self._arrow_source_pix = pix
                    icon_set = True
                    if icon_path and os.path.normpath(icon_path) == p:
                        self._use_custom_arrow_icon = True
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
            self._arrow_source_pix = px
            self._use_custom_arrow_icon = False

        try:
            self.box.set_arrow_use_pixmap(self._use_custom_arrow_icon)
        except Exception:
            pass
        self._apply_arrow_color()

        self._angle_obj = None
        self._angle_anim = None
        if self._enable_flip_animation:
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
            self._angle_anim.setDuration(300)
            self._angle_anim.setEasingCurve(QEasingCurve.OutBack)
        elif self.arrow_type == "small":
            class _OffsetAnimator(QObject):
                def __init__(self, cb):
                    super().__init__()
                    self._offset = 0.0
                    self._cb = cb

                def _get(self):
                    return self._offset

                def _set(self, v):
                    self._offset = float(v)
                    try:
                        self._cb(self._offset)
                    except Exception:
                        pass

                offset = Property(float, _get, _set)

            self._small_offset_obj = _OffsetAnimator(self._apply_small_arrow_offset)
            self._small_offset_anim = QPropertyAnimation(self._small_offset_obj, b'offset')
            self._small_offset_anim.setDuration(100)
            self._small_offset_anim.setEasingCurve(QEasingCurve.OutCubic)

        # ensure initial icon angle
        if self._enable_flip_animation and self._orig_arrow_pix is not None:
            self._update_arrow_angle(0)
        elif self.arrow_type == "small" and self._orig_arrow_pix is not None:
            self._set_arrow_angle(0)

        # dropdown uses RoundedFrame so clipping and borders are real
        self.dropdown = RoundedFrame(parent, tl=20, tr=20, br=20, bl=20,
                                     make_border=True, border_color=None, border_width=1, border_opacity=1.0)
        self.row_h = 33
        visible_rows = min(3, len(items)) if len(items) > 0 else 1
        drop_h = self.row_h * visible_rows + 2
        self.dropdown.setGeometry(x, y + 26, width, drop_h)
        self.dropdown.set_bg_color(self._dropdown_color)
        self.dropdown.hide()
        apply_widget_shadow(self.dropdown, radius=20)
        self._dropdown_full_h = int(drop_h)
        self._drop_anim_closing = False
        self._drop_anim = QPropertyAnimation(self.dropdown, b"geometry", self)
        self._drop_anim.setDuration(180)
        self._drop_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._drop_anim.finished.connect(self._on_drop_anim_finished)

        self.inner_frame = QFrame(self.dropdown)
        self.inner_frame.setGeometry(1, 1, width - 2, drop_h - 2)
        self.inner_frame.setStyleSheet("background: transparent; border: none;")

        self.scroll = QScrollArea(self.inner_frame)
        self.scroll.setGeometry(0, 0, width - 2, drop_h - 2)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.viewport().setStyleSheet("background: transparent;")
        self.scroll.setVerticalScrollBar(
            CircleScrollBar(Qt.Vertical, self.scroll, handle_d=10, margin_top=12, margin_bottom=12, margin_right=6, track_w=10)
        )

        self.scroll_content = QWidget()
        min_h = self.row_h * len(items) if len(items) > 0 else self.row_h
        self.scroll_content.setMinimumHeight(min_h)
        self.scroll_content.setMinimumWidth(width)
        self.scroll.setWidget(self.scroll_content)

        # watch parent clicks to close dropdown when clicking outside
        try:
            parent.installEventFilter(self)
        except Exception:
            pass

        for i, text in enumerate(items):
            btn = QPushButton(text, self.scroll_content)
            btn.setGeometry(10, i * self.row_h, width - 22, self.row_h)

            bf = QFont()
            bf.setPointSize(12)
            btn.setFont(bf)

            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding-left: 5px;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)

            btn.clicked.connect(lambda checked=False, b=btn, t=text: self.select(b, t))
            self.option_buttons.append(btn)

            # divider
            if i < len(items) - 1:
                div = QFrame(self.scroll_content)
                div.setGeometry(16, (i + 1) * self.row_h - 1, width - 32, 1)
                div.setStyleSheet("background-color: rgba(144,144,144,128);")

        if len(items) == 0:
            empty = QLabel("No graphs found", self.scroll_content)
            empty.setGeometry(0, 0, width, self.row_h)
            ef = QFont()
            ef.setPointSize(11)
            empty.setFont(ef)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #9a9a9a; background: transparent;")

    # behavior
    def toggle_dropdown(self):
        if self.arrow_open:
            self._close_dropdown()
        else:
            self._open_dropdown()

    def _open_dropdown(self):
        try:
            full_geo = QRect(self.x(), self.y() + 26, self.width(), self._dropdown_full_h)
            start_geo = QRect(full_geo.x(), full_geo.y(), full_geo.width(), 0)

            self._drop_anim_closing = False
            self._drop_anim.stop()
            self.dropdown.setGeometry(start_geo)
            self.dropdown.show()
            self.dropdown.raise_()
            self._drop_anim.setStartValue(start_geo)
            self._drop_anim.setEndValue(full_geo)
            self._drop_anim.start()
            QTimer.singleShot(0, self._scroll_to_selected_option)
            if self._enable_flip_animation and self._angle_anim is not None:
                self._angle_anim.stop()
                self._angle_anim.setStartValue(0)
                self._angle_anim.setEndValue(180)
                self._angle_anim.start()
            elif self.arrow_type == "small":
                self._set_arrow_angle(180)
            self.arrow_open = True
        except Exception:
            pass

    def _scroll_to_selected_option(self):
        try:
            if not self.option_buttons or not self.selected:
                return

            target_btn = None
            for btn in self.option_buttons:
                if btn.text() == self.selected:
                    target_btn = btn
                    break
            if target_btn is None:
                return

            vbar = self.scroll.verticalScrollBar()
            if vbar is None or vbar.maximum() <= vbar.minimum():
                return

            viewport_h = self.scroll.viewport().height()
            if viewport_h <= 0:
                return

            btn_top = target_btn.y()
            btn_h = target_btn.height()
            desired = btn_top - max(0, (viewport_h - btn_h) // 2)
            desired = max(vbar.minimum(), min(vbar.maximum(), int(desired)))
            vbar.setValue(desired)
        except Exception:
            pass

    def _close_dropdown(self):
        try:
            full_geo = QRect(self.dropdown.geometry())
            end_geo = QRect(full_geo.x(), full_geo.y(), full_geo.width(), 0)

            self._drop_anim_closing = True
            self._drop_anim.stop()
            self._drop_anim.setStartValue(full_geo)
            self._drop_anim.setEndValue(end_geo)
            self._drop_anim.start()

            if self._enable_flip_animation and self._angle_anim is not None:
                self._angle_anim.stop()
                self._angle_anim.setStartValue(180)
                self._angle_anim.setEndValue(0)
            if self._enable_flip_animation and self._angle_anim is not None:
                self._angle_anim.start()
            elif self.arrow_type == "small":
                self._set_arrow_angle(0)
            self.arrow_open = False
        except Exception:
            pass

    def _on_drop_anim_finished(self):
        if not self._drop_anim_closing:
            return
        try:
            self.dropdown.hide()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj in (self.box, self.label) and event.type() == QEvent.Enter:
            self._set_trigger_hovered(True)
        if obj in (self.box, self.label) and event.type() == QEvent.Leave:
            if not (self.underMouse() or self.box.underMouse() or self.label.underMouse()):
                self._set_trigger_hovered(False)
        if obj in (self.box, self.label) and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.toggle_dropdown()
                return True
        if event.type() == QEvent.MouseButtonPress and self.dropdown.isVisible():
            try:
                gpos = event.globalPos()
                parent_widget = self.dropdown.parent()
                local = parent_widget.mapFromGlobal(gpos)
                # Ignore this "outside" close when the user actually clicked
                # on this dropdown's own trigger area.
                local_self = self.mapFromGlobal(gpos)
                if self.rect().contains(local_self):
                    return super().eventFilter(obj, event)
                if not self.dropdown.geometry().contains(local):
                    try:
                        self._close_dropdown()
                    except Exception:
                        self.dropdown.hide()
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self._set_trigger_hovered(True)
        super().enterEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._set_trigger_hovered(False)
        super().leaveEvent(event)

    def event(self, event):
        return super().event(event)

    def _apply_trigger_background(self):
        bg = self._trigger_hover_color if self._trigger_hovered else self._box_color
        arrow_bg = self._trigger_hover_color if self._trigger_hovered else self._arrow_button_color
        self.box.set_bg_color(bg)
        try:
            self.box.arrow_bg_color = arrow_bg
            self.box.update()
        except Exception:
            pass

    def _set_trigger_hovered(self, hovered):
        hovered = bool(hovered)
        if self._trigger_hovered == hovered:
            return
        self._trigger_hovered = hovered
        if self.arrow_type == "large":
            self._apply_arrow_color()
        if self.arrow_type == "small":
            self._small_arrow_hovered = hovered
            self._set_small_arrow_offset(self._small_arrow_shift_px if hovered else 0)
        self._apply_trigger_background()

    def select(self, button, text):
        self._apply_selection(text, active_button=button)
        try:
            if callable(self._on_select_cb):
                self._on_select_cb(text)
        except Exception:
            pass
        try:
            self._close_dropdown()
        except Exception:
            self.dropdown.hide()

    def set_value(self, text):
        self._apply_selection(text, active_button=None)
        try:
            if callable(self._on_select_cb):
                self._on_select_cb(text)
        except Exception:
            pass

    def _apply_selection(self, text, active_button=None):
        self.selected = text
        theme = self._theme or {}
        accent = theme.get("accent_color", "#5BF69F")
        text_color = theme.get("text_color", "#FFFFFF")

        for btn in self.option_buttons:
            is_active = (btn is active_button) or (btn.text() == text)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        color: %(text_color)s;
                        background-color: %(accent)s;
                        border: none;
                        text-align: left;
                        padding-left: 8px;
                        border-radius: 15px;
                    }
                """ % {"accent": accent, "text_color": text_color})
            else:
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

        self.label.setText(text)
        self.label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
        """)

    def value(self):
        return self.selected

    def _tint_pixmap(self, pix, color):
        if pix is None or pix.isNull():
            return pix
        tinted = QPixmap(pix.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pix)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color))
        painter.end()
        return tinted

    def _apply_arrow_color(self):
        try:
            self.box.set_arrow_color(self._arrow_color)
            if self._arrow_source_pix is None:
                return
            if self._use_custom_arrow_icon:
                self._orig_arrow_pix = self._arrow_source_pix
            else:
                self._orig_arrow_pix = self._tint_pixmap(self._arrow_source_pix, self._arrow_color)
            self.box.set_arrow_icon(self._orig_arrow_pix)
            if self._enable_flip_animation:
                self._update_arrow_angle(0 if not self.arrow_open else 180)
            elif self.arrow_type == "small":
                self._set_arrow_angle(180 if self.arrow_open else 0)
            else:
                icon_dims = self._effective_icon_dimensions()
                self.box.set_arrow_style(size=icon_dims, angle=0, offset_y=0)
        except Exception:
            pass

    def _effective_icon_size(self):
        if self.arrow_type == "small":
            return max(1, int(self._icon_compact_size))
        size = int(self._icon_current_size) + int(self._large_arrow_extra_px)
        if self._trigger_hovered:
            size = int(round(size * self._large_hover_scale))
        return max(1, size)

    def _effective_icon_dimensions(self):
        if not self._use_custom_arrow_icon:
            base_w = max(1, int(self._vector_arrow_base_w))
            base_h = max(1, int(self._vector_arrow_base_h))
            if self.arrow_type == "small":
                compact_ratio = float(self._icon_compact_size) / float(max(1, self._icon_base_size))
                base_w = max(1, int(round(base_w * compact_ratio)))
                base_h = max(1, int(round(base_h * compact_ratio)))
            elif self._trigger_hovered:
                base_w = max(1, int(round(base_w * self._large_hover_scale)))
                base_h = max(1, int(round(base_h * self._large_hover_scale)))
            return (base_w, base_h)

        size = self._effective_icon_size()
        if self._orig_arrow_pix is None or self._orig_arrow_pix.isNull():
            return (size, size)
        src_w = max(1, int(self._orig_arrow_pix.width()))
        src_h = max(1, int(self._orig_arrow_pix.height()))
        if src_w >= src_h:
            scale = float(size) / float(src_w)
        else:
            scale = float(size) / float(src_h)
        dst_w = max(1, int(round(src_w * scale)))
        dst_h = max(1, int(round(src_h * scale)))
        return (dst_w, dst_h)

    def set_colors(self, dropdown_color=None, arrow_button_color=None, arrow_color=None, box_color=None):
        try:
            if box_color is not None:
                self._box_color = box_color
            if dropdown_color is not None:
                self._dropdown_color = dropdown_color
                self.dropdown.set_bg_color(self._dropdown_color)
            if arrow_button_color is not None:
                self._arrow_button_color = arrow_button_color
            if arrow_color is not None:
                self._arrow_color = arrow_color
                self._apply_arrow_color()
            self._apply_trigger_background()
        except Exception:
            pass

    def _set_arrow_angle(self, angle):
        try:
            if not self._orig_arrow_pix:
                return
            self._arrow_angle = float(angle)
            if self.arrow_type == "small":
                icon_dims = self._effective_icon_dimensions()
                offset = int(round(self._small_arrow_offset_y))
            else:
                icon_dims = self._effective_icon_dimensions()
                offset = 0
            self.box.set_arrow_style(size=icon_dims, angle=self._arrow_angle, offset_y=offset)
        except Exception:
            pass

    def _update_arrow_angle(self, angle):
        try:
            self._set_arrow_angle(angle)
        except Exception:
            pass

    def _set_small_arrow_offset(self, offset_y):
        try:
            target = float(offset_y)
            if self._small_offset_anim is not None:
                self._small_offset_anim.stop()
                self._small_offset_anim.setStartValue(float(self._small_arrow_offset_y))
                self._small_offset_anim.setEndValue(target)
                self._small_offset_anim.start()
            else:
                self._apply_small_arrow_offset(target)
        except Exception:
            pass

    def _apply_small_arrow_offset(self, offset_y):
        self._small_arrow_offset_y = float(offset_y)
        try:
            angle = 180.0 if self.arrow_open else 0.0
            self._arrow_angle = angle
            icon_dims = self._effective_icon_dimensions()
            self.box.set_arrow_style(
                size=icon_dims,
                angle=self._arrow_angle,
                offset_y=int(round(self._small_arrow_offset_y))
            )
        except Exception:
            pass

    def set_icon_compact(self, compact: bool):
        try:
            if self.arrow_type == "small":
                self._icon_current_size = self._icon_compact_size
            else:
                self._icon_current_size = self._icon_compact_size if compact else self._icon_base_size
            if self._orig_arrow_pix is not None:
                if self._enable_flip_animation:
                    self._update_arrow_angle(0 if not self.arrow_open else 180)
                elif self.arrow_type == "small":
                    self._set_arrow_angle(180 if self.arrow_open else 0)
                else:
                    icon_dims = self._effective_icon_dimensions()
                    self.box.set_arrow_style(size=icon_dims, angle=0, offset_y=0)
        except Exception:
            pass

    def update_accent_colors(self):
        try:
            self._theme = get_theme()
            if self.selected:
                self._apply_selection(self.selected, active_button=None)
        except Exception:
            pass


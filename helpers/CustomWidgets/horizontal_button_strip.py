from ._shared import *
from .arrow_horizontal_scrollbar import ArrowHorizontalScrollBar
from .hover_scale_button import HoverScaleButton
from PySide6.QtGui import QFontMetrics


class HorizontalButtonStrip(QWidget):
    """A rounded pill-strip that shows a row of HoverScaleButtons.

    - When all buttons fit: centered horizontally + vertically, no scrollbar.
    - When content overflows: left-aligned, scrollable via custom hbar.

    Scrolling works by shifting a clip container's x offset — no QScrollArea,
    so HoverScaleButton's geometry animation works correctly.

    Usage
    -----
        strip = HorizontalButtonStrip(parent=some_frame)
        strip.setGeometry(12, 40, 383, 52)

        strip.set_items(
            items=["alpha", "beta", "gamma"],
            on_click=lambda name: print(name),
            selected="alpha",
            accent_color="#5BF69F",
            hover_color="#48C47F",
            text_color="#FFFFFF",
        )

        strip.set_selected("beta")
        print(strip.selected)
    """

    item_clicked = Signal(str)

    def __init__(
        self,
        parent=None,
        bg_color="#3e3e3e",
        border_color="#4d4d4d",
        border_radius=8,
        button_height=30,
        button_radius=12,
        button_font_size=12,
        button_min_width=80,
        button_padding=28,
        spacing=8,
        bar_height=6,
        bar_arrow_area=12,
        bar_min_handle=22,
        arrow_width_factor=1.3,
        arrow_corner_radius=1.5,
    ):
        super().__init__(parent)

        self._bg_color        = bg_color
        self._border_color    = border_color
        self._border_radius   = border_radius
        self._button_height   = int(button_height)
        self._button_radius   = int(button_radius)
        self._button_font_size = int(button_font_size)
        self._button_min_width = int(button_min_width)
        self._button_padding  = int(button_padding)
        self._spacing         = int(spacing)
        self._bar_height      = int(bar_height)
        self._bar_arrow_area  = int(bar_arrow_area)
        self._bar_min_handle  = int(bar_min_handle)
        self._arrow_width_factor   = float(arrow_width_factor)
        self._arrow_corner_radius  = float(arrow_corner_radius)

        self._accent = "#5BF69F"
        self._hover  = "#48C47F"
        self._text   = "#FFFFFF"

        self.selected      = None
        self._buttons: dict[str, HoverScaleButton] = {}
        self._widths: dict[str, int] = {}
        self._on_click_cb  = None
        self._content_width = 0   # natural total width of all buttons + spacing
        self._empty_label  = None
        self._scroll_offset = 0   # current horizontal scroll in pixels

        self._build()

    # ─────────────────────────── build ───────────────────────────

    def _build(self):
        # Outer rounded frame — clips children via stylesheet border-radius
        self._frame = QFrame(self)
        self._frame.setAttribute(Qt.WA_StyledBackground, True)
        self._frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self._bg_color};
                border-radius: {self._border_radius}px;
                border: 1px solid {self._border_color};
            }}
        """)

        # Clip widget — sits inside the frame, masks overflowing buttons
        # Buttons are direct children of this widget so their geometry
        # animation (HoverScaleButton) works without interference.
        self._clip = QWidget(self._frame)
        self._clip.setStyleSheet("background: transparent; border: none;")

        # hbar lives inside the frame, below the clip area
        self._hbar = ArrowHorizontalScrollBar(
            parent=self._frame,
            arrow_area_width=self._bar_arrow_area,
            bar_height=self._bar_height,
            margin=2,
            min_handle_width=self._bar_min_handle,
            arrow_width_factor=self._arrow_width_factor,
            arrow_corner_radius=self._arrow_corner_radius,
        )
        self._hbar.setStyleSheet("QScrollBar { background: transparent; border: none; }")
        self._hbar.valueChanged.connect(self._on_scroll)
        self._hbar.hide()

    # ─────────────────────────── layout ───────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_layout()

    def _sync_layout(self):
        w, h = self.width(), self.height()
        self._frame.setGeometry(0, 0, w, h)

        inner_w = max(1, w - 2)
        inner_h = max(1, h - 2)

        needs_scroll = self._content_width > inner_w

        if needs_scroll:
            bar_h   = self._bar_height + 4
            clip_h  = max(1, inner_h - bar_h)
            self._clip.setGeometry(1, 1, inner_w, clip_h)
            self._hbar.setGeometry(1, 1 + clip_h, inner_w, bar_h)
            self._hbar.setRange(0, self._content_width - inner_w)
            self._hbar.setPageStep(inner_w)
            self._hbar.show()
            self._place_buttons(clip_h, inner_w, center=False)
        else:
            self._scroll_offset = 0
            self._clip.setGeometry(1, 1, inner_w, inner_h)
            self._hbar.hide()
            self._place_buttons(inner_h, inner_w, center=True)

    def _place_buttons(self, clip_h: int, clip_w: int, center: bool):
        btn_h = self._button_height
        y = max(0, (clip_h - btn_h) // 2)

        if center:
            x_start = max(0, (clip_w - self._content_width) // 2)
        else:
            x_start = 4 - self._scroll_offset

        x = x_start
        for label, btn in self._buttons.items():
            bw = self._widths.get(label, self._button_min_width)
            r = QRect(x, y, bw, btn_h)
            # Call QWidget.setGeometry directly to bypass HoverScaleButton's
            # override which would clobber _base_geometry during animation frames
            QWidget.setGeometry(btn, r)
            btn._base_geometry = QRect(r)
            x += bw + self._spacing

        if self._empty_label is not None:
            lw, lh = 180, 22
            lx = max(0, (clip_w - lw) // 2) if center else 4
            ly = max(0, (clip_h - lh) // 2)
            self._empty_label.setGeometry(lx, ly, lw, lh)

    def _on_scroll(self, value: int):
        self._scroll_offset = value
        # recompute button positions for the new offset
        clip_geom = self._clip.geometry()
        self._place_buttons(clip_geom.height(), clip_geom.width(), center=False)

    # ─────────────────────────── public API ───────────────────────────

    def set_items(
        self,
        items: list[str],
        on_click=None,
        selected=None,
        accent_color: str = None,
        hover_color: str = None,
        text_color: str = None,
    ):
        if accent_color:
            self._accent = accent_color
        if hover_color:
            self._hover = hover_color
        if text_color:
            self._text = text_color

        self.selected     = selected
        self._on_click_cb = on_click

        for btn in self._buttons.values():
            btn.deleteLater()
        self._buttons.clear()
        self._widths.clear()

        if self._empty_label is not None:
            self._empty_label.deleteLater()
            self._empty_label = None

        self._scroll_offset = 0

        font = QFont()
        font.setPointSize(self._button_font_size)
        fm = QFontMetrics(font)

        if not items:
            self._content_width = 0
            lbl = QLabel("None", self._clip)
            lbl.setFixedSize(180, 22)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #9a9a9a; background: transparent; border: none;")
            lbl.show()
            self._empty_label = lbl
        else:
            total_w = 0
            for label in items:
                bw = max(self._button_min_width,
                         fm.horizontalAdvance(label) + self._button_padding)
                btn = HoverScaleButton(label, self._clip, border_radius=self._button_radius)
                btn.setFixedSize(bw, self._button_height)
                btn.setFont(font)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked=False, lbl=label: self._handle_click(lbl))
                btn.show()
                self._buttons[label] = btn
                self._widths[label] = bw
                total_w += bw
            total_w += max(0, (len(items) - 1) * self._spacing)
            self._content_width = total_w

        self._sync_layout()
        self._apply_button_styles()

    def set_selected(self, label: str | None):
        self.selected = label
        self._apply_button_styles()

    def update_theme(self, accent_color=None, hover_color=None, text_color=None):
        if accent_color:
            self._accent = accent_color
        if hover_color:
            self._hover = hover_color
        if text_color:
            self._text = text_color
        self._apply_button_styles()


    # ─────────────────────────── scroll ───────────────────────────

    def wheelEvent(self, event):
        """Forward both horizontal and vertical wheel/touchpad swipes to the scrollbar."""
        if not self._hbar.isVisible():
            event.ignore()
            return
        # Prefer horizontal delta; fall back to vertical (so a plain scroll wheel
        # on a mouse also scrolls the strip sideways).
        delta_x = event.angleDelta().x()
        delta_y = event.angleDelta().y()
        delta = delta_x if abs(delta_x) >= abs(delta_y) else -delta_y
        # angleDelta is in eighths of a degree; 120 eighths = one notch = 15°
        step = max(1, self._hbar.singleStep())
        scroll_amount = int(delta / 120 * step * 3)
        new_val = max(self._hbar.minimum(),
                      min(self._hbar.maximum(), self._hbar.value() - scroll_amount))
        self._hbar.setValue(new_val)
        event.accept()

    # ─────────────────────────── internals ───────────────────────────

    def _handle_click(self, label: str):
        self.selected = label
        self._apply_button_styles()
        self.item_clicked.emit(label)
        if callable(self._on_click_cb):
            self._on_click_cb(label)

    def _apply_button_styles(self):
        for label, btn in self._buttons.items():
            is_sel = (label == self.selected)
            bg  = self._accent if is_sel else "#4a4a4a"
            hbg = self._hover  if is_sel else "#565656"
            fg  = self._text   if is_sel else "#c0c0c0"
            btn.set_text_color(fg)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    border-radius: {self._button_radius}px;
                    color: {fg};
                    font-size: {self._button_font_size}px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {hbg};
                }}
            """)
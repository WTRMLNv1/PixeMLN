from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton,
    QLineEdit, QApplication
)
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter, QTransform, QLinearGradient, QPen, QBrush, QPainterPath
from PySide6.QtCore import (
    Qt, QTimer, QVariantAnimation, QEasingCurve,
    QSequentialAnimationGroup, QParallelAnimationGroup, QPropertyAnimation,
    QAbstractAnimation, QRectF, QPoint, QRect, QSize, Signal, Property, QEvent
)
from helpers.CustomWidgets import (
    HoverScaleButton, HorizontalButtonStrip,
    SpinnerWidget, TickWidget, apply_widget_shadow, IntFltToggle,
)
from helpers.json_manager import (
    get_current_user,
    get_user_graph_names,
    get_theme,
    add_graph,
    rename_graph,
    delete_graph,
    get_graph_color,
    set_graph_color,
)
import os

# Mirror the color schemes from create_graph_images so we don't import matplotlib here
GRAPH_COLOR_SCHEMES = {
    "green":    {"cmap": ["#0f1f17", "#1f6f4a", "#5BF69F"], "bar": "#5BF69F"},
    "rose":     {"cmap": ["#1f0f14", "#6f2040", "#F6758A"], "bar": "#F6758A"},
    "sky":      {"cmap": ["#0f1520", "#2a4a7f", "#7EB8F6"], "bar": "#7EB8F6"},
    "peach":    {"cmap": ["#1f1508", "#7f4e1a", "#F6B87E"], "bar": "#F6B87E"},
    "lavender": {"cmap": ["#130f1f", "#4a2a7f", "#B47EF6"], "bar": "#B47EF6"},
    "arctic":   {"cmap": ["#0a1a1f", "#1a6070", "#6EE8E0"], "bar": "#6EE8E0"},
}


class HeatmapBubbleSwatch(QWidget):
    """Heatmap-bubble color picker button.

    Outer frame: 92×20px, border-radius 8, fill #3e3e3e, border #4d4d4d.
    Inside: 3 × 16×16 squares (heatmap stops, corner-radius 4),
    a 14px vertical divider line (#4d4d4d, RoundCap),
    then 1 × 16×16 square (bar/graph accent color).
    """

    clicked = Signal()

    W = 92
    H = 20
    SQUARE  = 16
    RADIUS  = 4
    DIV_LEN = 14

    def __init__(self, color_key: str, parent=None):
        super().__init__(parent)
        self.color_key = color_key
        self._selected = False
        self._refresh_colors()
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    def _refresh_colors(self):
        scheme = GRAPH_COLOR_SCHEMES.get(self.color_key, GRAPH_COLOR_SCHEMES["green"])
        self._stops = scheme["cmap"]   # 3 hex strings (dark → mid → bright)
        self._bar   = scheme["bar"]    # accent/graph line color

    def set_color_key(self, key: str):
        self.color_key = key
        self._refresh_colors()
        self.update()

    def set_selected(self, sel: bool):
        self._selected = sel
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.W, self.H
        sq = self.SQUARE

        # ── outer frame ──
        outer = QRectF(0.5, 0.5, w - 1, h - 1)
        painter.setPen(QPen(QColor("#4d4d4d"), 1))
        painter.setBrush(QColor("#3e3e3e"))
        painter.drawRoundedRect(outer, 8, 8)

        # ── layout: 6px left pad, 4px gaps between all objects, 6px right ──
        # Objects: sq0 | 4px | sq1 | 4px | sq2 | 4px | divider | 4px | sq3 | 6px right
        pad_l = 6
        gap   = 4
        y = (h - sq) // 2   # vertically centred

        xs = [pad_l + i * (sq + gap) for i in range(3)]   # 3 heatmap squares

        # divider x: after sq2 + gap
        div_x = xs[2] + sq + gap
        # bar square: after divider (1px wide) + gap
        bar_x = div_x + 1 + gap

        # ── 3 heatmap squares ──
        for i, stop in enumerate(self._stops):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(stop))
            painter.drawRoundedRect(QRectF(xs[i], y, sq, sq), self.RADIUS, self.RADIUS)

        # ── vertical divider ──
        pen = QPen(QColor("#4d4d4d"), 1)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        cy = h / 2
        painter.drawLine(
            QPoint(int(div_x), int(cy - self.DIV_LEN / 2)),
            QPoint(int(div_x), int(cy + self.DIV_LEN / 2)),
        )

        # ── bar/accent square ──
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._bar))
        painter.drawRoundedRect(QRectF(bar_x, y, sq, sq), self.RADIUS, self.RADIUS)

        # ── selection ring ──
        if self._selected:
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(outer, 8, 8)

        painter.end()


class ColorPickerPopup(QFrame):
    """A small floating popup showing all gradient swatches."""

    def __init__(self, parent, on_select):
        super().__init__(parent)
        self._on_select = on_select
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #555555;
                border-radius: 14px;
            }
        """)

        # layout: 2 columns × 3 rows of swatches
        keys = list(GRAPH_COLOR_SCHEMES.keys())
        cols, pad, gap_x, gap_y = 2, 10, 8, 8
        sw_w, sw_h = HeatmapBubbleSwatch.W, HeatmapBubbleSwatch.H
        rows = (len(keys) + cols - 1) // cols
        total_w = pad * 2 + cols * sw_w + (cols - 1) * gap_x
        total_h = pad * 2 + rows * sw_h + (rows - 1) * gap_y
        self.setFixedSize(total_w, total_h)

        self._swatch_buttons = {}
        for i, key in enumerate(keys):
            row, col = divmod(i, cols)
            x = pad + col * (sw_w + gap_x)
            y = pad + row * (sw_h + gap_y)
            btn = HeatmapBubbleSwatch(key, self)
            btn.move(x, y)
            btn.clicked.connect(lambda k=key: self._pick(k))
            self._swatch_buttons[key] = btn

        self.hide()

    def show_near(self, anchor_widget, current_color):
        # position popup above the anchor widget
        anchor_pos = anchor_widget.mapTo(self.parent(), anchor_widget.pos() * 0)
        anchor_global = anchor_widget.mapToParent(anchor_widget.rect().topLeft())
        x = anchor_global.x()
        y = anchor_global.y() - self.height() - 6
        # clamp to parent bounds
        parent_w = self.parent().width()
        if x + self.width() > parent_w:
            x = parent_w - self.width() - 4
        self.move(x, y)
        for k, b in self._swatch_buttons.items():
            b.set_selected(k == current_color)
        self.raise_()
        self.show()

    def _pick(self, key):
        self.hide()
        if self._on_select:
            self._on_select(key)


class MorphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._radius = 14.0
        self._color = QColor("#5BF69F")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def _set_radius(self, value):
        try:
            self._radius = float(value)
        except Exception:
            return
        self.update()

    def _get_radius(self):
        return float(self._radius)

    def _set_color(self, value):
        c = value if isinstance(value, QColor) else QColor(value)
        if not c.isValid():
            return
        self._color = c
        self.update()

    def _get_color(self):
        return QColor(self._color)

    radius = Property(float, _get_radius, _set_radius)
    color = Property(QColor, _get_color, _set_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)
        painter.end()


class Graphs(QWidget):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self._setup_done = False
        self.accent_buttons = []

        # state
        self.current_user = None
        self.graphs = []
        self.selected_graph = None
        self._create_color = "green"   # chosen color for the next graph creation
        self._edit_color = None         # color chosen in edit/rename modal
        # sequence counter used by background image rebuilds
        self._load_seq = 0

        # spinner / tick refs
        self._spinner_anim = None
        self._tick_anim = None

        # arrow-button animation data (from account.py pattern)
        self._arrow_source_pix = None
        self._action_button_content = {}
        self._arrow_hover_shift_px = 4

        # morph animation for edit graph button
        self._edit_graph_morph = None
        self._edit_graph_morph_group = None

    # ─────────────────────────── setup ───────────────────────────

    def run(self):
        if self._setup_done:
            return
        self._setup_done = True

        self.setFixedSize(640, 550)

        # ── main frame ──
        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 640, 550)
        self.main_frame.setStyleSheet(
            "background-color: #2b2b2b; border-radius: 20px;"
        )
        apply_widget_shadow(self.main_frame, radius=20)

        # ── title ──
        title = QLabel("Graphs", self.main_frame)
        tf = QFont()
        tf.setPointSize(35)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet("color: #FFFFFF; border: none;")
        title.setGeometry(0, 16, 640, 55)
        title.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        # ── divider ──
        divider = QFrame(self.main_frame)
        divider.setStyleSheet("background-color: #5a5a5a;")
        divider.setFixedSize(300, 1)
        divider.move((640 - 300) // 2, 70)

        # ── current user box (standalone, like account.py) ──
        self.current_user_box = QFrame(self.main_frame)
        self.current_user_box.setGeometry(191, 98, 260, 86)
        self.current_user_box.setStyleSheet("""
            QFrame {
                background-color: #2e3a34;
                border: 1px solid #3b5247;
                border-radius: 20px;
            }
        """)

        current_user_title = QLabel("current user", self.current_user_box)
        ctf = QFont()
        ctf.setPointSize(15)
        current_user_title.setFont(ctf)
        current_user_title.setGeometry(0, 8, 260, 26)
        current_user_title.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        current_user_title.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        self.current_user_value = QLabel("", self.current_user_box)
        cvf = QFont()
        cvf.setPointSize(15)
        cvf.setBold(True)
        self.current_user_value.setFont(cvf)
        self.current_user_value.setGeometry(0, 33, 260, 44)
        self.current_user_value.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.current_user_value.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        # ── form panel (matches account.py geometry: y=220, h=286) ──
        self.form_frame = QFrame(self.main_frame)
        self.form_frame.setGeometry(45, 220, 551, 286)
        self.form_frame.setStyleSheet(
            "background-color: #353535; border-radius: 20px;"
            " border: 1px solid rgba(96,96,96,0.9);"
        )

        label_font = QFont()
        label_font.setPointSize(15)
        label_font.setBold(True)

        small_font = QFont()
        small_font.setPointSize(12)

        ef = QFont()
        ef.setPointSize(10)

        # ── "Your graphs:" label ──
        graphs_label = QLabel("Your graphs:", self.form_frame)
        graphs_label.setGeometry(16, 10, 280, 28)
        graphs_label.setFont(label_font)
        graphs_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        # ── selected graph subtitle ──
        self.selected_graph_label = QLabel("none", self.form_frame)
        self.selected_graph_label.setGeometry(170, 15, 365, 20)
        self.selected_graph_label.setFont(small_font)
        self.selected_graph_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.selected_graph_label.setStyleSheet(
            "color: #7f7f7f; background: transparent; border: none;"
        )

        # ── graph scroll strip (inside a container frame, Figma: Frame 2610471) ──
        self.graph_strip = HorizontalButtonStrip(
            parent=self.form_frame,
            border_radius=8,
            button_height=30,
            button_radius=14,
            button_font_size=14,
            button_min_width=80,
            button_padding=28,
            spacing=8,
            bar_height=8,
            bar_arrow_area=12,
            bar_min_handle=22,
        )
        self.graph_strip.setGeometry(16, 38, 451, 52)

        # spinner + tick next to strip
        accent = get_theme().get("accent_color", "#5BF69F")
        self.graph_spinner = SpinnerWidget(size=14, thickness=2, color=accent, parent=self.form_frame)
        self.graph_tick = TickWidget(size=14, thickness=2, color=accent, parent=self.form_frame)
        self._position_status_widgets()
        self._set_status("idle")

        # ── separator ──
        sep1 = QFrame(self.form_frame)
        sep1.setStyleSheet("background-color: #505050; border: none;")
        sep1.setFixedSize(519, 1)
        sep1.move(16, 112)

        # ── "Create a graph:" label ──
        create_label = QLabel("Create a graph:", self.form_frame)
        create_label.setGeometry(16, 121, 220, 26)
        create_label.setFont(label_font)
        create_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        # ── graph name input ──
        self.create_name_input = QLineEdit(self.form_frame)
        self.create_name_input.setGeometry(16, 152, 328, 22)
        self.create_name_input.setPlaceholderText("Graph name")
        self._style_input(self.create_name_input)
        self.create_name_input.textChanged.connect(self._on_create_input_changed)
        self.create_name_input.returnPressed.connect(self._submit_create)

        # ── Type label + int/flt toggle ──
        type_label = QLabel("Type:", self.form_frame)
        type_label.setGeometry(16, 179, 40, 18)
        type_label.setFont(ef)
        type_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        theme = get_theme()
        self.type_toggle = IntFltToggle(
            parent=self.form_frame,
            on_change=self._on_type_changed,
            accent_color=theme.get("accent_color", "#5BF69F"),
            hover_color=theme.get("hover_color", "#48C47F"),
            text_color=theme.get("text_color", "#FFFFFF"),
            initial_value="int",
        )
        self.type_toggle.move(62, 178)

        # ── Color label + swatch button (create) ──
        color_label_create = QLabel("Color:", self.form_frame)
        color_label_create.setGeometry(200, 179, 44, 18)
        color_label_create.setFont(ef)
        color_label_create.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )
        self.create_color_btn = HeatmapBubbleSwatch(self._create_color, self.form_frame)
        self.create_color_btn.move(248, 179)
        self.create_color_btn.clicked.connect(self._toggle_create_color_popup)
        # popup (created lazily and parented to main_frame so it floats above form)
        self._create_color_popup = ColorPickerPopup(self.main_frame, self._on_create_color_picked)

        # Create button
        self.create_btn = HoverScaleButton("Create", self.form_frame, border_radius=12)
        self.create_btn.setGeometry(402, 149, 77, 28)
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.setFont(small_font)
        self.accent_buttons.append(self.create_btn)
        self.create_btn.clicked.connect(self._submit_create)

        # create error
        self.create_error = QLabel("", self.form_frame)
        self.create_error.setGeometry(16, 200, 519, 16)
        self.create_error.setFont(ef)
        self.create_error.setStyleSheet(
            "color: #ff7e7e; background: transparent; border: none;"
        )
        self.create_error.hide()

        # ── separator ──
        sep2 = QFrame(self.form_frame)
        sep2.setStyleSheet("background-color: #505050; border: none;")
        sep2.setFixedSize(519, 1)
        sep2.move(16, 220)

        # ── "Edit a graph:" label ──
        edit_label = QLabel("Edit a graph:", self.form_frame)
        edit_label.setGeometry(16, 229, 220, 26)
        edit_label.setFont(label_font)
        edit_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        # ── edit graph button (accent pill, with animated arrow) ──
        self.edit_graph_btn = QPushButton("edit graph", self.form_frame)
        self.edit_graph_btn.setGeometry(16, 257, 110, 22)
        self.edit_graph_btn.setCursor(Qt.PointingHandCursor)
        self.accent_buttons.append(self.edit_graph_btn)
        self._prepare_arrow_source()
        self._setup_action_button_arrow(self.edit_graph_btn)

        # edit error
        self.edit_error = QLabel("", self.form_frame)
        self.edit_error.setGeometry(135, 258, 400, 16)
        self.edit_error.setFont(ef)
        self.edit_error.setStyleSheet(
            "color: #ff7e7e; background: transparent; border: none;"
        )
        self.edit_error.hide()

        # ── modals ──
        self._build_rename_modal()
        self._build_delete_modal()

        for w in (self, self.main_frame, self.form_frame, self.rename_overlay):
            try:
                w.installEventFilter(self)
            except Exception:
                pass
        app = QApplication.instance()
        if app is not None:
            try:
                app.installEventFilter(self)
            except Exception:
                pass

        # ── load data ──
        self._load_data()
        self._build_graph_buttons()
        self.update_accent_colors()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            self._hide_color_popup_on_outside_click(
                popup=getattr(self, "_create_color_popup", None),
                anchor=self.create_color_btn,
                global_pos=event.globalPos(),
            )
            self._hide_color_popup_on_outside_click(
                popup=getattr(self, "_edit_color_popup", None),
                anchor=getattr(self, "edit_color_btn", None),
                global_pos=event.globalPos(),
            )
        return super().eventFilter(obj, event)

    def _hide_color_popup_on_outside_click(self, popup, anchor, global_pos):
        if popup is None or anchor is None or not popup.isVisible():
            return
        try:
            popup_local = popup.mapFromGlobal(global_pos)
            if popup.rect().contains(popup_local):
                return
            anchor_local = anchor.mapFromGlobal(global_pos)
            if anchor.rect().contains(anchor_local):
                return
            popup.hide()
        except Exception:
            pass

    # ─────────────────────────── data ───────────────────────────

    def _load_data(self):
        try:
            self.current_user = get_current_user()
        except Exception:
            self.current_user = None
        try:
            self.graphs = get_user_graph_names(self.current_user) if self.current_user else []
        except Exception:
            self.graphs = []

        if not getattr(self, "_setup_done", False):
            return
        self.current_user_value.setText(self.current_user or "unknown")

    # ─────────────────────────── graph buttons ───────────────────────────

    def _build_graph_buttons(self):
        strip = getattr(self, "graph_strip", None)
        if strip is None:
            return
        safe_graphs = [str(g).strip() for g in (self.graphs or []) if str(g).strip()]
        theme = get_theme()
        strip.set_items(
            items=safe_graphs,
            on_click=self._on_graph_selected,
            selected=self.selected_graph,
            accent_color=theme.get("accent_color", "#5BF69F"),
            hover_color=theme.get("hover_color", "#48C47F"),
            text_color=theme.get("text_color", "#FFFFFF"),
        )
        self._refresh_graph_button_styles()

    def _on_graph_selected(self, graph_name):
        self.selected_graph = graph_name
        self._refresh_graph_button_styles()
        self._refresh_selected_label()
        self._set_edit_error("")

    def _refresh_graph_button_styles(self):
        theme = get_theme()
        strip = getattr(self, "graph_strip", None)
        if strip is None:
            return
        strip.update_theme(
            accent_color=theme.get("accent_color", "#5BF69F"),
            hover_color=theme.get("hover_color", "#48C47F"),
            text_color=theme.get("text_color", "#FFFFFF"),
        )
        strip.set_selected(self.selected_graph)

    def _refresh_selected_label(self):
        if not self.selected_graph:
            self.selected_graph_label.setText("none")
            self.selected_graph_label.setStyleSheet(
                "color: #7f7f7f; background: transparent; border: none;"
            )
        else:
            self.selected_graph_label.setText(self.selected_graph)
            self.selected_graph_label.setStyleSheet(
                "color: #9b9b9b; background: transparent; border: none;"
            )

    # ─────────────────────────── type toggle ───────────────────────────

    def _on_type_changed(self, value):
        pass  # value is 'int' or 'flt'

    @property
    def _selected_type(self):
        toggle = getattr(self, "type_toggle", None)
        return toggle.value() if toggle else "int"

    # ─────────────────────────── create ───────────────────────────

    def _on_create_input_changed(self, text):
        if self.create_error.isVisible():
            self.create_error.hide()

    def _set_create_error(self, msg):
        if msg:
            self.create_error.setText(msg)
            self.create_error.show()
        else:
            self.create_error.hide()

    def _submit_create(self):
        name = self.create_name_input.text().strip()
        if not name:
            self._set_create_error("Graph name cannot be empty")
            return
        if not self.current_user:
            self._set_create_error("No current user found")
            return
        if name in self.graphs:
            self._set_create_error("A graph with that name already exists")
            return

        try:
            add_graph(self.current_user, name, self._selected_type, self._create_color)
        except Exception as e:
            self._set_create_error(f"Error: {e}")
            return

        self.create_name_input.clear()
        self._set_create_error("")
        self._reload_graphs(select=name)
        self._set_status("done")

    # ─────────────────────────── rename modal ───────────────────────────

    def _build_rename_modal(self):
        self.rename_overlay = QFrame(self.main_frame)
        self.rename_overlay.setGeometry(0, 0, 640, 550)
        self.rename_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.rename_overlay.setStyleSheet("QFrame { background-color: rgba(0,0,0,165); }")
        self.rename_overlay.hide()

        modal = QFrame(self.rename_overlay)
        modal.setGeometry(145, 163, 350, 224)
        modal.setAttribute(Qt.WA_StyledBackground, True)
        modal.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border: 1px solid #555555;
                border-radius: 16px;
            }
        """)
        self.rename_modal = modal

        title = QLabel("Edit graph", modal)
        tf = QFont()
        tf.setPointSize(18)
        tf.setBold(True)
        title.setFont(tf)
        title.setGeometry(0, 14, 350, 28)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        inp_label = QLabel("Name", modal)
        lf = QFont()
        lf.setPointSize(11)
        inp_label.setFont(lf)
        inp_label.setGeometry(24, 54, 100, 18)
        inp_label.setStyleSheet("color: #cfcfcf; background: transparent; border: none;")

        self.rename_input = QLineEdit(modal)
        self.rename_input.setGeometry(24, 76, 302, 30)
        self.rename_input.setPlaceholderText("Enter new graph name")
        self._style_input(self.rename_input)
        self.rename_input.returnPressed.connect(self._submit_rename)
        self.rename_input.textChanged.connect(
            lambda: self.rename_error.hide() if self.rename_error.isVisible() else None
        )

        self.rename_error = QLabel("", modal)
        ef = QFont()
        ef.setPointSize(10)
        self.rename_error.setFont(ef)
        self.rename_error.setGeometry(24, 110, 302, 18)
        self.rename_error.setStyleSheet("color: #ff7e7e; background: transparent; border: none;")
        self.rename_error.hide()

        # ── Color row ──
        color_lbl = QLabel("Color:", modal)
        color_lbl.setFont(ef)
        color_lbl.setGeometry(24, 134, 40, 20)
        color_lbl.setStyleSheet("color: #cfcfcf; background: transparent; border: none;")

        self.edit_color_btn = HeatmapBubbleSwatch("green", modal)
        self.edit_color_btn.move(70, 134)
        self.edit_color_btn.clicked.connect(self._toggle_edit_color_popup)

        # popup parented to rename_overlay so it floats above the modal
        self._edit_color_popup = ColorPickerPopup(self.rename_overlay, self._on_edit_color_picked)

        cancel_btn = QPushButton("Cancel", modal)
        cancel_btn.setGeometry(24, 172, 140, 32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #4b4b4b;
                color: #FFFFFF;
                border: 1px solid #616161;
                border-radius: 10px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #595959; }
        """)
        cancel_btn.clicked.connect(self._close_rename_modal)

        self.rename_confirm_btn = QPushButton("Save", modal)
        self.rename_confirm_btn.setGeometry(186, 172, 140, 32)
        self.rename_confirm_btn.setCursor(Qt.PointingHandCursor)
        self.rename_confirm_btn.clicked.connect(self._submit_rename)
        self.accent_buttons.append(self.rename_confirm_btn)

    def _open_rename_modal(self):
        if not self.selected_graph:
            self._set_edit_error("Select a graph first")
            return
        self._set_edit_error("")
        self.rename_input.setText(self.selected_graph or "")
        self.rename_input.selectAll()
        self.rename_input.setPlaceholderText("Graph name")
        self.rename_error.hide()
        # load current color for this graph
        try:
            self._edit_color = get_graph_color(self.current_user, self.selected_graph)
        except Exception:
            self._edit_color = "green"
        self.edit_color_btn.set_color_key(self._edit_color or "green")
        self.rename_overlay.raise_()
        self.rename_overlay.show()
        self.rename_input.setFocus()

    def _submit_rename(self):
        new_name = self.rename_input.text().strip()
        if not new_name:
            self.rename_error.setText("Name cannot be empty")
            self.rename_error.show()
            return
        if new_name == self.selected_graph:
            # name unchanged — but color may have changed; save color and rebuild image
            old_color = get_graph_color(self.current_user, self.selected_graph)
            if self._edit_color and self._edit_color != old_color:
                try:
                    set_graph_color(self.current_user, self.selected_graph, self._edit_color)
                except Exception:
                    pass
                self._close_rename_modal()
                self._set_status("loading")
                self._rebuild_display_image_for(self.selected_graph)
            else:
                self._close_rename_modal()
                self._set_status("done")
            return
        if new_name in self.graphs:
            self.rename_error.setText("A graph with that name already exists")
            self.rename_error.show()
            return

        old_name = self.selected_graph
        try:
            ok, msg = rename_graph(self.current_user, old_name, new_name)
        except Exception as e:
            self.rename_error.setText(str(e))
            self.rename_error.show()
            return

        if not ok:
            self.rename_error.setText(msg)
            self.rename_error.show()
            return

        # save color (use new name since rename already happened)
        if self._edit_color:
            try:
                set_graph_color(self.current_user, new_name, self._edit_color)
            except Exception:
                pass

        self._close_rename_modal()
        self._reload_graphs(select=new_name)
        self._set_status("done")

    # ─────────────────────────── image rebuild helper ───────────────────────────

    def _rebuild_display_image_for(self, graph_name):
        """Regenerate the cached heatmap/histogram for graph_name, then refresh the homepage."""
        import threading
        from functions.create_graph_images import create_heatmap, create_histogram
        from helpers.json_manager import get_current_graph
        from PySide6.QtCore import QTimer

        self._load_seq += 1
        seq_id = self._load_seq

        def _worker():
            try:
                current = get_current_graph() or {}
                display_type = (current.get("type") or "").strip().lower()
                if display_type == "histogram":
                    create_histogram(self.current_user, graph_name)
                else:
                    create_heatmap(self.current_user, graph_name)
            finally:
                def _finish():
                    try:
                        self.ui.home_screen.refresh_info()
                    finally:
                        self._maybe_finish_load(seq_id)
                QTimer.singleShot(0, self, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _maybe_finish_load(self, seq_id):
        """Mark load finished only if seq_id matches latest request."""
        if not hasattr(self, "_load_seq") or seq_id != self._load_seq:
            return
        try:
            self._set_status("done")
        except Exception:
            pass

    # ─────────────────────────── delete modal ───────────────────────────

    def _build_delete_modal(self):
        self.delete_overlay = QFrame(self.main_frame)
        self.delete_overlay.setGeometry(0, 0, 640, 550)
        self.delete_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.delete_overlay.setStyleSheet("QFrame { background-color: rgba(0,0,0,165); }")
        self.delete_overlay.hide()

        modal = QFrame(self.delete_overlay)
        modal.setGeometry(145, 195, 350, 160)
        modal.setAttribute(Qt.WA_StyledBackground, True)
        modal.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border: 1px solid #555555;
                border-radius: 16px;
            }
        """)
        self.delete_modal = modal

        title = QLabel("Delete graph?", modal)
        tf = QFont()
        tf.setPointSize(18)
        tf.setBold(True)
        title.setFont(tf)
        title.setGeometry(0, 14, 350, 28)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")

        self.delete_graph_name_label = QLabel("", modal)
        lf = QFont()
        lf.setPointSize(11)
        self.delete_graph_name_label.setFont(lf)
        self.delete_graph_name_label.setGeometry(0, 50, 350, 20)
        self.delete_graph_name_label.setAlignment(Qt.AlignCenter)
        self.delete_graph_name_label.setStyleSheet(
            "color: #cfcfcf; background: transparent; border: none;"
        )

        self.delete_error = QLabel("", modal)
        ef = QFont()
        ef.setPointSize(10)
        self.delete_error.setFont(ef)
        self.delete_error.setGeometry(24, 78, 302, 18)
        self.delete_error.setStyleSheet("color: #ff7e7e; background: transparent; border: none;")
        self.delete_error.hide()

        cancel_btn = QPushButton("Cancel", modal)
        cancel_btn.setGeometry(24, 110, 140, 32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #4b4b4b;
                color: #FFFFFF;
                border: 1px solid #616161;
                border-radius: 10px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #595959; }
        """)
        cancel_btn.clicked.connect(self._close_delete_modal)

        confirm_btn = QPushButton("Delete", modal)
        confirm_btn.setGeometry(186, 110, 140, 32)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b2020;
                color: #FFFFFF;
                border-radius: 10px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #a02828; }
        """)
        confirm_btn.clicked.connect(self._confirm_delete)

    def _open_delete_modal(self):
        if not self.selected_graph:
            self._set_edit_error("Select a graph first")
            return
        self._set_edit_error("")
        self.delete_graph_name_label.setText(f'"{self.selected_graph}"')
        self.delete_error.hide()
        self.delete_overlay.raise_()
        self.delete_overlay.show()

    def _close_delete_modal(self):
        self.delete_overlay.hide()

    def _confirm_delete(self):
        graph = self.selected_graph
        if not graph:
            self._close_delete_modal()
            return
        try:
            ok, msg = delete_graph(self.current_user, graph)
        except Exception as e:
            self.delete_error.setText(str(e))
            self.delete_error.show()
            return

        if not ok:
            self.delete_error.setText(msg)
            self.delete_error.show()
            return

        self._close_delete_modal()
        self.selected_graph = None
        self._refresh_selected_label()
        self._reload_graphs(select=None)
        self._set_status("done")

    # ─────────────────────────── edit button ───────────────────────────

    def _set_edit_error(self, msg):
        if msg:
            self.edit_error.setText(msg)
            self.edit_error.show()
        else:
            self.edit_error.hide()

    def _on_edit_graph_clicked(self):
        if not self.selected_graph:
            self._set_edit_error("Select a graph first")
            return
        self._set_edit_error("")

        # Stop any previous morph
        if self._edit_graph_morph_group is not None and self._edit_graph_morph_group.state() == QAbstractAnimation.Running:
            self._edit_graph_morph_group.stop()
            self._edit_graph_morph_group = None
        if self._edit_graph_morph is not None:
            self._edit_graph_morph.deleteLater()
            self._edit_graph_morph = None

        btn = self.edit_graph_btn
        start_top_left = btn.mapTo(self.main_frame, QPoint(0, 0))
        start_rect = QRect(start_top_left, btn.size())
        end_rect = QRect(self.rename_modal.mapTo(self.main_frame, QPoint(0, 0)), self.rename_modal.size())

        theme = get_theme()
        start_color = QColor(theme.get("accent_color", "#5BF69F"))
        if not start_color.isValid():
            start_color = QColor("#5BF69F")
        end_color = QColor("#2f2f2f")

        morph = MorphWidget(self.main_frame)
        morph.setGeometry(start_rect)
        morph.radius = 11.0
        morph.color = start_color
        morph.show()
        morph.raise_()
        self._edit_graph_morph = morph

        self.rename_overlay.hide()

        group = QParallelAnimationGroup(self)

        geo_anim = QPropertyAnimation(morph, b"geometry", self)
        geo_anim.setDuration(280)
        geo_anim.setStartValue(start_rect)
        geo_anim.setEndValue(end_rect)
        geo_anim.setEasingCurve(QEasingCurve.InOutCubic)

        radius_anim = QPropertyAnimation(morph, b"radius", self)
        radius_anim.setDuration(280)
        radius_anim.setStartValue(11.0)
        radius_anim.setEndValue(16.0)
        radius_anim.setEasingCurve(QEasingCurve.InOutCubic)

        color_anim = QPropertyAnimation(morph, b"color", self)
        color_anim.setDuration(280)
        color_anim.setStartValue(start_color)
        color_anim.setEndValue(end_color)
        color_anim.setEasingCurve(QEasingCurve.InOutCubic)

        group.addAnimation(geo_anim)
        group.addAnimation(radius_anim)
        group.addAnimation(color_anim)
        group.finished.connect(self._finish_open_rename_modal)
        self._edit_graph_morph_group = group
        group.start()

    def _finish_open_rename_modal(self):
        if self._edit_graph_morph is not None:
            self._edit_graph_morph.deleteLater()
            self._edit_graph_morph = None
        self._edit_graph_morph_group = None
        self._open_rename_modal()

    # ─────────────────────────── color picker ───────────────────────────

    def _toggle_create_color_popup(self):
        popup = self._create_color_popup
        if popup.isVisible():
            popup.hide()
            return
        # position popup relative to main_frame
        btn_pos = self.create_color_btn.mapTo(self.main_frame, self.create_color_btn.rect().topLeft())
        x = btn_pos.x()
        y = btn_pos.y() - popup.height() - 6
        parent_w = self.main_frame.width()
        if x + popup.width() > parent_w:
            x = parent_w - popup.width() - 4
        if y < 0:
            y = btn_pos.y() + self.create_color_btn.height() + 4
        popup.move(x, y)
        for k, b in popup._swatch_buttons.items():
            b.set_selected(k == self._create_color)
        popup.raise_()
        popup.show()

    def _on_create_color_picked(self, key: str):
        self._create_color = key
        self.create_color_btn.set_color_key(key)

    def _toggle_edit_color_popup(self):
        popup = self._edit_color_popup
        if popup.isVisible():
            popup.hide()
            return
        btn_pos = self.edit_color_btn.mapTo(self.rename_overlay, self.edit_color_btn.rect().topLeft())
        x = btn_pos.x()
        y = btn_pos.y() - popup.height() - 6
        parent_w = self.rename_overlay.width()
        if x + popup.width() > parent_w:
            x = parent_w - popup.width() - 4
        if y < 0:
            y = btn_pos.y() + self.edit_color_btn.height() + 4
        popup.move(x, y)
        cur = self._edit_color or "green"
        for k, b in popup._swatch_buttons.items():
            b.set_selected(k == cur)
        popup.raise_()
        popup.show()

    def _on_edit_color_picked(self, key: str):
        self._edit_color = key
        self.edit_color_btn.set_color_key(key)

    def _close_rename_modal(self):
        self._edit_color_popup.hide()
        self.rename_overlay.hide()

    # ─────────────────────────── spinner / tick ───────────────────────────

    def _position_status_widgets(self):
        gf = self.graph_strip.geometry()
        x = gf.x() + gf.width() + 8
        y = gf.y() + (gf.height() - 14) // 2
        self.graph_spinner.move(x, y)
        self.graph_tick.move(x, y)

    def _set_status(self, state):
        if state == "idle":
            self._stop_spinner()
            self.graph_spinner.hide()
            self.graph_tick.hide()
        elif state == "loading":
            self._start_spinner()
        elif state == "done":
            self._stop_spinner_with_tick()

    def _ensure_spinner_anim(self):
        if self._spinner_anim is not None:
            return
        self._spinner_anim = QVariantAnimation(self)
        self._spinner_anim.setStartValue(0)
        self._spinner_anim.setEndValue(360)
        self._spinner_anim.setDuration(900)
        self._spinner_anim.setLoopCount(-1)
        self._spinner_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._spinner_anim.valueChanged.connect(
            lambda v: self.graph_spinner.setAngle(v)
        )

    def _start_spinner(self):
        self._ensure_spinner_anim()
        self.graph_spinner.show()
        self.graph_tick.hide()
        if self._spinner_anim.state() != QVariantAnimation.Running:
            self._spinner_anim.start()

    def _stop_spinner(self):
        if self._spinner_anim:
            self._spinner_anim.stop()

    def _ensure_tick_anim(self):
        if self._tick_anim is not None:
            return
        self._tick_anim = QVariantAnimation(self)
        self._tick_anim.setStartValue(0.0)
        self._tick_anim.setEndValue(1.0)
        self._tick_anim.setDuration(220)
        self._tick_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._tick_anim.valueChanged.connect(
            lambda v: self.graph_tick.setProgress(v)
        )

    def _stop_spinner_with_tick(self):
        self._stop_spinner()
        self._ensure_tick_anim()
        self.graph_spinner.hide()
        self.graph_tick.show()
        self._tick_anim.stop()
        self.graph_tick.setProgress(0.0)
        self._tick_anim.start()
        QTimer.singleShot(1600, lambda: self.graph_tick.hide())

    # ─────────────────────────── arrow button (account.py pattern) ───────────────────────────

    def _prepare_arrow_source(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        candidates = [
            (os.path.join(base_dir, "assets", "arrow_right.png"), 0),
            (os.path.join(base_dir, "assets", "right_arrow.png"), 0),
            (os.path.join(base_dir, "assets", "side_arrow.png"), 180),
            (os.path.join(base_dir, "assets", "dropdown_arrow.png"), -90),
        ]
        self._arrow_source_pix = None
        for path, rotation in candidates:
            pix = QPixmap(path)
            if not pix.isNull():
                if rotation:
                    pix = pix.transformed(QTransform().rotate(rotation), Qt.SmoothTransformation)
                self._arrow_source_pix = pix
                break

    def _recolor_pixels(self, pixmap, color_hex):
        if pixmap is None or pixmap.isNull():
            return QPixmap()
        qcolor = QColor(color_hex)
        if not qcolor.isValid():
            qcolor = QColor("#FFFFFF")
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), qcolor)
        painter.end()
        return tinted

    def _setup_action_button_arrow(self, btn):
        if btn is None:
            return
        text_value = btn.text()
        btn.setText("")

        content = QWidget(btn)
        content.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        content.setStyleSheet("background: transparent; border: none;")

        text_label = QLabel(text_value, content)
        text_label.setFont(btn.font())
        text_label.setStyleSheet("background: transparent; border: none; font-size: 13px;")

        arrow_label = QLabel(content)
        arrow_label.setObjectName("arrow")
        arrow_label.setStyleSheet("background: transparent; border: none;")

        anim = QPropertyAnimation(arrow_label, b"pos")
        anim.setDuration(150)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        self._action_button_content[btn] = {
            "content": content,
            "text": text_label,
            "arrow": arrow_label,
            "anim": anim,
        }
        self._layout_action_button_content(btn)

        btn.clicked.connect(self._on_edit_graph_clicked)
        btn.enterEvent = lambda e, b=btn: self._arrow_hover_enter(b)
        btn.leaveEvent = lambda e, b=btn: self._arrow_hover_leave(b)

    def _layout_action_button_content(self, btn):
        data = self._action_button_content.get(btn)
        if not data:
            return

        spacing = 3
        content = data["content"]
        text_label = data["text"]
        arrow_label = data["arrow"]

        text_label.adjustSize()
        text_w = text_label.width()
        text_h = text_label.height()

        pix = arrow_label.pixmap()
        if pix is None or pix.isNull():
            icon_w, icon_h = 10, 10
        else:
            icon_w, icon_h = pix.width(), pix.height()

        group_w = text_w + spacing + icon_w
        group_h = max(text_h, icon_h)
        x = max(0, (btn.width() - group_w) // 2)
        y = max(0, (btn.height() - group_h) // 2)

        content.setGeometry(x, y, group_w + self._arrow_hover_shift_px, group_h)
        text_label.move(0, max(0, (group_h - text_h) // 2))
        arrow_label.move(text_w + spacing, max(0, (group_h - icon_h) // 2))
        data["original_arrow_pos"] = QPoint(arrow_label.pos())

    def _arrow_hover_enter(self, btn):
        data = self._action_button_content.get(btn)
        if not data:
            return
        arrow = data["arrow"]
        anim = data["anim"]
        start_pos = arrow.pos()
        end_pos = QPoint(start_pos.x() + self._arrow_hover_shift_px, start_pos.y())
        anim.stop()
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.start()

    def _arrow_hover_leave(self, btn):
        data = self._action_button_content.get(btn)
        if not data:
            return
        arrow = data["arrow"]
        anim = data["anim"]
        current_pos = arrow.pos()
        end_pos = data.get("original_arrow_pos", QPoint(data["text"].width() + 3, current_pos.y()))
        anim.stop()
        anim.setStartValue(current_pos)
        anim.setEndValue(end_pos)
        anim.start()

    def _update_action_button_arrows(self, color_hex):
        if self._arrow_source_pix is None:
            return
        tinted = self._recolor_pixels(self._arrow_source_pix, color_hex)
        if tinted.isNull():
            return
        arrow_pix = tinted.scaled(QSize(10, 10), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        for btn, data in self._action_button_content.items():
            arrow_label = data["arrow"]
            arrow_label.setPixmap(arrow_pix)
            arrow_label.resize(arrow_pix.size())
            self._layout_action_button_content(btn)

    def _update_action_button_content_color(self, color_hex):
        for btn, data in self._action_button_content.items():
            text_label = data["text"]
            text_label.setStyleSheet(
                f"background: transparent; border: none; color: {color_hex}; font-size: 13px;"
            )
            self._layout_action_button_content(btn)

    # ─────────────────────────── helpers ───────────────────────────

    def _style_input(self, inp):
        mono_family = self.ui.fonts.get("mono") or "Roboto Mono"
        inp.setFont(QFont(mono_family, 11))
        inp.setStyleSheet("""
            QLineEdit {
                color: #FFFFFF;
                background-color: #3c3c3c;
                border: 1px solid #5b5b5b;
                border-radius: 10px;
                padding-left: 10px;
            }
            QLineEdit:focus { border: 1px solid #7a7a7a; }
            QLineEdit::placeholder { color: #8b8b8b; }
        """)

    def _reload_graphs(self, select=None):
        try:
            self.graphs = get_user_graph_names(self.current_user)
        except Exception:
            self.graphs = []
        if select and select in self.graphs:
            self.selected_graph = select
        elif self.selected_graph not in self.graphs:
            self.selected_graph = None
        self._build_graph_buttons()
        self._refresh_selected_label()

        # notify add_pixel screen
        try:
            ap = getattr(self.ui, "add_pixel_screen", None)
            if ap and hasattr(ap, "refresh_after_account_change"):
                ap.refresh_after_account_change()
        except Exception:
            pass

        # notify settings screen so its dropdown stays in sync
        try:
            ss = getattr(self.ui, "settings_screen", None)
            if ss and hasattr(ss, "_rebuild_display_dropdown_items"):
                ss._rebuild_display_dropdown_items(self.graphs)
                # re-sync selection in case current graph was deleted
                try:
                    from helpers.json_manager import get_current_graph
                    current = get_current_graph() or {}
                    selected_graph = current.get("graph")
                    if selected_graph not in self.graphs:
                        selected_graph = self.graphs[0] if self.graphs else None
                    if selected_graph:
                        ss.display_dropdown.set_value(selected_graph)
                except Exception:
                    pass
        except Exception:
            pass

    # ─────────────────────────── theme ───────────────────────────

    def update_accent_colors(self):
        if not self._setup_done:
            return
        theme = get_theme()
        accent = theme.get("accent_color", "#5BF69F")
        hover = theme.get("hover_color", "#48C47F")
        text = theme.get("text_color", "#FFFFFF")

        for btn in self.accent_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    border-radius: 11px;
                    color: {text};
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {hover}; }}
                QPushButton:pressed {{ background-color: {hover}; }}
            """)
            if hasattr(btn, "set_text_color"):
                btn.set_text_color(text)

        self._refresh_graph_button_styles()

        if hasattr(self, "graph_spinner"):
            self.graph_spinner.update_color(accent)
        if hasattr(self, "graph_tick"):
            self.graph_tick.update_color(accent)

        if hasattr(self, "type_toggle"):
            self.type_toggle.update_colors(
                accent_color=accent,
                hover_color=hover,
                text_color=text,
            )

        self._update_action_button_arrows(text)
        self._update_action_button_content_color(text)

    # ─────────────────────────── refresh after account change ───────────────────────────

    def refresh_after_account_change(self):
        if not self._setup_done:
            return
        self._load_data()
        self.current_user_value.setText(self.current_user or "unknown")
        self.selected_graph = None
        self._reload_graphs(select=None)

"""
IntFltToggle — a pill-style int / flt selector matching the Graphs screen design.
The active option slides under an accent-coloured indicator.
"""
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QFrame
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve


class IntFltToggle(QWidget):
    """
    A two-option pill toggle: 'int' on the left, 'flt' on the right.
    Call `set_value('int')` or `set_value('flt')` to change selection.
    Pass `on_change=callable(str)` to receive selection events.
    """

    def __init__(
        self,
        parent=None,
        *,
        on_change=None,
        accent_color="#5BF69F",
        hover_color="#48C47F",
        text_color="#1e1e1e",
        inactive_text="#a0a0a0",
        track_color="#5a5a5a",
        initial_value="int",
    ):
        super().__init__(parent)
        self._on_change = on_change
        self._accent = accent_color
        self._hover = hover_color
        self._text_color = text_color
        self._inactive_text = inactive_text
        self._track_color = track_color
        self._value = initial_value

        # Fixed size matches Figma: 100 × 20
        self.setFixedSize(100, 20)
        self._build()
        self.set_value(initial_value, animate=False)

    # ── build ──────────────────────────────────────────────────────────

    def _build(self):
        # Track (grey pill background)
        self._track = QFrame(self)
        self._track.setGeometry(0, 0, 100, 20)
        self._track.setAttribute(Qt.WA_StyledBackground, True)
        self._track.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update_track_style()

        # Sliding indicator
        self._indicator = QFrame(self)
        self._indicator.setFixedSize(50, 20)
        self._indicator.setAttribute(Qt.WA_StyledBackground, True)
        self._indicator.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update_indicator_style()

        # Slide animation
        self._anim = QPropertyAnimation(self._indicator, b"pos", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # Labels (raised above indicator so they are always readable)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        self._lbl_flt = QLabel("flt", self)
        self._lbl_flt.setGeometry(0, 0, 50, 20)
        self._lbl_flt.setAlignment(Qt.AlignCenter)
        self._lbl_flt.setFont(font)
        self._lbl_flt.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._lbl_int = QLabel("int", self)
        self._lbl_int.setGeometry(50, 0, 50, 20)
        self._lbl_int.setAlignment(Qt.AlignCenter)
        self._lbl_int.setFont(font)
        self._lbl_int.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Invisible click areas
        btn_flt = QPushButton(self)
        btn_flt.setGeometry(0, 0, 50, 20)
        btn_flt.setFlat(True)
        btn_flt.setStyleSheet("background: transparent; border: none;")
        btn_flt.setCursor(Qt.PointingHandCursor)
        btn_flt.clicked.connect(lambda: self.set_value("flt"))

        btn_int = QPushButton(self)
        btn_int.setGeometry(50, 0, 50, 20)
        btn_int.setFlat(True)
        btn_int.setStyleSheet("background: transparent; border: none;")
        btn_int.setCursor(Qt.PointingHandCursor)
        btn_int.clicked.connect(lambda: self.set_value("int"))

        self._raise_labels()

    def _raise_labels(self):
        self._lbl_flt.raise_()
        self._lbl_int.raise_()

    # ── public API ─────────────────────────────────────────────────────

    def value(self):
        return self._value

    def set_value(self, value, animate=True):
        if value not in ("int", "flt"):
            return
        changed = value != self._value
        self._value = value
        target_x = 50 if value == "int" else 0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._indicator.pos())
            from PySide6.QtCore import QPoint
            self._anim.setEndValue(QPoint(target_x, 0))
            self._anim.start()
        else:
            self._indicator.move(target_x, 0)
        self._update_labels()
        if changed and self._on_change:
            self._on_change(value)

    def update_colors(self, accent_color=None, hover_color=None,
                      text_color=None, inactive_text=None, track_color=None):
        if accent_color is not None:
            self._accent = accent_color
        if hover_color is not None:
            self._hover = hover_color
        if text_color is not None:
            self._text_color = text_color
        if inactive_text is not None:
            self._inactive_text = inactive_text
        if track_color is not None:
            self._track_color = track_color
        self._update_track_style()
        self._update_indicator_style()
        self._update_labels()

    # ── private ────────────────────────────────────────────────────────

    def _update_track_style(self):
        self._track.setStyleSheet(
            f"QFrame {{ background-color: {self._track_color}; border-radius: 10px; }}"
        )

    def _update_indicator_style(self):
        self._indicator.setStyleSheet(
            f"QFrame {{ background-color: {self._accent}; border-radius: 10px; }}"
        )

    def _update_labels(self):
        for lbl, opt in ((self._lbl_flt, "flt"), (self._lbl_int, "int")):
            active = self._value == opt
            color = self._text_color if active else self._inactive_text
            lbl.setStyleSheet(
                f"color: {color}; background: transparent; border: none;"
            )

from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt
from helpers.CustomWidgets import HoverScaleButton, apply_widget_shadow
from helpers.json_manager import get_theme
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SideBar(QWidget):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.setFixedSize(200, 550)
        self.setStyleSheet("background-color: transparent;")
        self.accent_buttons = []
        self.screen_buttons = {}

        # outer frame look
        self.frame = QFrame(self)
        self.frame.setGeometry(0, 0, 200, 550)
        self.frame.setStyleSheet("background-color: #2b2b2b; border-radius: 20px;")
        apply_widget_shadow(self.frame, radius=20)

        # Logo_frame1
        self.logo_frame = QFrame(self.frame)
        self.logo_frame.setGeometry(15, 15, 170, 57)
        self.logo_frame.setStyleSheet("background-color: #242424; border-radius: 20px;")

        # logo image
        self.logo_label = QLabel(self.logo_frame)
        self.logo_label.setGeometry(0, 0, 170, 57)
        self.logo_label.setAlignment(Qt.AlignCenter)
        try:
            pix = QPixmap(os.path.join(BASE_DIR, "assets", "pixemln-logo-text-side.png"))
            if not pix.isNull():
                self.logo_label.setPixmap(pix.scaled(200, 57, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass

        # sidebar buttons
        buttons = [
            ("Home", "home"),
            ("Add Pixel", "add_pixel"),
            ("Graphs", "graphs"),
            ("Account", "account"),
            ("Settings", "settings")
        ]


        y_start = 150


        for i, (text, screen_name) in enumerate(buttons):
            btn = HoverScaleButton(text, self.frame, border_radius=15)
            btn.setGeometry(25, y_start + i * 50, 150, 30)

            btn.setCursor(Qt.PointingHandCursor)

            inter_family = self.ui.fonts.get("inter") or self.ui.fonts.get("ui")
            if inter_family:
                btn.setFont(QFont(inter_family, 15))
            self.accent_buttons.append(btn)
            self.screen_buttons[screen_name] = btn
            self._apply_accent_button_style(btn, is_selected=False, inter_family=inter_family)


            btn.clicked.connect(
                lambda checked, name=screen_name: self._on_click(name)
            )

    def _apply_accent_button_style(self, btn, is_selected=False, inter_family=None):
        theme = get_theme()
        accent = theme.get("accent_color", "#5BF69F")
        hover = theme.get("hover_color", "#48C47F")
        text = theme.get("text_color", "#FFFFFF")
        normal_bg = "#3f3f3f"
        normal_hover = "#474747"
        unselected_text = "#9f9f9f"
        selected_border = "2px solid #FFFFFF"
        normal_border = "1px solid #4f4f4f"
        bg = accent if is_selected else normal_bg
        hover_bg = hover if is_selected else normal_hover
        fg = text if is_selected else unselected_text
        border = selected_border if is_selected else normal_border
        family = inter_family or ""
        btn.set_text_color(fg)
        btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg};
            border: {border};
            border-radius: 15px;
            color: {fg};
            font-family: "{family}";
            font-size: 15px;
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
        }}
        QPushButton:pressed {{
            background-color: {hover_bg};
            border: {border};
            border-radius: 15px;
        }}
        """)

    def update_accent_colors(self):
        inter_family = self.ui.fonts.get("inter") or self.ui.fonts.get("ui")
        selected = getattr(self.ui, "selected_screen", None)
        for screen_name, btn in self.screen_buttons.items():
            self._apply_accent_button_style(btn, is_selected=(screen_name == selected), inter_family=inter_family)

    def set_selected_screen(self, name: str):
        if not hasattr(self.ui, "selected_screen"):
            return
        inter_family = self.ui.fonts.get("inter") or self.ui.fonts.get("ui")
        for screen_name, btn in self.screen_buttons.items():
            self._apply_accent_button_style(btn, is_selected=(screen_name == name), inter_family=inter_family)

    def _on_click(self, name: str):
        if hasattr(self.ui, 'switch_to'):
            self.ui.switch_to(name)

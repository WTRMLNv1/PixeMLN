from PySide6.QtWidgets import QApplication, QWidget, QStackedWidget
from PySide6.QtGui import QFontDatabase, QFont, QIcon
from PySide6.QtCore import Qt
from ui.sidebar import SideBar
from ui.homepage import HomePage
from ui.add_pixels import AddPixels
from ui.settings import Settings
from ui.account import Account
from ui.graphs import Graphs
import ctypes
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\ui", "").replace("\\", "/")

class UI:
    def __init__(self):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pixemln.PixeMLN")
        self.app = QApplication.instance() or QApplication([])

        icon_path = os.path.join(BASE_DIR, "assets", "pixemln-logo-no_text-ico.ico")
        if not os.path.exists(icon_path):
            print(f"Warning: Icon file not found at path: {icon_path}")

        # SET APP ICON FIRST (IMPORTANT FOR TASKBAR)
        self.app.setWindowIcon(QIcon(icon_path))

        # CREATE MAIN WINDOW ONCE
        self.main_window = QWidget()
        self.main_window.setWindowTitle("PixeMLN")
        self.main_window.setWindowIcon(QIcon(icon_path))
        self.main_window.setFixedSize(900, 600)
        self.main_window.setStyleSheet("background-color: #1e1e1e;")


        self.fonts = {}

        def load_font(path):
            abs_path = os.path.join(BASE_DIR, path)
            fid = QFontDatabase.addApplicationFont(abs_path)
            if fid != -1:
                family = QFontDatabase.applicationFontFamilies(fid)[0]
                return family
            print(f"Warning: Could not load font: {abs_path}")
            return None

        # load fonts
        self.fonts["mono"] = load_font("fonts/RobotoMono-Bold.ttf")
        self.fonts["ui"]   = load_font("fonts/Inter-Bold.ttf")
        self.fonts["inter"] = self.fonts["ui"]
        self.fonts["roboto_mono"] = self.fonts["mono"]

        # make font families discoverable across widgets
        self.app.setProperty("pixemln_font_ui", self.fonts["ui"] or "Inter")
        self.app.setProperty("pixemln_font_mono", self.fonts["mono"] or "Roboto Mono")

        # set default app font (Inter)
        if self.fonts["ui"]:
            self.app.setFont(QFont(self.fonts["ui"], 10))

        self.selected_screen = None

        # persistent sidebar (placed on main window)
        self.sidebar = SideBar(self)
        self.sidebar.setParent(self.main_window)
        self.sidebar.setGeometry(25, 25, 200, 550)

        # central stacked area for screens
        self.stack = QStackedWidget(self.main_window)
        self.stack.setGeometry(235, 25, 640, 550)
        self.home_screen = HomePage()
        self.add_pixel_screen = AddPixels(self)
        self.settings_screen = Settings(self)
        self.account_screen = Account(self)
        self.graphs_screen = Graphs(self)
        self.screens = {}
        # initialize deferred UI elements
        self.home_screen.run()
        self.add_pixel_screen.run()
        self.settings_screen.run()
        self.account_screen.run()
        self.graphs_screen.run()
        self.add_screen(self.home_screen, "home")
        self.add_screen(self.add_pixel_screen, "add_pixel")
        self.add_screen(self.settings_screen, "settings")
        self.add_screen(self.account_screen, "account")
        self.add_screen(self.graphs_screen, "graphs")
        self.apply_theme()
        self.switch_to("home")

    def add_screen(self, widget, name: str):
        idx = self.stack.addWidget(widget)
        self.screens[name] = idx

    def switch_to(self, name: str):
        if name in self.screens:
            self.stack.setCurrentIndex(self.screens[name])
            self.selected_screen = name
            try:
                self.sidebar.set_selected_screen(name)
            except Exception:
                pass

    def run(self):
        self.main_window.show()
        return self.app.exec()

    def apply_theme(self):
        for widget in (
            self.sidebar,
            self.add_pixel_screen,
            self.settings_screen,
            self.account_screen,
            self.graphs_screen,
        ):
            try:
                widget.update_accent_colors()
            except Exception:
                pass

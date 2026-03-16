from ._shared import *

class SpinnerWidget(QWidget):
    """A lightweight arc spinner widget for loading/progress indicators.

    - Paints a partial circular arc based on the current angle.
    - Size, thickness, and color are configurable.
    - Intended to be driven by an external timer/animation.

    Usage
    -----
        spinner = SpinnerWidget(size=16, thickness=2, parent=some_widget)
        spinner.setAngle(90)
        spinner.setColor("#5BF69F")
    """

    def __init__(self, size=14, thickness=2, color=None, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        self._size = int(size)
        self._thickness = int(thickness)
        self._color = color
        self.setFixedSize(self._size, self._size)

    def setAngle(self, angle):
        self._angle = float(angle)
        self.update()

    def setColor(self, color):
        self._color = color
        self.update()

    def update_color(self, color):
        self.setColor(color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._color:
            pen_color = QColor(self._color)
        else:
            pen_color = self.palette().highlight().color()
        pen = QPen(pen_color, self._thickness)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        rect = self.rect().adjusted(
            self._thickness,
            self._thickness,
            -self._thickness,
            -self._thickness
        )
        painter.drawArc(
            rect,
            int(-self._angle * 16),
            int(-270 * 16)
        )


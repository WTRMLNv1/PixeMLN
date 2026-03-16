from ._shared import *

class TickWidget(QWidget):
    """A progressive check-mark painter for success/complete animations.

    - Draws the tick in two segments as `progress` moves from 0.0 to 1.0.
    - Supports configurable size, stroke thickness, and color.
    - Works well with a property animation that drives `setProgress`.

    Usage
    -----
        tick = TickWidget(size=14, thickness=2, parent=some_widget)
        tick.setColor("#5BF69F")
        tick.setProgress(0.75)
    """

    def __init__(self, size=14, thickness=2, color=None, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._size = int(size)
        self._thickness = int(thickness)
        self._color = color
        self.setFixedSize(self._size, self._size)

    def setProgress(self, p):
        self._progress = max(0.0, min(1.0, float(p)))
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

        p1 = (self._size * 0.2, self._size * 0.55)
        p2 = (self._size * 0.45, self._size * 0.75)
        p3 = (self._size * 0.8, self._size * 0.25)

        if self._progress < 0.5:
            t = self._progress / 0.5
            painter.drawLine(
                int(p1[0]),
                int(p1[1]),
                int(p1[0] + (p2[0] - p1[0]) * t),
                int(p1[1] + (p2[1] - p1[1]) * t),
            )
        else:
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
            t = (self._progress - 0.5) / 0.5
            painter.drawLine(
                int(p2[0]),
                int(p2[1]),
                int(p2[0] + (p3[0] - p2[0]) * t),
                int(p2[1] + (p3[1] - p2[1]) * t),
            )


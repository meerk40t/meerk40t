import wx

from meerk40t.gui.scene.widget import Widget


class ControlWidget(Widget):
    def __init__(self, scene):
        super().__init__(scene, 0, 0, 10000, 10000)

    def process_draw(self, gc: wx.GraphicsContext):
        gc.SetBrush(wx.RED_BRUSH)
        gc.DrawEllipse(
            self.left, self.top, self.right - self.left, self.bottom - self.top
        )

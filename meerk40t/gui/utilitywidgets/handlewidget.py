import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
)
from meerk40t.gui.scene.widget import Widget


class HandleWidget(Widget):

    def __init__(self, scene, left, top, right, bottom, bitmap):
        Widget.__init__(self, scene, left, top, right, bottom)
        self.bitmap = bitmap
        self.background_brush = None
        self.enabled = True

    def hit(self):
        if self.enabled:
            return HITCHAIN_HIT
        else:
            return HITCHAIN_DELEGATE

    def process_draw(self, gc: wx.GraphicsContext):
        gc.PushState()
        if self.background_brush is not None:
            gc.SetBrush(self.background_brush)
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.DrawRectangle(self.left, self.top, self.width, self.height)
        gc.DrawBitmap(self.bitmap, self.left, self.top, self.width, self.height)
        gc.PopState()

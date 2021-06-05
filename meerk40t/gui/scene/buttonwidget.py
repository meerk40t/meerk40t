import wx

from meerk40t.gui.scene.scene import (HITCHAIN_DELEGATE, HITCHAIN_HIT,
                                      RESPONSE_ABORT, Widget)
from meerk40t.gui.zmatrix import ZMatrix


class ButtonWidget(Widget):
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
        gc.SetTransform(ZMatrix(self.matrix))
        if self.background_brush is not None:
            gc.SetBrush(self.background_brush)
            gc.DrawRectangle(0, 0, self.width, self.height)
        gc.DrawBitmap(self.bitmap)
        gc.PopState()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftdown":
            self.clicked(window_pos=None, space_pos=None)
        return RESPONSE_ABORT

    def clicked(self, window_pos=None, space_pos=None):
        pass

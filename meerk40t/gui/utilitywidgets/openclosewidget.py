import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE_AND_HIT,
    HITCHAIN_HIT,
    RESPONSE_ABORT,
)
from meerk40t.gui.scene.widget import Widget

_ = wx.GetTranslation


class OpenCloseWidget(Widget):
    def __init__(self, scene, bitmap):
        Widget.__init__(self, scene)
        self.bitmap = bitmap
        self._opened = False
        self.scene.request_refresh()

    def hit(self):
        if self._opened:
            return HITCHAIN_DELEGATE_AND_HIT
        else:
            return HITCHAIN_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        gc.PushState()
        gc.DrawBitmap(self.bitmap, self.left, self.top, self.width, self.height)
        gc.PopState()

    def draw(self, gc):
        if self._opened:
            super().draw(gc)
        else:
            self.process_draw(gc)

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type == "leftdown":
            self._opened = not self._opened
        return RESPONSE_ABORT

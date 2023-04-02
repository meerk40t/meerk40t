"""
Relocate widget adds a widget relocation widget. Moving the widget will cause the direct parent of this widget to
move. The expectation is that the parent type of this widget will DELEGATE or DELEGATE and HIT.

This is usually used for a group of widgets which should be moved together.
"""

import wx

from meerk40t.gui import icons
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CONSUME
from meerk40t.gui.scene.widget import Widget


class RelocateWidget(Widget):
    def __init__(self, scene, x, y):
        size = 10000
        Widget.__init__(self, scene, x - size, y - size, x + size, y + size)
        self.bitmap = icons.icons8_center_of_gravity_50.GetBitmap()

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        gc.DrawBitmap(self.bitmap, self.left, self.top, self.width, self.height)

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type == "move":
            dx = space_pos[4]
            dy = space_pos[5]
            self.parent.translate(dx, dy)
            self.scene.request_refresh()
        return RESPONSE_CONSUME

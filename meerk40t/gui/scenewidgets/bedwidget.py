"""
Bedwidget is entirely concerned with drawing the background bed object. This is usually white colored box.

If a background is set, e.g. a camera image that is displayed instead. If there is a background image then, this widget
also implements a right-click menu to remove said background image.
"""

import wx

from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND, swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
)
from meerk40t.gui.scene.widget import Widget


class BedWidget(Widget):
    """
    Bed Widget Interface Widget
    """

    def __init__(self, scene, name=None):
        Widget.__init__(self, scene, all=True)
        if name is None:
            self.name = "Standard"
        else:
            self.name = name
        self._background = {}

    @property
    def background(self):
        try:
            devlabel =  self.scene.context.device.label
            if devlabel in self._background:
                return self._background[devlabel]
        except AttributeError:
            pass
        return None

    @background.setter
    def background(self, value):
        try:
            devlabel =  self.scene.context.device.label
        except AttributeError:
            return

        if value is None:
            self._background.pop(devlabel, None)
        else:
            self._background[devlabel] = value

    def hit(self):
        if self.background is None:
            return HITCHAIN_DELEGATE
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        """
        Capture and deal with the double click event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "doubleclick":
            menu = wx.Menu()
            _ = self.scene.context._
            if self.background is not None:
                item = menu.Append(wx.ID_ANY, _("Remove Background"), "")
                self.scene.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.scene.gui.signal("background", None),
                    id=item.GetId(),
                )
                if menu.MenuItemCount != 0:
                    self.scene.gui.PopupMenu(menu)
                    menu.Destroy()
        return RESPONSE_CHAIN

    def process_draw(self, gc):
        """
        Draws the background on the scene.
        """
        # print ("Bedwidget draw %s" % self.name)
        if self.scene.context.draw_mode & DRAW_MODE_BACKGROUND == 0:
            context = self.scene.context
            try:
                unit_width = context.device.view.unit_width
                unit_height = context.device.view.unit_height
            except AttributeError:
                return
            background = self.background
            if background is None:
                brush = wx.Brush(
                    colour=self.scene.colors.color_bed, style=wx.BRUSHSTYLE_SOLID
                )
                gc.SetBrush(brush)
                gc.DrawRectangle(0, 0, unit_width, unit_height)
            elif isinstance(background, int):
                gc.SetBrush(wx.Brush(wx.Colour(swizzlecolor(background))))
                gc.DrawRectangle(0, 0, unit_width, unit_height)
            else:
                gc.DrawBitmap(background, 0, 0, unit_width, unit_height)

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        if signal == "background":
            self.background = args[0]
            if args[0] is None:
                self.scene.has_background = False
            elif isinstance(args[0], int):
                # A pure color is not deemed to represent a 'real' background
                self.scene.has_background = False
            else:
                self.scene.has_background = True
                self.scene.active_background = self.background

import wx

from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND, swizzlecolor
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN
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
        self.background = None

    def hit(self):
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
            unit_width = context.device.unit_width
            unit_height = context.device.unit_height
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
                self.scene.pane.has_background = False
            elif isinstance(args[0], int):
                # A pure color is not deemed to represent a 'real' background
                self.scene.pane.has_background = False
            else:
                self.scene.pane.has_background = True

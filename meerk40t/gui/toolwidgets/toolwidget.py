import wx

from meerk40t.gui.scene.widget import Widget

from ..scene.scene import Scene
from ..scene.sceneconst import HITCHAIN_HIT
from .circlebrush import CircleBrush


class ToolWidget(Widget):
    """
    AbstractClass for the ToolWidgets
    """

    def __init__(self, scene: Scene):
        Widget.__init__(self, scene, all=True)
        self.brush = CircleBrush()
        self.pen = wx.Pen()
        self.pen.SetColour(wx.BLUE)
        self.pen.SetWidth(1000)
        # Set proper default values for cap and join
        # as MKs defaults differ from wxPythons...
        self.pen.SetCap(wx.CAP_BUTT)
        self.pen.SetJoin(wx.JOIN_MITER)

    def hit(self):
        return HITCHAIN_HIT

    def notify_created(self, node=None):
        self.scene.context.signal("element_added", node)
        select_it = getattr(self.scene.context, "auto_select", True)
        if select_it:
            self.scene.context.elements.set_emphasis([node])
        else:
            self.scene.context.elements.set_emphasis(None)
        ## Make some final steps like deemphasize existing elements etc

    def process_draw(self, gc):
        self.brush.draw(gc)

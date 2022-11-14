import wx

from meerk40t.gui.laserrender import DRAW_MODE_RETICLE
from meerk40t.gui.scene.widget import Widget
from meerk40t.svgelements import Color


class ReticleWidget(Widget):
    """
    SceneWidget

    Draw the tracking reticles. Each different origin for the driver;position and emulator;position
    gives a new tracking reticle.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.reticles = {}
        self.pen = wx.Pen()

    def init(self, context):
        """
        Listen to driver;position and emulator;position
        """
        context.listen("driver;position", self.on_update_driver)
        context.listen("emulator;position", self.on_update_emulator)

    def final(self, context):
        """
        Unlisten to driver;position and emulator;position
        """
        context.unlisten("driver;position", self.on_update_driver)
        context.unlisten("emulator;position", self.on_update_emulator)

    def on_update_driver(self, origin, pos):
        """
        Update of driver adds and ensures the location of the d+origin position
        """
        self.reticles["d" + origin] = pos[2], pos[3]
        self.scene.request_refresh_for_animation()

    def on_update_emulator(self, origin, pos):
        """
        Update of emulator adds and ensures the location of the e+origin position
        """
        self.reticles["e" + origin] = pos[2], pos[3]
        self.scene.request_refresh_for_animation()

    def process_draw(self, gc):
        """
        Draw all the registered reticles.
        """
        context = self.scene.context
        try:
            if context.draw_mode & DRAW_MODE_RETICLE == 0:
                # Draw Reticles
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
                for index, ret in enumerate(self.reticles):
                    r = self.reticles[ret]
                    self.pen.SetColour(Color.distinct(index + 2).hex)
                    gc.SetPen(self.pen)
                    x = r[0]
                    y = r[1]
                    if x is None or y is None:
                        x = 0
                        y = 0
                    x, y = self.scene.convert_scene_to_window([x, y])
                    gc.DrawEllipse(x - 5, y - 5, 10, 10)
        except AttributeError:
            pass

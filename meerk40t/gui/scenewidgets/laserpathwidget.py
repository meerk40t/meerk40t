"""
This widget draws laser position updates in blue lines to highlight the changes in the laser positions.
"""

import wx

from meerk40t.gui.laserrender import DRAW_MODE_LASERPATH
from meerk40t.gui.scene.widget import Widget


class LaserPathWidget(Widget):
    """
    Scene Widget.

    Draw the laserpath.

    These are blue lines that track the previous position of the laser-head.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.laserpath = [[0, 0] for _ in range(1000)], [[0, 0] for _ in range(1000)]
        self.laserpath_index = 0

    def init(self, context):
        context.listen("driver;position", self.on_update)
        context.listen("emulator;position", self.on_update)

    def final(self, context):
        context.unlisten("driver;position", self.on_update)
        context.unlisten("emulator;position", self.on_update)

    def on_update(self, origin, pos):
        laserpath = self.laserpath
        index = self.laserpath_index
        laserpath[0][index][0] = pos[0]
        laserpath[0][index][1] = pos[1]
        laserpath[1][index][0] = pos[2]
        laserpath[1][index][1] = pos[3]
        index += 1
        index %= len(laserpath[0])
        self.laserpath_index = index

    def clear_laserpath(self):
        self.laserpath = [[0, 0] for _ in range(1000)], [[0, 0] for _ in range(1000)]
        self.laserpath_index = 0

    def process_draw(self, gc):
        """
        Draw the blue lines of the LaserPath
        """
        context = self.scene.context
        if context.draw_mode & DRAW_MODE_LASERPATH == 0:
            mycol = self.scene.colors.color_laserpath
            pen = wx.Pen(mycol)
            gc.SetPen(pen)
            starts, ends = self.laserpath
            try:
                gc.StrokeLineSegments(starts, ends)
            except OverflowError:
                pass  # I don't actually know why this would happen.

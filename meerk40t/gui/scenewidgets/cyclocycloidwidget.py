import math

import wx

from meerk40t.gui import icons
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    HITCHAIN_DELEGATE_AND_HIT,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scenewidgets.buttonwidget import ButtonWidget
from meerk40t.svgelements import Path


class CyclocycloidWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.pen = wx.Pen()
        self.pen.SetColour(wx.BLUE)
        self.pen.SetWidth(1000)

        self.series = []
        self.degree_step = 1
        self.rotations = 20
        self.r_minor = None
        self.r_major = None
        self.offset = None
        bed_width, bed_height = scene.context.device.physical_to_scene_position(
            "100%", "100%"
        )
        self.x, self.y = bed_width / 2, bed_height / 2
        size = 100000

        self.add_widget(
            -1,
            ButtonWidget(
                scene, 0, 0, size, size, icons.icon_corner1.GetBitmap(), self.confirm
            ),
        )
        self.add_widget(
            -1,
            ButtonWidget(
                scene,
                bed_width - size,
                0,
                bed_width,
                size,
                icons.icon_corner2.GetBitmap(),
                self.confirm,
            ),
        )
        self.add_widget(
            -1,
            ButtonWidget(
                scene,
                bed_width - size,
                bed_height - size,
                bed_width,
                bed_height,
                icons.icon_corner3.GetBitmap(),
                self.confirm,
            ),
        )
        self.add_widget(
            -1,
            ButtonWidget(
                scene,
                0,
                bed_height - size,
                size,
                bed_height,
                icons.icon_corner4.GetBitmap(),
                self.confirm,
            ),
        )
        self.update_shape()

    def confirm(self, **kwargs):
        try:
            t = Path(stroke="blue", stroke_width=1000)
            t.move(self.series[0])
            for m in self.series:
                t.line(m)
            elements = self.scene.context.elements
            node = elements.elem_branch.add(path=t, type="elem path")
            elements.classify([node])
            self.parent.remove_widget(self)
        except IndexError:
            pass
        self.series = None
        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_DELEGATE_AND_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        if self.series is not None and len(self.series) > 1:
            gc.SetPen(self.pen)
            gc.StrokeLines(self.series)

    def update_shape(self):
        import random

        self.r_minor = random.randint(5000, 50000)
        self.r_major = random.randint(self.r_minor, 50000)
        self.offset = random.randint(5000, 5000)
        self.series.clear()
        radian_step = math.radians(self.degree_step)
        t = 0
        m = math.tau * self.rotations
        while t < m:
            r_minor = self.r_minor
            r_major = self.r_major
            offset = self.offset
            px = (r_minor + r_major) * math.cos(t) - (r_minor + offset) * math.cos(
                ((r_major + r_minor) / r_minor) * t
            )
            py = (r_minor + r_major) * math.sin(t) - (r_minor + offset) * math.sin(
                ((r_major + r_minor) / r_minor) * t
            )
            self.series.append((self.x + px, self.y + py))
            t += radian_step
        self.scene.request_refresh()

    def event(
        self, window_pos=None, space_pos=None, event_type=None, nearest_snap=None
    ):
        response = RESPONSE_CHAIN
        if self.series is None:
            self.series = []
        if event_type == "leftdown":
            self.update_shape()
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            self.confirm()
            response = RESPONSE_CONSUME
        return response

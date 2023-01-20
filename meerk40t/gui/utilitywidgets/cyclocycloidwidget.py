import math

import wx

from meerk40t.gui import icons
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE_AND_HIT,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scenewidgets.relocatewidget import RelocateWidget
from meerk40t.gui.utilitywidgets.buttonwidget import ButtonWidget
from meerk40t.svgelements import Path


class CyclocycloidWidget(Widget):
    """
    Cyclocycloid widgets performs basic epicycloidal shapes. This code is also set to be solid example code for a
    widget with some advanced controls. It contains a relocation widget and several button widgets. It shows how to
    use animations to better implement subtle changes to a particular parameter.
    """

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
                scene,
                0,
                0,
                size,
                size,
                icons.icon_corner1.GetBitmap(use_theme=False),
                self.confirm,
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
                icons.icon_corner2.GetBitmap(use_theme=False),
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
                icons.icon_corner3.GetBitmap(use_theme=False),
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
                icons.icon_corner4.GetBitmap(use_theme=False),
                self.confirm,
            ),
        )
        self.add_widget(-1, RelocateWidget(scene, self.x, self.y))
        self.add_widget(-1, MajorHandleWidget(scene, self))
        self.add_widget(-1, MinorHandleWidget(scene, self))
        self.random_shape()
        self.update_shape()

    def translate_self(self, dx, dy):
        """
        Dx and Dy for the translation provided by the relocation widget fails to move the x and y value since they
        are not from the base widget. This hook catches the self translation routine and also changes x and y position
        @param dx:
        @param dy:
        @return:
        """
        Widget.translate_self(self, dx, dy)
        self.x += dx
        self.y += dy

    def confirm(self, **kwargs):
        """
        Converts the series into a path and adds it to the current scene. This removes the current widget when executed
        @param kwargs:
        @return:
        """
        try:
            elements = self.scene.context.elements
            t = Path(
                stroke=elements.default_stroke,
                stroke_width=elements.default_strokewidth,
            )
            t.move((self.series[0][0] + self.x, self.series[0][1] + self.y))
            for m in self.series:
                t.line((m[0] + self.x, m[1] + self.y))
            node = elements.elem_branch.add(path=t, type="elem path")
            elements.classify([node])
            self.parent.remove_widget(self)
        except IndexError:
            pass
        self.series = None
        self.scene.request_refresh()

    def hit(self):
        """
        Since this widget has button, major, minor and relocation widgets it should process the children first then
        if those children do not handle the events, process itself.
        @return:
        """
        return HITCHAIN_DELEGATE_AND_HIT

    def process_draw(self, gc: wx.GraphicsContext):
        gc.PushState()
        gc.Translate(self.x, self.y)
        if self.series is not None and len(self.series) > 1:
            gc.SetPen(self.pen)
            gc.StrokeLines(self.series)
        gc.PopState()

    def random_shape(self):
        """
        Randomizes the shape.
        @return:
        """
        import random

        self.r_minor = random.randint(5000, 50000)
        self.r_major = random.randint(self.r_minor, 50000)
        self.offset = random.randint(0, 5000)
        self.offset = 0

    def update_shape(self):
        """
        Updates the shape and regenerates the series based on the current values.

        @return:
        """
        self.series.clear()
        radian_step = math.radians(self.degree_step)
        t = 0
        m = math.tau * self.rotations
        while t < m:
            r_minor = self.r_minor
            if r_minor == 0:
                r_minor = 1
            r_major = self.r_major
            offset = self.offset
            px = (r_minor + r_major) * math.cos(t) - (r_minor + offset) * math.cos(
                ((r_major + r_minor) / r_minor) * t
            )
            py = (r_minor + r_major) * math.sin(t) - (r_minor + offset) * math.sin(
                ((r_major + r_minor) / r_minor) * t
            )
            self.series.append((px, py))
            t += radian_step
        self.scene.request_refresh_for_animation()

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        response = RESPONSE_CHAIN
        if self.series is None:
            self.series = []
        if event_type == "leftdown":
            self.random_shape()
            self.update_shape()
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            self.confirm()
            response = RESPONSE_CONSUME
        return response


class MajorHandleWidget(Widget):
    """
    Widget to adjust the radius major of the shape. Performs this adjustment within an animation.
    """

    def __init__(self, scene, cyclowidget):
        self.size = 20000
        Widget.__init__(self, scene, 0, 0, self.size, self.size)
        self.pen = wx.Pen()
        self.pen.SetColour(wx.BLUE)
        self.pen.SetWidth(1000)
        self.widget = cyclowidget
        self.bitmap = icons.icons8_point_50.GetBitmap(use_theme=False)
        self._start_x = None
        self._start_y = None
        self._current_x = None
        self._current_y = None
        self._start_value = None

    def hit(self):
        return HITCHAIN_HIT

    def tick(self):
        """
        This widget is animated, we slowly adjust the value based on the current location.
        @return: True, if more to animate.
        """
        if self._current_x is None or self._current_y is None:
            return False
        diff = self._current_x - self._start_x
        self._start_value += diff * 0.01
        self.widget.r_major = self._start_value
        self.widget.update_shape()
        return True

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Draws the current widget, simply a bitmap.
        @param gc:
        @return:
        """
        self.left = self.widget.x + self.widget.r_major - self.width / 2
        self.top = self.widget.y - self.height / 2
        self.right = self.left + self.size
        self.bottom = self.top + self.size
        gc.DrawBitmap(self.bitmap, self.left, self.top, self.width, self.height)

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.scene.animate(
                self
            )  # Starts the animation. This will stop when tick() returns false.
            self._start_x = space_pos[0]
            self._start_y = space_pos[1]
            self._current_x = space_pos[0]
            self._current_y = space_pos[1]
            self._start_value = self.widget.r_major
            response = RESPONSE_CONSUME
        elif event_type == "move":
            self._current_x = space_pos[0]
            self._current_y = space_pos[1]
            response = RESPONSE_CONSUME
        elif event_type == "leftup":
            self._start_x = None
            self._start_y = None
            self._current_x = None
            self._current_y = None
            self._start_value = None
            response = RESPONSE_CONSUME
        return response


class MinorHandleWidget(Widget):
    """
    Does the same as Major but for the r_minor of the given shape.
    """

    def __init__(self, scene, cyclowidget):
        self.size = 20000
        Widget.__init__(self, scene, 0, 0, self.size, self.size)
        self.pen = wx.Pen()
        self.pen.SetColour(wx.BLUE)
        self.pen.SetWidth(1000)
        self.widget = cyclowidget
        self.bitmap = icons.icons8_point_50.GetBitmap(use_theme=False)
        self._start_x = None
        self._start_y = None
        self._current_x = None
        self._current_y = None
        self._start_value = None

    def hit(self):
        return HITCHAIN_HIT

    def tick(self):
        if self._current_x is None or self._current_y is None:
            return False
        diff = self._current_x - self._start_x
        self._start_value += diff * 0.01
        self.widget.r_minor = self._start_value
        self.widget.update_shape()
        return True

    def process_draw(self, gc: wx.GraphicsContext):
        self.left = (
            self.widget.x
            + self.widget.r_major
            + (self.widget.r_minor * 2)
            - self.width / 2
        )
        self.top = self.widget.y - self.height / 2
        self.right = self.left + self.size
        self.bottom = self.top + self.size
        gc.DrawBitmap(self.bitmap, self.left, self.top, self.width, self.height)

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.scene.animate(self)
            self._start_x = space_pos[0]
            self._start_y = space_pos[1]
            self._current_x = space_pos[0]
            self._current_y = space_pos[1]
            self._start_value = self.widget.r_minor
            response = RESPONSE_CONSUME
        elif event_type == "move":
            self._current_x = space_pos[0]
            self._current_y = space_pos[1]
            response = RESPONSE_CONSUME
        elif event_type == "leftup":
            self._start_x = None
            self._start_y = None
            self._current_x = None
            self._current_y = None
            self._start_value = None
            response = RESPONSE_CONSUME
        return response

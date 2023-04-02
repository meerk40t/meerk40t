import math
import random

import numpy as np
import wx
from meerk40t.gui import icons
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scenewidgets.relocatewidget import RelocateWidget
from meerk40t.gui.utilitywidgets.buttonwidget import ButtonWidget
from meerk40t.gui.utilitywidgets.openclosewidget import OpenCloseWidget
from meerk40t.gui.utilitywidgets.rotationwidget import RotationWidget
from meerk40t.gui.utilitywidgets.scalewidget import ScaleWidget
from meerk40t.gui.utilitywidgets.toolbarwidget import ToolbarWidget
from meerk40t.gui.zmatrix import ZMatrix
from meerk40t.svgelements import Path, Matrix


class HShape:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.display_x = True
        self.display_y = True
        self.use_phase = True
        self.use_offset = True
        self.use_rotate = True
        self.use_scale_x = True
        self.use_scale_y = True
        self.use_damp = True
        self.use_speed = True
        self.use_xeqy = True

        self.damping = 0.1
        self.phase = 0.5
        self.speed = 1.0
        self.frequency = 1.0
        self.amplitude = 1.0
        self.progression_x = 0
        self.progression_y = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.matrix = None
        self.offset = 0
        self.theta = 0

    def set_none(self):
        self.use_phase = False
        self.use_offset = False
        self.use_rotate = False
        self.use_scale_x = False
        self.use_scale_y = False
        self.use_damp = False
        self.use_speed = False
        self.use_xeqy = False

    def set_oval(self):
        self.set_none()
        self.use_phase = True
        self.use_offset = True
        self.use_rotate = True
        self.use_scale_x = True
        self.use_scale_y = True
        self.use_speed = True

    def set_circle(self):
        self.set_oval()
        self.use_xeqy = True

    def set_spiral(self):
        self.set_oval()
        self.use_damp = True

    def set_x_pendulum(self):
        self.set_none()
        self.display_x = True
        self.use_scale_x = True
        self.use_phase = True
        self.use_speed = True
        self.use_damp = True

    def set_y_pendulum(self):
        self.set_none()
        self.display_y = True
        self.use_scale_y = True
        self.use_phase = True
        self.use_speed = True
        self.use_damp = True

    def calculate_matrix(self):
        self.matrix = Matrix()
        scale_x = self.scale_x if self.use_scale_x else 1.0
        scale_y = self.scale_y if self.use_scale_y else 1.0
        if self.use_xeqy:
            scale_y = scale_x

        self.matrix.post_scale(
            self._get_offset() + scale_x, self._get_offset() + scale_y
        )
        self.matrix.post_rotate(self.theta)
        self.matrix.post_translate(self.x, self.y)
        return self.matrix

    def random(self):
        r = random.Random()
        self.scale_x = r.random() * 150 + 50
        self.scale_y = r.random() * 150 + 50
        self.speed = r.random() * 5 + 0.1
        self.damping = r.random() * 0.1 - 0.01
        self.phase = r.random()
        self.offset = r.random() * 10

    def _get_offset(self):
        if not self.use_offset:
            return 0
        return self.offset

    def _get_modified_time(self, t):
        speed = self.speed if self.use_speed else 1.0
        phase = self.phase if self.use_phase else 0.0
        return t * speed + phase

    def _get_damping(self, t):
        if not self.use_damp:
            return 1.0
        damp = self.damping
        speed = self.speed if self.use_speed else 1.0
        return np.exp(-damp * speed * t)

    def position(self, t):
        matrix = self.calculate_matrix()
        time = self._get_modified_time(t)
        damp = self._get_damping(t)
        if self.display_x:
            cos_t = np.cos(time * math.tau)
            x = cos_t * damp
        else:
            x = 0
        if self.display_y:
            sin_t = np.sin(time * math.tau)
            y = sin_t * damp
        else:
            y = 0
        x, y = matrix.point_in_matrix_space((x, y))
        # apply matrix
        x += self.progression_x * t
        y += self.progression_y * t

        series = np.stack((x, y), axis=1)
        return series


class HarmonographWidget(Widget):
    def __init__(self, scene):
        bed_width, bed_height = scene.context.device.physical_to_scene_position(
            "100%", "100%"
        )
        x, y = bed_width / 2, bed_height / 2
        super().__init__(scene, x, y, x, y)
        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.BLUE)
        self.shape_matrix = None

        self.curves = list()

        self.theta = 0
        self._scale = 1000.0
        self.rotations = 20.0

        size = 15000
        self.t_step = 0.015
        self.series = []
        self.add_pendulum_x()
        self.add_pendulum_y()

        accept_widget = ButtonWidget(
            scene,
            size * -2,
            size * -0.5,
            size * -1,
            size * 0.5,
            icons.icons8_checkmark_50.GetBitmap(use_theme=False),
            self.confirm,
        )
        accept_widget.background_brush = wx.WHITE_BRUSH
        self.add_widget(-1, accept_widget)

        random_widget = ButtonWidget(
            scene,
            size * -0.5,
            size * -2,
            size * 0.5,
            size * -1,
            icons.icons8_next_page_20.GetBitmap(use_theme=False, resize=50),
            self.set_random_harmonograph,
        )
        random_widget.background_brush = wx.WHITE_BRUSH
        self.add_widget(-1, random_widget)

        remove_widget = ButtonWidget(
            scene,
            size * 1,
            size * -0.5,
            size * 2,
            size * 0.5,
            icons.icons8_delete_50.GetBitmap(use_theme=False),
            self.cancel,
        )
        remove_widget.background_brush = wx.WHITE_BRUSH
        self.add_widget(-1, remove_widget)

        relocate_widget = RelocateWidget(scene, 0, 0)
        self.add_widget(-1, relocate_widget)

        def delta_theta(delta):
            self.theta += delta
            self.shape_matrix = None
            self.scene.toast(f"theta: {self.theta}")

        rotation_widget = RotationWidget(
            scene,
            size * -1,
            size * 1,
            size * 0,
            size * 2,
            icons.icons8_rotate_left_50.GetBitmap(use_theme=False),
            delta_theta,
        )
        rotation_widget.background_brush = wx.WHITE_BRUSH
        self.add_widget(-1, rotation_widget)

        def delta_step(delta):
            self.t_step += delta / 1000.0
            if self.t_step <= 0.001:
                self.t_step = 0.001
            self.scene.toast(f"t_step: {self.t_step}")
            self.series = None

        step_handle = RotationWidget(
            scene,
            size * 0,
            size * 1,
            size * 1,
            size * 2,
            icons.icons8_fantasy_50.GetBitmap(use_theme=False),
            delta_step,
        )
        step_handle.background_brush = wx.WHITE_BRUSH
        self.add_widget(-1, step_handle)

        def delta_rotations(delta):
            self.rotations += delta
            self.scene.toast(f"rotations: {self.rotations}")
            self.series = None

        rotate_widget = RotationWidget(
            scene,
            size * -1,
            size * 2,
            size * 0,
            size * 3,
            icons.icons8_roll_50.GetBitmap(use_theme=False),
            delta_rotations,
        )
        rotate_widget.background_brush = wx.WHITE_BRUSH
        self.add_widget(-1, rotate_widget)

        scale_widget = ScaleWidget(scene, size * 0, size * 2, size * 1, size * 3)
        scale_widget.background_brush = wx.WHITE_BRUSH
        self.add_widget(-1, scale_widget)

        self.set_random_harmonograph()
        self.process_shape()

        curvebar = ToolbarWidget(scene, 5 * size, 0)
        for c in self.curves:
            curvebar.add_widget(
                -1,
                CurveWidget(
                    scene,
                    icons.icons8_computer_support_50.GetBitmap(use_theme=False),
                    c,
                ),
            )
        self.add_widget(-1, curvebar)

    @property
    def scale(self):
        return self._scale / 1000.0

    @scale.setter
    def scale(self, v):
        self._scale = 1000.0 * v
        self.process_matrix()
        self.scene.request_refresh()

    def add_pendulum_x(self, **kwargs):
        x_pen = HShape()
        x_pen.set_x_pendulum()
        x_pen.random()
        self.curves.append(x_pen)
        self.series = None

    def add_pendulum_y(self, **kwargs):
        y_pen = HShape()
        y_pen.set_y_pendulum()
        y_pen.random()
        self.curves.append(y_pen)
        self.series = None

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
            t.move((self.series[0][0], self.series[0][1]))
            for m in self.series:
                t.line((m[0], m[1]))
            self.process_matrix()
            t *= self.shape_matrix
            node = elements.elem_branch.add(path=abs(t), type="elem path")
            node.stroke_width = elements.default_strokewidth
            elements.classify([node])
            self.parent.remove_widget(self)
        except IndexError:
            pass
        self.series = None
        self.scene.request_refresh()

    def cancel(self, **kwargs):
        """
        Removes the current widget when executed
        @param kwargs:
        @return:
        """

        self.parent.remove_widget(self)
        self.series = None
        self.scene.request_refresh()

    def close_all_curve_widgets(self):
        for cw in self.curves:
            cw.minimize(-1)

    def set_random_harmonograph(self, **kwargs):
        for p in self.curves:
            p.random()
        self.series = None
        self.scene.request_refresh()

    def process_draw(self, gc: wx.GraphicsContext):
        gc.PushState()
        if self.shape_matrix is None:
            self.process_matrix()
        if self.series is None:
            self.process_shape()
        gc.ConcatTransform(
            wx.GraphicsContext.CreateMatrix(gc, ZMatrix(self.shape_matrix))
        )
        gc.SetPen(self.tool_pen)
        gc.StrokeLines(self.series)
        gc.PopState()

    def process_matrix(self):
        self.shape_matrix = Matrix()
        self.shape_matrix.post_rotate(self.theta)
        self.shape_matrix.post_scale(self._scale, self._scale)
        self.shape_matrix.post_translate(self.left, self.top)

    def notify_moved_child(self, child):
        self.process_matrix()

    def process_shape(self):
        if self.series is not None:
            return
        self.series = None
        step = self.t_step

        if step <= 0:
            step = 0.001
        steps = int(self.rotations / step)
        v = np.linspace(0, self.rotations, num=steps)
        total = None
        for p in self.curves:
            pos = p.position(v)
            if total is None:
                total = pos
            else:
                total += pos
        self.series = total

    def remove_curver(self, c):
        self.series = None
        self.curves.remove(c)
        self.process_shape()


class CurveWidget(OpenCloseWidget):
    def __init__(self, scene, bitmap, curve):
        super().__init__(scene, bitmap)
        self.curve = curve
        phase_control = ControlWidget(scene)
        self.add_widget(-1, phase_control)
        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.RED)
        self.tool_pen.SetWidth(1000)
        self.series = list()

    def process_draw(self, gc: wx.GraphicsContext):
        if self.series:
            return
        # self.series = None
        # step = 0.1 / SLICES
        #
        # if step <= 0:
        #     step = 0.001
        #
        # time = 0
        # while time < self.parent.parent.rotations:
        #     px = 0
        #     py = 0
        #     pdx, pdy = self.curve.position(time)
        #     px += pdx
        #     py += pdy
        #     px += self.left
        #     py += self.top
        #     self.series.append((px, py))
        #     time += step
        # gc.SetPen(self.tool_pen)
        # gc.StrokeLines(self.series)


class ControlWidget(Widget):
    def __init__(self, scene):
        super().__init__(scene, 0, 0, 10000, 10000)

    def process_draw(self, gc: wx.GraphicsContext):
        gc.SetBrush(wx.RED_BRUSH)
        gc.DrawEllipse(
            self.left, self.top, self.right - self.left, self.bottom - self.top
        )

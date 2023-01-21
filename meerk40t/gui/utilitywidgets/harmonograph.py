import math

import wx
from meerk40t.gui import icons
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scenewidgets.relocatewidget import RelocateWidget
from meerk40t.gui.utilitywidgets.buttonwidget import ButtonWidget
from meerk40t.gui.utilitywidgets.rotationwidget import RotationWidget
from meerk40t.gui.utilitywidgets.scalewidget import ScaleWidget
from meerk40t.gui.utilitywidgets.toolbarwidget import ToolbarWidget
from meerk40t.svgelements import Path, Matrix


class HShape:
    def __init__(self):
        self.x = 0
        self.y = 0
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

    def calculate_matrix(self):
        self.matrix = Matrix()
        self.matrix.post_scale(self._get_offset() + self.scale_x, self._get_offset, self.scale_y)
        self.matrix.post_rotate(self.theta)
        self.matrix.post_translate(self.x, self.y)

    def random(self):
        pass

    def _get_offset(self):
        return self.offset

    def _get_modified_time(self, t):
        return t * self.speed + self.phase

    def _get_damping(self, t):
        return math.exp(-self.damping * self.speed * t)

    def position(self, t):
        time = self._get_modified_time(t)
        cosT = math.cos(time * math.tau)
        sinT = math.sin(time * math.tau)
        damp = self._get_damping(t)
        x = cosT * damp
        y = sinT * damp
        # apply matrix
        x += self.progression_x * t
        y += self.progression_y * t
        return x, y


SLICES = 50


class HarmonographWidget(Widget):

    def __init__(self, scene):
        super().__init__(scene)
        toolPaint = wx.Pen()
        toolPaint.SetColour(wx.RED)
        toolPaint.SetWidth(10)
        bed_width, bed_height = scene.context.device.physical_to_scene_position(
            "100%", "100%"
        )
        self.x, self.y = bed_width / 2, bed_height / 2
        self.theta = 0
        self.scale = 1.0
        self.rotations = 50.0

        size = 10000
        self.degree_step = 0.1
        self.series = []
        self.curves = [HShape(), HShape()]

        toolbar = ToolbarWidget(scene, self.x, self.y + 35000)
        remove_widget = ButtonWidget(
                scene,
                0,
                0,
                size,
                size,
                icons.icons8_delete_50.GetBitmap(use_theme=False),
                self.confirm,
            )

        toolbar.add_widget(-1, remove_widget,)
        accept_widget = ButtonWidget(
                scene,
                0,
                0,
                size,
                size,
                icons.icons8_center_of_gravity_50.GetBitmap(use_theme=False),
                self.confirm,
            )
        toolbar.add_widget(-1, accept_widget)
        random_widget = ButtonWidget(
            scene,
            0,
            0,
            size,
            size,
            icons.icons8_center_of_gravity_50.GetBitmap(use_theme=False),
            self.set_random_harmonograph,
        )
        toolbar.add_widget(-1, random_widget)

        add_oval_widget = ButtonWidget(
            scene,
            0,
            0,
            size,
            size,
            icons.icons8_center_of_gravity_50.GetBitmap(use_theme=False),
            self.add_oval,
        )
        toolbar.add_widget(-1, add_oval_widget)
        add_circle_widget = ButtonWidget(
            scene,
            0,
            0,
            size,
            size,
            icons.icons8_center_of_gravity_50.GetBitmap(use_theme=False),
            self.add_circle,
        )
        toolbar.add_widget(-1, add_circle_widget)
        add_y_pendulum_widget = ButtonWidget(
            scene,
            0,
            0,
            size,
            size,
            icons.icons8_center_of_gravity_50.GetBitmap(use_theme=False),
            self.add_pendulum_y,
        )
        toolbar.add_widget(-1, add_y_pendulum_widget)
        add_x_pendulum_widget = ButtonWidget(
            scene,
            0,
            0,
            size,
            size,
            icons.icons8_center_of_gravity_50.GetBitmap(use_theme=False),
            self.add_pendulum_x,
        )
        toolbar.add_widget(-1, add_x_pendulum_widget)
        add_spiral_widget = ButtonWidget(
            scene,
            0,
            0,
            size,
            size,
            icons.icons8_center_of_gravity_50.GetBitmap(use_theme=False),
            self.add_spiral,
        )
        toolbar.add_widget(-1, add_spiral_widget)

        self.add_widget(-1, toolbar)
        self.add_widget(-1, RelocateWidget(scene, self.x, self.y))

        def delta_theta(delta):
            self.theta += delta
            self.scene.toast(f"theta: {self.theta}")

        rotation_widget = RotationWidget(scene, self.x + 0, self.y + 20000, self.x + 10000, self.y + 30000, icons.icons8_rotate_left_50.GetBitmap(use_theme=False), delta_theta)
        self.add_widget(-1, rotation_widget)

        def delta_step(delta):
            self.degree_step += delta
            self.scene.toast(f"degree_step: {self.degree_step}")

        step_handle = RotationWidget(scene, self.x + 0, self.y + 50000, self.x + 10000, self.y + 60000, icons.icons8_fantasy_50.GetBitmap(use_theme=False), delta_step)
        self.add_widget(-1, step_handle)

        def delta_rotations(delta):
            self.rotations += delta
            self.scene.toast(f"rotations: {self.rotations}")

        rotate_widget = RotationWidget(scene, self.x + 0, self.y + 60000, self.x + 10000, self.y + 70000,  icons.icons8_rotate_left_50.GetBitmap(use_theme=False), delta_rotations)
        self.add_widget(-1, rotate_widget)

        scale_widget = ScaleWidget(scene, self.x, self.y + 80000, self.x + 10000, self.y + 90000)
        self.add_widget(-1, scale_widget)

        self.set_random_harmonograph()
        self.process_shape()

    def add_oval(self):
        pass

    def add_circle(self):
        pass

    def add_pendulum_y(self):
        pass

    def add_pendulum_x(self):
        pass

    def add_spiral(self):
        pass

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

    def close_all_curve_widgets(self):
        for cw in self.curves:
            cw.minimize(-1)

    def set_random_harmonograph(self):
        for p in self.curves:
            p.random()

    def process_shape(self):
        self.series.clear()
        step = self.degree_step / SLICES

        if step <= 0:
            step = 0.001

        time = 0
        while time < self.rotations:
            px = 0
            py = 0
            for p in self.curves:
                pdx, pdy = p.position(time)
                px += pdx
                py += pdy
            self.series.append((px,py))
            time += step

        shape_matrix = Matrix()
        shape_matrix.post_rotate(self.theta)
        shape_matrix.post_scale(self.scale, self.scale)
        shape_matrix.post_translate(self.x, self.y)
        # transform shape by matrix

    def remove_curver(self, c):
        self.curves.remove(c)
        self.process_shape()

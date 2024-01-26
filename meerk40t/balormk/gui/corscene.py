import time
from math import tau

import wx

from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    HITCHAIN_DELEGATE_AND_HIT,
    RESPONSE_CONSUME,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui import icons
from meerk40t.gui.icons import icons8_center_of_gravity
from meerk40t.gui.utilitywidgets.buttonwidget import ButtonWidget
from meerk40t.gui.scene.scenespacewidget import SceneSpaceWidget
from meerk40t.tools.geomstr import Geomstr
from meerk40t.tools.pmatrix import PMatrix


def cor_file_geometry(width=None):
    path = Geomstr()
    path.line(complex(0x17A5, 0x7FFF), complex(0xE859, 0x7FFF))
    path.line(complex(0x7FFF, 0x17A5), complex(0x7FFF, 0xE859))
    path.line(complex(0x8A3C, 0x9EB6), complex(0x8A3C, 0x75C2))

    path.line(complex(0x1999, 0x1999), complex(0xE665, 0x1999))
    path.line(complex(0xE665, 0x1999), complex(0xE665, 0xE665))
    path.line(complex(0xE665, 0xE665), complex(0x1999, 0xE665))
    path.line(complex(0x1999, 0xE665), complex(0x1999, 0x1999))

    path.line(complex(0x1EB7, 0xCCCC), complex(0x3331, 0xCCCC))
    path.line(complex(0x3331, 0xCCCC), complex(0x3331, 0xE146))
    path.line(complex(0x3331, 0xE146), complex(0x1EB7, 0xE146))
    path.line(complex(0x1EB7, 0xE146), complex(0x1EB7, 0xCCCC))

    path.line(complex(0xD709, 0x1EB7), complex(0xE146, 0x28F4))
    path.line(complex(0xE146, 0x28F4), complex(0xD709, 0x3331))
    path.line(complex(0xD709, 0x3331), complex(0xCCCC, 0x28F4))
    path.line(complex(0xCCCC, 0x28F4), complex(0xD709, 0x1EB7))
    return path


def setup_corfile_widget(service):
    scene = service.root.opened.get("Scene")

    scene.push_stack(SceneSpaceWidget(scene))
    corfile_widget = CorFileWidget(scene)
    scene.widget_root.scene_widget.add_widget(-1, corfile_widget)

    def confirm(**kwargs):
        scene.pop_stack()
        scene.request_refresh()

    def rotate_left(**kwargs):
        corfile_widget.rotate_left()
        scene.request_refresh()

    def rotate_right(**kwargs):
        corfile_widget.rotate_right()
        scene.request_refresh()

    def vflip(**kwargs):
        corfile_widget.vflip()
        scene.request_refresh()

    def hflip(**kwargs):
        corfile_widget.hflip()
        scene.request_refresh()

    size = 100
    scene.widget_root.interface_widget.add_widget(
        -1,
        ButtonWidget(
            scene,
            0,
            0,
            size,
            size,
            icons.icons8_delete.GetBitmap(use_theme=False),
            confirm,
        ),
    )
    scene.widget_root.interface_widget.add_widget(
        -1,
        ButtonWidget(
            scene,
            0,
            size * 2,
            size,
            size * 3,
            icons.icons8_rotate_left.GetBitmap(use_theme=False),
            rotate_left,
        ),
    )
    scene.widget_root.interface_widget.add_widget(
        -1,
        ButtonWidget(
            scene,
            0,
            size * 4,
            size,
            size * 5,
            icons.icons8_rotate_right.GetBitmap(use_theme=False),
            rotate_right,
        ),
    )
    scene.widget_root.interface_widget.add_widget(
        -1,
        ButtonWidget(
            scene,
            0,
            size * 6,
            size,
            size * 7,
            icons.icons8_flip_horizontal.GetBitmap(use_theme=False),
            hflip,
        ),
    )
    scene.widget_root.interface_widget.add_widget(
        -1,
        ButtonWidget(
            scene,
            0,
            size * 8,
            size,
            size * 9,
            icons.icons8_flip_vertical.GetBitmap(use_theme=False),
            vflip,
        ),
    )
    scene.widget_root.focus_viewport_scene((0, 0, 0xFFFF, 0xFFFF), scene.gui.Size)
    scene.request_refresh()


def register_scene(service):
    _ = service.kernel.translation

    service.register(
        "button/control/cor_file",
        {
            "label": _("cor_file"),
            "icon": icons8_center_of_gravity,
            "tip": _("Create CorFile"),
            "help": "devicebalor",
            "action": lambda v: service("widget_corfile\n"),
        },
    )

    @service.console_command(
        "widget_corfile",
        hidden=True,
        help=_("Update galvo flips for movement"),
    )
    def scene_corfile(**kwargs):
        setup_corfile_widget(service)


class CorFileWidget(Widget):
    """
    Widget for cor file creation routine.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.name = "Corfile"
        self.render = LaserRender(scene.context)
        self.geometry = cor_file_geometry()

        self.outline_pen = wx.Pen()
        self.outline_pen.SetColour(wx.BLACK)
        self.outline_pen.SetWidth(4)

        self.background_brush = wx.Brush()
        self.background_brush.SetColour(wx.WHITE)

        self.active_brush = wx.LIGHT_GREY_BRUSH

        self.hot_brush = wx.MEDIUM_GREY_BRUSH

        self.font_color = wx.Colour()
        self.font_color.SetRGBA(0xFF000000)
        self.font = wx.Font(wx.SWISS_FONT)

        self.text_height = float("inf")
        self.text_width = float("inf")

        self.mouse_location = None
        self.was_clicked = None

        self.active = None
        self.hot = None

        self.p1 = "50.0"
        self.p2 = "50.0"
        self.p3 = "50.0"
        self.p4 = "50.0"
        self.p5 = "50.0"
        self.p6 = "50.0"
        self.p7 = "50.0"
        self.p8 = "50.0"
        self.p9 = "50.0"
        self.p10 = "50.0"
        self.p11 = "50.0"
        self.p12 = "50.0"
        text_positions = (
            (21500, 5200, 5000, 1000, self, "p1"),
            (45000, 5200, 5000, 1000, self, "p2"),
            (60000, 20000, 5000, 1000, self, "p3"),
            (60000, 45000, 5000, 1000, self, "p4"),
            (45000, 60000, 5000, 1000, self, "p5"),
            (20000, 60000, 5000, 1000, self, "p6"),
            (5200, 45000, 5000, 1000, self, "p7"),
            (5200, 20000, 5000, 1000, self, "p8"),
            (20000, 32000, 5000, 1000, self, "p9"),
            (45000, 32000, 5000, 1000, self, "p10"),
            (32000, 20000, 5000, 1000, self, "p11"),
            (32000, 45000, 5000, 1000, self, "p12"),
        )
        self.text_fields = text_positions

    def _contains(self, location, x, y, width, height):
        if location is None:
            return
        if location[0] < x:
            return False
        if location[1] < y:
            return False
        if location[0] > (x + width):
            return False
        if location[1] > (y + height):
            return False
        return True

    def hit(self):
        return HITCHAIN_DELEGATE_AND_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        """
        Capture and deal with the double click event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type == "hover_start":
            self.scene.animate(self)
        if event_type in ("hover", "move"):
            self.mouse_location = space_pos
        if event_type == "leftdown":
            self.was_clicked = True
            print(space_pos)
        self.scene.request_refresh()
        return RESPONSE_CHAIN

    def rotate_left(self):
        matrix = PMatrix.rotate(tau / 4, 0x7FFF, 0x7FFF)
        self.geometry.transform3x3(matrix)

    def rotate_right(self):
        matrix = PMatrix.rotate(-tau / 4, 0x7FFF, 0x7FFF)
        self.geometry.transform3x3(matrix)

    def hflip(self):
        matrix = PMatrix.scale(-1, 1, 0x7FFF, 0x7FFF)
        self.geometry.transform3x3(matrix)

    def vflip(self):
        matrix = PMatrix.scale(1, -1, 0x7FFF, 0x7FFF)
        self.geometry.transform3x3(matrix)

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Draws the background on the scene.
        """
        unit_width = 0xFFFF
        unit_height = 0xFFFF
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawRectangle(0, 0, unit_width, unit_height)
        gc.SetPen(wx.BLACK_PEN)
        path = self.render.make_geomstr(gc, self.geometry)
        gc.DrawPath(path)

        if self.mouse_location:
            gc.DrawRectangle(self.mouse_location[0] - 500, self.mouse_location[1] - 500, 1000, 1000)
        gc.SetBrush(self.background_brush)
        gc.SetPen(self.outline_pen)
        was_hovered = False
        for i, textfield in enumerate(self.text_fields):
            x, y, width, height, obj, attr = textfield
            if self.hot == i:
                gc.SetBrush(self.hot_brush)
            elif self.active == i:
                gc.SetBrush(self.active_brush)
            else:
                gc.SetBrush(self.background_brush)
            gc.DrawRectangle(x, y, width, height)
            if self._contains(self.mouse_location, x, y, width, height):
                self.scene.cursor("text")
                was_hovered = True
                self.active = i
                if self.was_clicked:
                    self.hot = i
                    self.was_clicked = False
            if obj is None or not hasattr(obj, attr):
                continue

            text = getattr(obj, attr)
            if text is None:
                text = ""
            text_size = height * 3.0 / 4.0  # px to pt conversion
            try:
                self.font.SetFractionalPointSize(text_size)
            except AttributeError:
                self.font.SetPointSize(int(text_size))
            gc.SetFont(self.font, self.font_color)
            if self.active == i and int(time.time() * 2) % 2 == 0:
                text += "|"
            gc.DrawText(text, x, y)

        if not was_hovered:
            self.scene.cursor("arrow")

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        pass

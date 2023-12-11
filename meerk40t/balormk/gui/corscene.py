from math import tau

import wx

from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
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
            pass
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
        # brush = wx.Brush(colour=wx.WHITE, style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawRectangle(0, 0, unit_width, unit_height)
        gc.SetPen(wx.BLACK_PEN)
        path = self.render.make_geomstr(gc, self.geometry)
        gc.DrawPath(path)

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        pass

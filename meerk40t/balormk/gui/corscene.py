"""
The corfile widget is an immediate mode gui swap in for the regular scene. The intent is to allow the user to enter the
required values to generate a lmc corfile by entering the required distances and allowing the calculation of the
correction file.

The use of immediate mode gui system is to allow for in-place editing of the values with robust interactions between
the different widget elements. Such as the highlight and use of different text boxes, which deselects the other entries.
"""

import bisect
import time
from math import tau

import wx

from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    HITCHAIN_DELEGATE_AND_HIT,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui import icons
from meerk40t.gui.icons import icons8_center_of_gravity
from meerk40t.gui.scene.scenespacewidget import SceneSpaceWidget
from meerk40t.tools.geomstr import Geomstr
from meerk40t.tools.pmatrix import PMatrix


def cor_file_geometry(s=0x6666):
    path = Geomstr()
    m = 0x7FFF
    path.line(complex(0x17A5, m), complex(0xE859, m))
    path.line(complex(m, 0x17A5), complex(m, 0xE859))
    path.line(complex(0x8A3C, 0x9EB6), complex(0x8A3C, 0x75C2))

    path.line(complex(m - s, m - s), complex(m + s, m - s))
    path.line(complex(m + s, m - s), complex(m + s, m + s))
    path.line(complex(m + s, m + s), complex(m - s, m + s))
    path.line(complex(m - s, m + s), complex(m - s, m - s))

    path.line(complex(0x1EB7, 0xCCCC), complex(0x3331, 0xCCCC))
    path.line(complex(0x3331, 0xCCCC), complex(0x3331, 0xE146))
    path.line(complex(0x3331, 0xE146), complex(0x1EB7, 0xE146))
    path.line(complex(0x1EB7, 0xE146), complex(0x1EB7, 0xCCCC))

    path.line(complex(0xD709, 0x1EB7), complex(0xE146, 0x28F4))
    path.line(complex(0xE146, 0x28F4), complex(0xD709, 0x3331))
    path.line(complex(0xD709, 0x3331), complex(0xCCCC, 0x28F4))
    path.line(complex(0xCCCC, 0x28F4), complex(0xD709, 0x1EB7))
    return path


def cor_file_line_associated(s=0x6666):
    path = Geomstr()
    m = 0x7FFF
    path.line(complex(m - s, m - s), complex(m, m - s), settings=0)
    path.line(complex(m, m - s), complex(m + s, m - s), settings=1)

    path.line(complex(m + s, m - s), complex(m + s, m), settings=2)
    path.line(complex(m + s, m), complex(m + s, m + s), settings=3)

    path.line(complex(m + s, m + s), complex(m, m + s), settings=4)
    path.line(complex(m, m + s), complex(m - s, m + s), settings=5)

    path.line(complex(m - s, m + s), complex(m - s, m), settings=6)
    path.line(complex(m - s, m), complex(m - s, m - s), settings=7)

    path.line(complex(0x17A5, m), complex(m, m), settings=8)
    path.line(complex(m, m), complex(0xE859, m), settings=9)

    path.line(complex(m, 0x17A5), complex(m, m), settings=10)
    path.line(complex(m, m), complex(m, 0xE859), settings=11)
    return path


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
        scene = service.root.opened.get("Scene")

        scene.push_stack(SceneSpaceWidget(scene))
        corfile_widget = CorFileWidget(scene)
        scene.widget_root.scene_widget.add_widget(-1, corfile_widget)
        scene.widget_root.focus_viewport_scene((0, 0, 0xFFFF, 0xFFFF), scene.gui.Size)
        scene.request_refresh()


class CorFileWidget(Widget):
    """
    Widget for cor file creation routine.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.name = "Corfile"
        self.render = LaserRender(scene.context)
        self.geometry = cor_file_geometry()
        self.assoc = cor_file_line_associated()

        self.outline_pen = wx.Pen()
        self.outline_pen.SetColour(wx.BLACK)
        self.outline_pen.SetWidth(4)

        self.highlight_pen = wx.Pen()
        self.highlight_pen.SetColour(wx.BLUE)
        self.highlight_pen.SetWidth(200)

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
        self.typed = ""

        self.active = None
        self.hot = None

        self.cursor = -1
        self.is_opened = True
        dev = scene.context.device
        self.geometry_size = 0x6666
        self._geometry_size = self.geometry_size
        self.text_fields = (
            (21500, 5200, 5000, 1000, dev, "cf_1"),
            (45000, 5200, 5000, 1000, dev, "cf_2"),
            (60000, 20000, 5000, 1000, dev, "cf_3"),
            (60000, 45000, 5000, 1000, dev, "cf_4"),
            (45000, 60000, 5000, 1000, dev, "cf_5"),
            (20000, 60000, 5000, 1000, dev, "cf_6"),
            (5200, 45000, 5000, 1000, dev, "cf_7"),
            (5200, 20000, 5000, 1000, dev, "cf_8"),
            (20000, 32000, 5000, 1000, dev, "cf_9"),
            (45000, 32000, 5000, 1000, dev, "cf_10"),
            (32000, 20000, 5000, 1000, dev, "cf_11"),
            (32000, 45000, 5000, 1000, dev, "cf_12"),
            (0xFFFF - 5000, -2000, 5000, 1000, self, "geometry_size"),
        )

        self.button_fields = (
            (
                -3000,
                0,
                3000,
                3000,
                icons.icons8_delete.GetBitmap(use_theme=False),
                self.close,
            ),
            (
                -3000,
                3000,
                3000,
                3000,
                icons.icons8_rotate_left.GetBitmap(use_theme=False),
                self.rotate_left,
            ),
            (
                -3000,
                6000,
                3000,
                3000,
                icons.icons8_rotate_right.GetBitmap(use_theme=False),
                self.rotate_right,
            ),
            (
                -3000,
                9000,
                3000,
                3000,
                icons.icons8_flip_horizontal.GetBitmap(use_theme=False),
                self.hflip,
            ),
            (
                -3000,
                12000,
                3000,
                3000,
                icons.icons8_flip_vertical.GetBitmap(use_theme=False),
                self.vflip,
            ),
            (
                0xFFFF - 5000,
                -6000,
                3000,
                3000,
                icons.icons8_up.GetBitmap(use_theme=False),
                self.geometry_size_increase,
            ),
            (
                0xFFFF - 2000,
                -6000,
                3000,
                3000,
                icons.icons8_down.GetBitmap(use_theme=False),
                self.geometry_size_decrease,
            ),
        )
        self.scene.animate(self)

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

    def tick(self):
        self.scene.request_refresh()
        return self.is_opened

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        """
        Capture and deal with the double click event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type in ("hover", "move"):
            self.mouse_location = space_pos
        if event_type == "leftdown":
            self.was_clicked = True
        if event_type == "key_up":
            key = kwargs.get("keycode")
            if key:
                self.typed += key
            else:
                modifier = kwargs.get("modifiers")
                if modifier == "right":
                    self.cursor += 1
                elif modifier == "left":
                    self.cursor -= 1
                elif modifier == "tab":
                    self.cursor = -1
                    self.hot += 1
                    self.hot %= 12
                elif modifier == "shift+tab":
                    self.cursor = -1
                    self.hot += 11
                    self.hot %= 12

        return RESPONSE_CHAIN

    def close(self):
        self.scene.pop_stack()
        self.scene.request_refresh()
        self.is_opened = False

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

    def geometry_size_increase(self):
        self.geometry_size += 100

    def geometry_size_decrease(self):
        self.geometry_size -= 100

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Draws the background on the scene.
        """
        unit_width = 0xFFFF
        unit_height = 0xFFFF
        if self._geometry_size != self.geometry_size:
            self._geometry_size = self.geometry_size
            self.geometry = cor_file_geometry(self.geometry_size)
            self.assoc = cor_file_line_associated(self.geometry_size)
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawRectangle(0, 0, unit_width, unit_height)
        gc.SetPen(wx.BLACK_PEN)
        path = self.render.make_geomstr(gc, self.geometry)
        gc.DrawPath(path)

        if self.hot is not None and 0 <= self.hot < 12:
            gc.SetPen(self.highlight_pen)
            p2 = self.render.make_geomstr(gc, self.assoc, settings=self.hot)
            gc.DrawPath(p2)

        if self.mouse_location:
            gc.DrawRectangle(
                self.mouse_location[0] - 500, self.mouse_location[1] - 500, 1000, 1000
            )
        gc.SetBrush(self.background_brush)
        gc.SetPen(self.outline_pen)
        was_hovered = False
        index = -1
        for textfield in self.text_fields:
            index += 1
            x, y, width, height, obj, attr = textfield

            if self.hot == index:
                gc.SetBrush(self.background_brush)
            elif self.active == index:
                gc.SetBrush(self.active_brush)
            else:
                gc.SetBrush(self.hot_brush)
            gc.DrawRectangle(x, y, width, height)

            text = str(getattr(obj, attr))
            if text is None:
                text = ""
            text_size = height * 3.0 / 4.0  # px to pt conversion
            try:
                self.font.SetFractionalPointSize(text_size)
            except AttributeError:
                self.font.SetPointSize(int(text_size))
            gc.SetFont(self.font, self.font_color)

            if self._contains(self.mouse_location, x, y, width, height):
                self.scene.cursor("text")
                was_hovered = True
                self.active = index
                if self.was_clicked:
                    c_pos = gc.GetPartialTextExtents(text)
                    self.cursor = bisect.bisect(c_pos, (self.mouse_location[0] - x))
                    self.hot = index
                    self.was_clicked = False
            if obj is None or not hasattr(obj, attr):
                continue

            if self.hot == index and int(time.time() * 2) % 2 == 0:
                if self.typed:
                    for char in self.typed:
                        new_cursor = self.cursor
                        if char == "\x00":
                            new_cursor = len(text)
                        elif char == "\x08":
                            if self.cursor != 0:
                                text = text[: self.cursor - 1] + text[self.cursor :]
                                new_cursor -= 1
                        else:
                            text = text[: self.cursor] + char + text[self.cursor :]
                            new_cursor += 1
                        try:
                            setattr(obj, attr, float(text))
                        except ValueError:
                            continue
                        self.cursor = new_cursor
                    self.typed = ""
                if self.cursor > len(text) or self.cursor == -1:
                    self.cursor = len(text)
                c_pos = gc.GetPartialTextExtents(text)
                c_pos.insert(0, 0)
                gc.SetBrush(wx.BLACK_BRUSH)
                try:
                    cursor_pos = c_pos[self.cursor]
                except IndexError:
                    cursor_pos = 0
                gc.DrawRectangle(x + cursor_pos, y, 40, height)
            gc.DrawText(text, x, y)
        if not was_hovered:
            self.scene.cursor("arrow")

        for i, button in enumerate(self.button_fields):
            index += 1
            x, y, width, height, bmp, click = button
            if self.active == index:
                gc.SetBrush(self.background_brush)
                gc.DrawRectangle(x, y, width, height)
            gc.DrawBitmap(bmp, x, y, width, height)
            if self._contains(self.mouse_location, x, y, width, height):
                self.active = index
                was_hovered = True
                if self.was_clicked:
                    self.hot = index
                    self.was_clicked = False
                    click()
        if not was_hovered:
            self.active = None

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        pass

import wx

from meerk40t.gui import icons
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.scenespacewidget import SceneSpaceWidget
from meerk40t.gui.scene.widget import Widget


def register_widget_icon(context):
    _ = context.kernel.translation

    @context.console_command(
        "widget_icons",
        hidden=True,
        help=_("Show the icon scene widget"),
    )
    def scene_corfile(**kwargs):
        scene = context.root.opened.get("Scene")

        scene.push_stack(SceneSpaceWidget(scene))
        corfile_widget = IconsWidget(scene)
        scene.widget_root.scene_widget.add_widget(-1, corfile_widget)
        scene.widget_root.focus_viewport_scene((0, 0, 0xFFFF, 0xFFFF), scene.gui.Size)
        scene.request_refresh()


class IconsWidget(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.is_opened = True
        self.font_color = wx.Colour()
        self.font_color.SetRGBA(0xFF000000)
        self.font = wx.Font(wx.SWISS_FONT)
        self.background_brush = wx.Brush()
        self.background_brush.SetColour(wx.WHITE)

        self.mouse_location = None
        self.was_clicked = None
        self.active = None
        self.hot = None

        height = 1000
        text_size = height * 3.0 / 4.0  # px to pt conversion
        try:
            self.font.SetFractionalPointSize(text_size)
        except AttributeError:
            self.font.SetPointSize(int(text_size))
        self.icolist = []
        for icon in dir(icons):
            if icon.startswith("icon"):
                data = getattr(icons, icon)
                try:
                    bmp = data.GetBitmap(resize=100, use_theme=False)
                except AttributeError:
                    continue
                self.icolist.append((bmp, icon))
        self.button_fields = (
            (
                -3000,
                0,
                3000,
                3000,
                icons.icons8_delete.GetBitmap(use_theme=False),
                self.close,
            ),
        )
        self.scene.animate(self)

    def close(self):
        self.scene.pop_stack()
        self.scene.request_refresh()
        self.is_opened = False

    def _contains(self, location, x, y, width, height):
        if location is None:
            return False
        if location[0] < x:
            return False
        if location[1] < y:
            return False
        if location[0] > (x + width):
            return False
        if location[1] > (y + height):
            return False
        return True

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Draws the background on the scene.
        """
        index = 0
        was_hovered = False
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
        x = 0
        y = 0
        width = 1000
        height = 1000
        gc.SetFont(self.font, self.font_color)

        for bmp, icon_name in self.icolist:
            try:
                gc.DrawBitmap(bmp, x, y, width, height)
                gc.DrawText(icon_name, x + width, y)
                y += height
            except AttributeError:
                pass

    def hit(self):
        return HITCHAIN_HIT

    def tick(self):
        self.scene.request_refresh()
        return self.is_opened

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        **kwargs,
    ):
        """
        Capture and deal with the double click event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type in ("hover", "move"):
            self.mouse_location = space_pos
        if event_type == "leftdown":
            self.was_clicked = True

        return RESPONSE_CHAIN

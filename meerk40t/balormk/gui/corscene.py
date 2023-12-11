from meerk40t.gui.icons import (
            icon_balor_bounds,
            icon_balor_full,
            icon_balor_hull,
            icon_balor_regmarks,
            icons8_center_of_gravity,
            icons8_computer_support,
            icons8_connected,
            icons8_flash_off,
            icons8_flash_on,
            icons8_light_off,
            icons8_light_on,
        )
import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui import icons
from meerk40t.gui.scenewidgets.guidewidget import GuideWidget
from meerk40t.gui.utilitywidgets.buttonwidget import ButtonWidget


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
            from meerk40t.gui.scene.scenespacewidget import SceneSpaceWidget

            scene.push_stack(SceneSpaceWidget(scene))
            scene.widget_root.scene_widget.add_widget(-1, CorFileWidget(scene))

            def confirm(**kwargs):
                scene.pop_stack()
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
            scene.widget_root.focus_viewport_scene(
                (0, 0, 0xFFFF, 0xFFFF), scene.gui.Size
            )
            scene.request_refresh()


class CorFileWidget(Widget):
    """
    Widget for cor file creation routine.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.name = "Corfile"

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

    def process_draw(self, gc):
        """
        Draws the background on the scene.
        """
        unit_width = 0xFFFF
        unit_height = 0xFFFF
        # brush = wx.Brush(colour=wx.WHITE, style=wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(wx.GREEN_BRUSH)
        gc.DrawRectangle(0, 0, unit_width, unit_height)

    def signal(self, signal, *args, **kwargs):
        """
        Signal commands which draw the background and updates the grid when needed to recalculate the lines
        """
        pass

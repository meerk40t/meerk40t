import wx

from meerk40t.core.units import Length
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME

# from meerk40t.gui.toolwidgets.textentry import TextEntry
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Color, Matrix

_ = wx.GetTranslation


class LineTextTool(ToolWidget):
    """
    Text Drawing Tool

    Adds Vectortext at set location.
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.scene.context.setting(float, "last_font_size", float(Length("20px")))
        self.scene.context.setting(str, "last_font", "")
        self.last_node_created = None

    def process_draw(self, gc: wx.GraphicsContext):
        pass

    def end_tool(self, force=False):
        self.scene.context.signal("statusmsg", "")
        self.scene.request_refresh()
        if force or self.scene.context.just_a_single_element:
            self.scene.pane.tool_active = False
            self.scene.context("tool none\n")

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        response = RESPONSE_CHAIN
        self.scene.cursor("text")
        if event_type == "leftdown":
            if nearest_snap is None:
                x, y = self.scene.get_snap_point(space_pos[0], space_pos[1], modifiers)
            else:
                x = nearest_snap[0]
                y = nearest_snap[1]
            elements = self.scene.context.elements
            # if elements.default_stroke is None:
            #     text_color = Color("black")
            # else:
            #     text_color = elements.default_stroke
            text_content = "Text"
            fsize = self.scene.context.last_font_size
            font = self.scene.context.last_font
            if font:
                font = f'-f "{font}"'
            self.scene.context(f'linetext {x} {y} "{text_content}" {font} -s {fsize}\n')
            self.scene.context(".window open Properties\n")
            self.scene.context.signal("textselect")
            self.end_tool()
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape") or (event_type=="rightdown"):
            if self.scene.pane.tool_active:
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.end_tool(force=True)
        return response

    # @staticmethod
    # def sub_register(kernel):
    #     kernel.register("window/TextEntry", TextEntry)

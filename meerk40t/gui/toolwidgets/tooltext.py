import wx

from meerk40t.core.units import UNITS_PER_PIXEL
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME

# from meerk40t.gui.toolwidgets.textentry import TextEntry
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Color, Matrix

_ = wx.GetTranslation


class TextTool(ToolWidget):
    """
    Text Drawing Tool

    Adds Text at set location.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None

    def process_draw(self, gc: wx.GraphicsContext):
        pass

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
                x = space_pos[0]
                y = space_pos[1]
            else:
                x = nearest_snap[0]
                y = nearest_snap[1]
            ## self.scene.context(f"window open TextEntry {x} {y}\n")
            self.scene.context("tool none\n")
            node = self.scene.context.elements.elem_branch.add(
                text="Text",
                matrix=Matrix(f"translate({x}, {y}) scale({UNITS_PER_PIXEL})"),
                anchor="start",
                fill=Color("black"),
                type="elem text",
            )
            if self.scene.context.elements.classify_new:
                self.scene.context.elements.classify([node])
            self.notify_created(node)
            self.scene.context.elements.set_selected([node])
            activate = self.scene.context.kernel.lookup(
                "function/open_property_window_for_node"
            )
            if activate is not None:
                activate(node)
            self.scene.context.signal("selected")
            self.scene.context.signal("textselect", node)

            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.tool_active:
                self.scene.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        return response

    # @staticmethod
    # def sub_register(kernel):
    #     kernel.register("window/TextEntry", TextEntry)

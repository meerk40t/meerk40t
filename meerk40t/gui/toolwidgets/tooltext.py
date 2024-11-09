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

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.last_node_created = None

    def process_draw(self, gc: wx.GraphicsContext):
        pass

    def refocus_text(self):
        node = self.last_node_created
        if node is None:
            return
        self.scene.context.elements.set_emphasis([node])
        node.focus()

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
            ## self.scene.context(f"window open TextEntry {x} {y}\n")
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
            node.focus()
            activate = self.scene.context.kernel.lookup(
                "function/open_property_window_for_node"
            )
            if activate is not None:
                activate(node)
            node.focus()
            # self.scene.context.signal("selected")
            self.scene.context.signal("textselect", node)
            # The ugliest hack ever, somewhere the node gets defocussed,
            # so we are trying to bring it back after all the ruckus happened...
            self.last_node_created = node
            wx.CallLater(750, self.refocus_text)
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

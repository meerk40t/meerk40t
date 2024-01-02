from meerk40t.gui.scene.sceneconst import HITCHAIN_DELEGATE_AND_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scenewidgets.affinemover import AffineMover
from meerk40t.gui.scenewidgets.nodeselector import NodeSelector
from meerk40t.gui.scenewidgets.selectionwidget import SelectionWidget


class ToolContainer(Widget):
    """
    Widget used to contain particular tools within the scene.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self._active_tool = "unset"
        self._tool_mode = "unset"
        # Selection/Manipulation widget.
        self.mode = "selection"
        self.selection_widgets = {
            "selection": SelectionWidget(scene),
            "affine": AffineMover(scene),
            "vertex": NodeSelector(scene),
        }
        self.set_tool(None)

    def hit(self):
        return HITCHAIN_DELEGATE_AND_HIT

    def event(self, event_type=None, modifiers=None, **kwargs):
        if event_type == "key_up" and modifiers == "escape":
            self.set_tool(None)
        return RESPONSE_CHAIN

    def signal(self, signal, *args, **kwargs):
        if signal == "tool":
            tool = args[0]
            if len(args) > 1:
                mode = args[1]
            else:
                mode = None
            self.set_tool(tool, mode=mode)

    def set_tool(self, tool, mode=None):
        if self._active_tool == tool and self._tool_mode == mode:
            return True, f"Tool {tool} was already active"
        self._active_tool = tool
        self._tool_mode = mode
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.suppress_selection = False
        self.remove_all_widgets()
        if tool is not None:
            new_tool = self.scene.context.lookup("tool", tool)
            if new_tool is None:
                response = f"Such a tool is not defined: {tool}, leave unchanged"
                return False, response
            else:
                self.mode = getattr(new_tool, "select_mode", "selection")
                response = f"Tool set to {tool}, selection mode: {self.mode}"
        else:
            new_tool = None
            self.mode = "selection"
            response = "Tool set to selection mode"

        self.add_widget(widget=self.selection_widgets.get(self.mode))
        if new_tool is not None:
            self.add_widget(widget=new_tool(self.scene, mode=mode))

        self.scene.cursor("arrow")

        if tool is None:
            tool = "none"
        self.scene.pane.active_tool = tool.lower()

        message = ("tool", tool)

        self.scene.context.signal("tool_changed", message)

        self.scene._signal_widget(self.scene.widget_root, "tool_changed", message)

        self.scene.request_refresh()
        return True, response

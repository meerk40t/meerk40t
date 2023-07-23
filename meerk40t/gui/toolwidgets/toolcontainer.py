from meerk40t.gui.scene.sceneconst import HITCHAIN_DELEGATE_AND_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scenewidgets.affinemover import AffineMover
from meerk40t.gui.scenewidgets.nodeeditor import NodeEditor
from meerk40t.gui.scenewidgets.selectionwidget import SelectionWidget


class ToolContainer(Widget):
    """
    Widget used to contain particular tools within the scene.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self._active_tool = "unset"
        # Selection/Manipulation widget.
        self.mode = "selection"
        self.selection_widgets = {
            "selection": SelectionWidget(scene),
            "affine": AffineMover(scene),
            "vertex_editor": NodeEditor(scene),
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
            self.set_tool(tool)

    def set_tool(self, tool):
        if self._active_tool == tool:
            return
        self._active_tool = tool
        self.scene.pane.tool_active = False
        self.remove_all_widgets()
        if tool is not None:
            new_tool = self.scene.context.lookup("tool", tool)
            self.mode = getattr(new_tool, "select_mode", "selection")
        else:
            new_tool = None
            self.mode = "selection"

        self.add_widget(widget=self.selection_widgets.get(self.mode))
        if new_tool is not None:
            self.add_widget(widget=new_tool(self.scene))

        self.scene.cursor("arrow")

        if tool is None:
            tool = "none"
        self.scene.pane.active_tool = tool.lower()

        message = ("tool", tool)

        self.scene.context.signal("tool_changed", message)

        self.scene._signal_widget(self.scene.widget_root, "tool_changed", message)

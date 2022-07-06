from meerk40t.gui.scene.widget import Widget


class ToolContainer(Widget):
    """
    Widget used to contain particular tools within the scene.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)

    def signal(self, signal, *args, **kwargs):
        if signal == "tool":
            tool = args[0]
            self.set_tool(tool)

    def set_tool(self, tool):
        self.scene.tool_active = False
        self.remove_all_widgets()
        self.scene.cursor("arrow")
        if tool is not None:
            new_tool = self.scene.context.lookup("tool", tool)
            if new_tool is not None:
                self.add_widget(0, new_tool(self.scene))
        if tool is None:
            tool="none"
        message = ("tool", tool)
        self.scene.context.signal("tool_changed", message)

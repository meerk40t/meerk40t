import wx
from wx import aui
from wx.aui import EVT_AUITOOLBAR_TOOL_DROPDOWN

from meerk40t.kernel import lookup_listener

ID_ADD_FILE = wx.NewId()
ID_OPEN = wx.NewId()
ID_SAVE = wx.NewId()
ID_JOB = wx.NewId()
ID_SIM = wx.NewId()
ID_NOTES = wx.NewId()
ID_CONSOLE = wx.NewId()
ID_RASTER = wx.NewId()

_ = wx.GetTranslation


def register_toolbars(gui, context):
    tbm = ToolbarManager(gui, context)
    gui.add_module_delegate(tbm)
    i = 0
    for tb in tbm.toolbars:
        toolbar, caption = tbm.toolbars[tb]
        name = "{toolbar}_toolbar".format(toolbar=tb)
        width = toolbar.ToolCount * 58
        pane = (
            aui.AuiPaneInfo()
            .Name(name)
            .Top()
            .ToolbarPane()
            .FloatingSize(width, 58)
            .Layer(1)
            .Position(i)
            .Caption(caption)
            .CaptionVisible(not context.pane_lock)
            .Hide()
        )
        toolbar.SetToolBitmapSize(wx.Size(16, 16))
        i += 1
        pane.control = toolbar
        toolbar.pane = pane
        pane.submenu = _("Toolbars")
        gui.on_pane_add(pane)
        context.register("pane/{name}".format(name=name), pane)


class ToolbarManager:
    def __init__(self, gui, context):
        self.gui = gui
        self.context = context
        self.toolbars = {
            "project": (aui.AuiToolBar(self.gui), _("Project")),
            "control": (aui.AuiToolBar(self.gui), _("Control")),
            "configuration": (aui.AuiToolBar(self.gui), _("Configuration")),
            "modify": (aui.AuiToolBar(self.gui), _("Modification")),
        }

    def module_open(self):
        self.set_project(self.context.find("button/project"))
        self.set_control(self.context.find("button/control"))
        self.set_config(self.context.find("button/config"))
        self.set_modify(self.context.find("button/modify"))

    @lookup_listener("button/control")
    def set_control(self, new_values, old_values=None):
        toolbar, caption = self.toolbars["control"]
        ToolbarManager.set_buttons(new_values, self.gui, toolbar)
        width = toolbar.ToolCount * 58
        toolbar.pane.BestSize((width, -1))
        toolbar.pane.MinSize((width, -1))
        toolbar.pane.MaxSize((width, -1))
        toolbar.Realize()
        self.gui._mgr.Update()

    @lookup_listener("button/project")
    def set_project(self, new_values, old_values=None):
        toolbar, caption = self.toolbars["project"]
        ToolbarManager.set_buttons(new_values, self.gui, toolbar)
        width = toolbar.ToolCount * 58
        toolbar.pane.BestSize((width, -1))
        toolbar.pane.MinSize((width, -1))
        toolbar.pane.MaxSize((width, -1))
        toolbar.Realize()
        self.gui._mgr.Update()

    @lookup_listener("button/config")
    def set_config(self, new_values, old_values=None):
        toolbar, caption = self.toolbars["configuration"]
        ToolbarManager.set_buttons(new_values, self.gui, toolbar)
        width = toolbar.ToolCount * 58
        toolbar.pane.BestSize((width, -1))
        toolbar.pane.MinSize((width, -1))
        toolbar.pane.MaxSize((width, -1))
        toolbar.Realize()
        self.gui._mgr.Update()

    @lookup_listener("button/modify")
    def set_modify(self, new_values, old_values=None):
        toolbar, caption = self.toolbars["modify"]
        ToolbarManager.set_buttons(new_values, self.gui, toolbar)
        width = toolbar.ToolCount * 58
        toolbar.pane.BestSize((width, -1))
        toolbar.pane.MinSize((width, -1))
        toolbar.pane.MaxSize((width, -1))
        toolbar.Realize()
        self.gui._mgr.Update()

    @staticmethod
    def set_buttons(new_values, gui, button_bar: aui.AuiToolBar):
        button_bar.ClearTools()
        buttons = []
        for button, name, sname in new_values:
            buttons.append(button)

        def sort_priority(elem):
            return elem["priority"] if "priority" in elem else 0

        buttons.sort(key=sort_priority)

        for button in buttons:
            new_id = wx.NewId()
            button_bar.AddTool(
                new_id,
                button["label"],
                button["icon"].GetBitmap(),
                kind=wx.ITEM_NORMAL,
                short_help_string=button["tip"],
            )
            if "alt-action" in button:
                def on_click(action):
                    def specific(event=None):
                        print(event)
                        action()

                    return specific

                def on_dropdown(b):
                    def specific(event=None):
                        if event.IsDropDownClicked():
                            menu = wx.Menu()
                            for act_label, act_func in b["alt-action"]:
                                opt_id = wx.NewId()
                                menu.Append(opt_id, act_label)
                                button_bar.Bind(wx.EVT_MENU, on_click(act_func), id=opt_id)
                            gui.PopupMenu(menu)
                        else:
                            b["action"]()
                        button_bar.SetToolSticky(event.GetId(), False)
                    return specific

                button_bar.SetToolDropDown(new_id, True)
                button_bar.Bind(
                    EVT_AUITOOLBAR_TOOL_DROPDOWN,
                    on_dropdown(button),
                    id=new_id,
                )
            else:
                button_bar.Bind(
                    wx.EVT_TOOL,
                    button["action"],
                    id=new_id,
                )

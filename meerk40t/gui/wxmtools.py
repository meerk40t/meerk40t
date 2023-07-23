"""
The WxmRibbon Bar is a core aspect of MeerK40t's interaction. To allow fully dynamic buttons we use the ribbonbar
control widget built into meerk40t.

Panels are created in a static fashion within this class. But the contents of those individual ribbon panels are defined
in the kernel lookup.

    service.register(
        "button/control/Redlight",
        {
            ...<def>...
        },
    )

This setup allows us to define a large series of buttons with a button prefix and the name of a panel it should be
added to as well as a unique name. This defines within the meerk40t ecosystem a methodology of specifically creating
dynamic buttons. When the service changes because of a switch in the device (for example) it will trigger the lookup
listeners which will update their contents, triggering the update within this control.
"""

import wx
from wx import aui

from meerk40t.kernel import Job, lookup_listener, signal_listener

from .icons import get_default_icon_size, icons8_opened_folder_50
from .ribbon import RibbonBarPanel

_ = wx.GetTranslation

ID_PAGE_TOOLS = 20


def register_panel_tools(window, context):
    iconsize = get_default_icon_size()
    minh = 1 * iconsize
    pane = (
        aui.AuiPaneInfo()
        .Name("tools")
        .Left()
        .BestSize(minh, 300)
        .FloatingSize(minh, 640)
        .Caption(_("Tools"))
        .CaptionVisible(not context.pane_lock)
    )
    pane.dock_proportion = 640
    ribbon = MKToolbarPanel(window, wx.ID_ANY, context=context, pane=pane)
    pane.control = ribbon

    window.on_pane_create(pane)
    context.register("pane/tools", pane)


class MKToolbarPanel(RibbonBarPanel):
    def __init__(self, parent, id, context=None, pane=None, **kwds):
        RibbonBarPanel.__init__(self, parent, id, context, **kwds)
        self.art.orientation = self.art.RIBBON_ORIENTATION_AUTO
        self.art.show_labels = False
        self.pane = pane
        # Define Ribbon.
        self.__set_ribbonbar()

    @lookup_listener("button/tool")
    def set_tool_buttons(self, new_values, old_values):
        self.tools.tool.set_buttons(new_values)

    @lookup_listener("button/extended_tools")
    def set_tool_extended_buttons(self, new_values, old_values):
        self.tools.extended.set_buttons(new_values)

    @lookup_listener("button/group")
    def set_group_buttons(self, new_values, old_values):
        self.tools.group.set_buttons(new_values)

    @signal_listener("emphasized")
    def on_emphasis_change(self, origin, *args):
        self.apply_enable_rules()

    @signal_listener("selected")
    def on_selected_change(self, origin, node=None, *args):
        self.apply_enable_rules()

    @signal_listener("icons")
    def on_requested_change(self, origin, node=None, *args):
        self.apply_enable_rules()
        self.modified()

    @signal_listener("tool_changed")
    def on_tool_changed(self, origin, newtool=None, *args):
        # Signal provides a tuple with (togglegroup, id)
        if newtool is None:
            return
        if isinstance(newtool, (list, tuple)):
            group = newtool[0].lower() if newtool[0] is not None else ""
            identifier = newtool[1].lower() if newtool[1] is not None else ""
        else:
            group = newtool
            identifier = ""

        for page in self.pages:
            for panel in page.panels:
                for button in panel.buttons:
                    if button.group != group:
                        continue
                    button.set_button_toggle(button.identifier == identifier)
        self.apply_enable_rules()
        self.modified()

    def __set_ribbonbar(self):
        """
        GUI Specific creation of ribbonbar.
        @return:
        """

        self.add_page(
            "tools",
            ID_PAGE_TOOLS,
            _("Tools"),
            icons8_opened_folder_50.GetBitmap(resize=16),
        )

        self.add_panel(
            "tool",
            parent=self.tools,
            id=wx.ID_ANY,
            label=_("Design"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "group",
            parent=self.tools,
            id=wx.ID_ANY,
            label=_("Group"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )

        self.add_panel(
            "extended",
            parent=self.tools,
            id=wx.ID_ANY,
            label=_("Extended Tools"),
            icon=icons8_opened_folder_50.GetBitmap(),
        )
        self.modified()

    def pane_show(self):
        pass

    def pane_hide(self):
        """
        On pane_hide all the listeners are disabled.
        @return:
        """
        for page in self.pages:
            for panel in page.panels:
                for key, listener in panel._registered_signals:
                    self.context.unlisten(key, listener)

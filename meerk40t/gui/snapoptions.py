import wx
from wx import aui
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel

_ = wx.GetTranslation


def register_panel_snapoptions(window, context):
    panel = SnapOptionPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .MinSize(80, 125)
        .FloatingSize(120, 145)
        .Hide()
        .Caption(_("Snap-Options"))
        .CaptionVisible(not context.pane_lock)
        .Name("snapoptions")
    )
    pane.dock_proportion = 150
    pane.control = panel
    pane.submenu = "_40_" + _("Editing")
    pane.helptext = _("Edit element movement snap options")

    window.on_pane_create(pane)
    context.register("pane/snapoptions", pane)


class SnapOptionPanel(wx.Panel):

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("snap")
        all_choices = self.context.lookup("choices", "preferences")
        choices = [c for c in all_choices if c.get("section", "") == "Snap-Options" and c.get("relevant", False) ]
        # Simplify choice dicts for panel
        for c in choices:
            c["page"] = ""
            c["section"] = "" 
            c["subsection"] = ""
        # Combine chocices into a subsection
        # _("Attraction"), _("Sensitivity"), _("Options")
        for (sect, atts) in (
            ("Attraction", ("snap_points", "snap_grid")),
            ("Sensitivity", ("action_attract_len", "grid_attract_len")),
            ("Options", ("snap_instant", "snap_preview")),
        ):
            for c in choices:
                if c.get("attr", "") in atts:
                    c["subsection"] = sect

        self.options = ChoicePropertyPanel(self, wx.ID_ANY, context=context, choices=choices)    

        # Main Sizer
        sizer_snap = wx.BoxSizer(wx.VERTICAL)
        sizer_snap.Add(self.options, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_snap)   


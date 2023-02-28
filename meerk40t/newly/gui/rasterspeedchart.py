import wx
import wx.lib.mixins.listctrl as listmix

from meerk40t.gui.icons import icons8_connected_50
from meerk40t.gui.mwindow import MWindow, _


class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    """TextEditMixin allows any column to be edited."""

    # ----------------------------------------------------------------------
    def __init__(
        self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0
    ):
        """Constructor"""
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)


class RasterSpeedChart(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: RasterSpeedChart.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        self.context = context
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        self.list_chart = EditableListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_chart.AppendColumn("Speed <=", format=wx.LIST_FORMAT_LEFT, width=133)
        self.list_chart.AppendColumn("Acceleration Length", format=wx.LIST_FORMAT_LEFT, width=244)
        self.list_chart.AppendColumn("Backlash", format=wx.LIST_FORMAT_LEFT, width=142)
        self.list_chart.AppendColumn("Corner Speed", format=wx.LIST_FORMAT_LEFT, width=128)
        sizer_main.Add(self.list_chart, 10, wx.EXPAND, 0)

        self.panel_control = wx.Panel(self, wx.ID_ANY)
        sizer_main.Add(self.panel_control, 1, wx.EXPAND, 0)

        sizer_control = wx.BoxSizer(wx.HORIZONTAL)

        self.button_add = wx.Button(self.panel_control, wx.ID_ANY, "Add")
        sizer_control.Add(self.button_add, 0, 0, 0)

        self.button_remove = wx.Button(self.panel_control, wx.ID_ANY, "Remove")
        sizer_control.Add(self.button_remove, 0, 0, 0)

        self.panel_control.SetSizer(sizer_control)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.Layout()

        self.list_chart.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_chart
        )
        self.list_chart.Bind(
            wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_item_label_edit
        )
        self.list_chart.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_chart_update)
        # end wxGlade

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_item_label_edit(self, event):
        list_id = event.GetIndex()  # Get the current row
        col_id = event.GetColumn()  # Get the current column
        if col_id >= 0:
            event.Allow()
        else:
            event.Veto()

    def on_chart_update(self, event):
        list_id = event.GetIndex()  # Get the current row
        col_id = event.GetColumn()  # Get the current column
        new_data = event.GetLabel()  # Get the changed data
        if list_id >= 0 and col_id >= 0:
            idx = self.list_chart.GetItemData(list_id)
            key = idx
            # Set the new data in the listctrl
            self.list_chart.SetItem(list_id, col_id, new_data)

    def on_item_selected(self, event=None):
        print(event)

    def on_item_rightclick(self, event=None):
        print(event)


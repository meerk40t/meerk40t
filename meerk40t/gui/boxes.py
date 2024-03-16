from math import atan2, sqrt

import numpy as np
import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.core.node.node import Node

from ..core.units import Length
from ..gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxRadioBox,
)
from ..kernel import signal_listener
from .icons import STD_ICON_SIZE, get_default_icon_size, icons8_arrange
from .mwindow import MWindow

_ = wx.GetTranslation


class BoxPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_main_h = wx.BoxSizer(wx.HORIZONTAL)

        sizer_left_v = wx.BoxSizer(wx.VERTICAL)

        sizer_dim_outer = StaticBoxSizer(
            self, wx.ID_ANY, _("Outer Dimensions"), wx.VERTICAL
        )

        sizer_x = wx.BoxSizer(wx.HORIZONTAL)

        self.label_x = wx.StaticText(self, wx.ID_ANY, _("Width"))
        self.label_x.SetMinSize(wx.Size(120, -1))

        sizer_x.Add(self.label_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_outer_x = wx.TextCtrl(self, wx.ID_ANY)
        self.text_outer_x.SetToolTip(_("The total width of your box"))

        sizer_x.Add(self.text_outer_x, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_dim_outer.Add(sizer_x, 0, wx.EXPAND, 0)

        sizer_y = wx.BoxSizer(wx.HORIZONTAL)

        self.label_y = wx.StaticText(self, wx.ID_ANY, _("Length"))
        self.label_y.SetMinSize(wx.Size(120, -1))

        sizer_y.Add(self.label_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_outer_y = wx.TextCtrl(self, wx.ID_ANY)
        self.text_outer_y.SetToolTip(_("The total length of your box"))

        sizer_y.Add(self.text_outer_y, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_dim_outer.Add(sizer_y, 0, wx.EXPAND, 0)

        sizer_z = wx.BoxSizer(wx.HORIZONTAL)

        self.label_z = wx.StaticText(self, wx.ID_ANY, _("Height"))
        self.label_z.SetMinSize(wx.Size(120, -1))

        sizer_z.Add(self.label_z, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_outer_z = wx.TextCtrl(
            self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0
        )
        self.text_outer_z.SetToolTip(_("The height of the box"))

        sizer_z.Add(self.text_outer_z, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_dim_outer.Add(sizer_z, 1, wx.EXPAND, 0)

        sizer_left_v.Add(sizer_dim_outer, 0, wx.EXPAND, 0)

        sizer_material = StaticBoxSizer(self, wx.ID_ANY, _("Material"), wx.VERTICAL)

        sizer_thick = wx.BoxSizer(wx.HORIZONTAL)

        self.label_thick = wx.StaticText(self, wx.ID_ANY, _("Thickness"))
        self.label_thick.SetMinSize(wx.Size(120, -1))

        sizer_thick.Add(self.label_thick, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_thickness = wx.TextCtrl(self, wx.ID_ANY)
        self.text_thickness.SetToolTip(_("The thickness of the material"))

        sizer_thick.Add(self.text_thickness, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_material.Add(sizer_thick, 0, wx.EXPAND, 0)

        sizer_fingerjoint = wx.BoxSizer(wx.HORIZONTAL)

        self.label_joint = wx.StaticText(self, wx.ID_ANY, _("Tab length"))
        self.label_joint.SetMinSize(wx.Size(120, -1))

        sizer_fingerjoint.Add(self.label_joint, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_joint = wx.TextCtrl(self, wx.ID_ANY)
        self.text_joint.SetToolTip(_("The thickness of the material"))

        sizer_fingerjoint.Add(self.text_joint, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_material.Add(sizer_fingerjoint, 1, wx.EXPAND, 0)

        sizer_kerf = wx.BoxSizer(wx.HORIZONTAL)

        self.label_kerf = wx.StaticText(self, wx.ID_ANY, _("Kerf"))
        self.label_kerf.SetMinSize(wx.Size(120, -1))

        sizer_kerf.Add(self.label_kerf, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_kerf = wx.TextCtrl(self, wx.ID_ANY)
        self.text_kerf.SetToolTip(_("Kerf tooltip TODO"))

        sizer_kerf.Add(self.text_kerf, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_material.Add(sizer_kerf, 0, wx.EXPAND, 0)

        sizer_left_v.Add(sizer_material, 0, wx.EXPAND, 0)

        sizer_interior = StaticBoxSizer(self, wx.ID_ANY, _("Interior"), wx.VERTICAL)

        sizer_columns = wx.BoxSizer(wx.HORIZONTAL)

        self.label_columns = wx.StaticText(self, wx.ID_ANY, _("Columns"))
        self.label_columns.SetMinSize(wx.Size(120, -1))

        sizer_columns.Add(self.label_columns, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_columns = wx.TextCtrl(self, wx.ID_ANY)
        self.text_columns.SetToolTip(_("Number of columns"))

        sizer_columns.Add(self.text_columns, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_interior.Add(sizer_columns, 0, wx.EXPAND, 0)

        sizer_rows = wx.BoxSizer(wx.HORIZONTAL)

        self.label_rows = wx.StaticText(self, wx.ID_ANY, _("Rows"))
        self.label_rows.SetMinSize(wx.Size(120, -1))

        sizer_rows.Add(self.label_rows, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_rows = wx.TextCtrl(self, wx.ID_ANY)
        self.text_rows.SetToolTip(_("Number of rows"))

        sizer_rows.Add(self.text_rows, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_interior.Add(sizer_rows, 1, wx.EXPAND, 0)

        sizer_left_v.Add(sizer_interior, 0, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_create = wx.Button(self, wx.ID_ANY, _("Create"))
        sizer_buttons.Add(self.btn_create, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_close = wx.Button(self, wx.ID_ANY, _("Close"))
        sizer_buttons.Add(self.btn_close, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_left_v.Add(sizer_buttons, 0, wx.EXPAND, 0)

        sizer_main_h.Add(sizer_left_v, 0, wx.EXPAND, 0)

        self.panel_preview = wx.Panel(self, wx.ID_ANY)
        sizer_main_h.Add(self.panel_preview, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main_h)
        self.Layout()


class BoxGenerator(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(
            360,
            485,
            *args,
            style=wx.CAPTION
            | wx.CLOSE_BOX
            | wx.FRAME_FLOAT_ON_PARENT
            | wx.TAB_TRAVERSAL
            | wx.RESIZE_BORDER,
            **kwds,
        )
        self.panel_boxes = BoxPanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel_boxes, 1, wx.EXPAND, 0)
        # self.add_module_delegate(self.panel_boxes)
        self.Layout()

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_arrange.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Alignment"))

    def delegates(self):
        yield self.panel_boxes

    @staticmethod
    def sub_register(kernel):
        buttonsize = STD_ICON_SIZE

    def window_open(self):
        pass

    def window_close(self):
        pass

    @staticmethod
    def submenu():
        return "Laser-Tools", "Box Generator"

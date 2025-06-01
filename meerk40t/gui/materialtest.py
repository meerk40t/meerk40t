from copy import copy
from math import tau

import wx
from wx import aui

from meerk40t.core.node.effect_hatch import HatchEffectNode
from meerk40t.core.node.effect_wobble import WobbleEffectNode
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.units import UNITS_PER_PIXEL, Angle, Length
from meerk40t.gui.icons import get_default_icon_size, icons8_detective
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxCheckListBox,
    wxComboBox,
    wxListBox,
    wxStaticText,
)
from meerk40t.kernel import Settings, lookup_listener, signal_listener
from meerk40t.svgelements import Color, Matrix

_ = wx.GetTranslation


class SaveLoadPanel(wx.Panel):
    """
    Provides the scaffold for saving and loading of parameter sets.
    Does not know a lot about the underlying structure of data as it
    blindly interacts with the parent via the callback routine
    (could hence work as a generic way to save / load data)
    """

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.callback = None
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer_main)
        sizer_name = wx.BoxSizer(wx.HORIZONTAL)
        lbl_info = wxStaticText(self, wx.ID_ANY, _("Template-Name"))
        self.txt_name = TextCtrl(self, wx.ID_ANY, "")
        self.btn_save = wxButton(self, wx.ID_ANY, _("Save"))
        self.btn_load = wxButton(self, wx.ID_ANY, _("Load"))
        self.btn_delete = wxButton(self, wx.ID_ANY, _("Delete"))
        self.btn_load.Enable(False)
        self.btn_save.Enable(False)
        self.btn_delete.Enable(False)
        sizer_name.Add(lbl_info, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_name.Add(self.txt_name, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_name.Add(self.btn_save, 0, wx.EXPAND, 0)
        sizer_name.Add(self.btn_load, 0, wx.EXPAND, 0)
        sizer_name.Add(self.btn_delete, 0, wx.EXPAND, 0)

        self.choices = []
        self.list_slots = wxListBox(
            self, wx.ID_ANY, choices=self.choices, style=wx.LB_SINGLE
        )
        self.list_slots.SetToolTip(_("Select an entry to reload"))
        sizer_main.Add(sizer_name, 0, wx.EXPAND, 0)
        sizer_main.Add(self.list_slots, 1, wx.EXPAND, 0)
        self.Layout()
        self.Bind(wx.EVT_TEXT, self.on_text_change, self.txt_name)
        self.Bind(wx.EVT_BUTTON, self.on_btn_load, self.btn_load)
        self.Bind(wx.EVT_BUTTON, self.on_btn_save, self.btn_save)
        self.Bind(wx.EVT_BUTTON, self.on_btn_delete, self.btn_delete)
        self.list_slots.Bind(wx.EVT_LISTBOX, self.on_listbox_click)
        self.list_slots.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_double_click)

    def set_callback(self, routine):
        self.callback = routine
        self.fill_choices("")

    def standardize(self, text):
        text = text.lower()
        for invalid in (
            "=",
            ":",
        ):
            text = text.replace(invalid, "_")
        return text

    def fill_choices(self, txt):
        self.choices = []
        if self.callback is not None:
            self.choices = self.callback("get", "")

        self.list_slots.Clear()
        self.list_slots.SetItems(self.choices)
        if txt:
            try:
                idx = self.choices.index(txt)
            except ValueError:
                idx = -1
            if idx >= 0:
                self.list_slots.SetSelection(idx)
        self.list_slots.Refresh()

    def on_text_change(self, event):
        info = self.txt_name.GetValue()
        flag1 = False
        flag2 = False
        if info:
            info = self.standardize(info)
            flag2 = True
            try:
                idx = self.choices.index(info)
            except ValueError:
                idx = -1
            flag1 = idx >= 0
        self.btn_load.Enable(flag1)
        self.btn_delete.Enable(flag1)
        self.btn_save.Enable(flag2)

    def on_btn_load(self, event):
        info = self.txt_name.GetValue()
        if self.callback is None or not info:
            return
        info = self.standardize(info)
        __ = self.callback("load", info)

    def on_btn_delete(self, event):
        info = self.txt_name.GetValue()
        if self.callback is None or not info:
            return
        info = self.standardize(info)
        __ = self.callback("delete", info)
        self.fill_choices("")

    def on_btn_save(self, event):
        info = self.txt_name.GetValue()
        if self.callback is None or not info:
            return
        info = self.standardize(info)
        __ = self.callback("save", info)
        self.fill_choices(info)
        self.on_text_change(None)

    def on_listbox_click(self, event):
        idx = self.list_slots.GetSelection()
        # print (f"Click with {idx}")
        if idx >= 0:
            info = self.choices[idx]
            self.txt_name.SetValue(info)
        self.on_text_change(None)

    def on_listbox_double_click(self, event):
        idx = self.list_slots.GetSelection()
        # print (f"DClick with {idx}")
        if idx >= 0:
            info = self.choices[idx]
            self.txt_name.SetValue(info)
            self.on_btn_load(None)
        self.on_text_change(None)


class TemplatePanel(wx.Panel):
    """
    Responsible for the generation of testpatterns and the user interface
    params:
    context - the current context
    storage - an instance of kernel.Settings to store/load parameter sets
    """

    def __init__(self, *args, context=None, storage=None, **kwds):
        def size_it(ctrl, value):
            ctrl.SetMaxSize(dip_size(self, int(value), -1))
            ctrl.SetMinSize(dip_size(self, int(value * 0.75), -1))
            ctrl.SetSize(dip_size(self, value, -1))

        # begin wxGlade: clsLasertools.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("testpattern")
        self.storage = storage
        self.callback = None
        self.current_op = None
        opchoices = [
            _("Cut"),
            _("Engrave"),
            _("Raster"),
            _("Image"),
            _("Hatch"),
            _("Wobble"),
        ]
        # Setup 5 Op nodes - they aren't saved yet
        self.default_op = []
        self.secondary_default_op = []
        # A tuple defining whether a free color-selection scheme is allowed, linked to default_op
        self.color_scheme_free = []
        self.default_op.append(CutOpNode())
        self.secondary_default_op.append(None)
        self.color_scheme_free.append(True)

        self.default_op.append(EngraveOpNode())
        self.color_scheme_free.append(True)
        self.secondary_default_op.append(None)

        self.default_op.append(RasterOpNode())
        self.color_scheme_free.append(False)
        self.secondary_default_op.append(None)

        self.default_op.append(ImageOpNode())
        self.color_scheme_free.append(True)
        self.secondary_default_op.append(None)

        # Hatch = Engrave
        op = EngraveOpNode()
        self.default_op.append(op)
        self.secondary_default_op.append(HatchEffectNode())
        self.color_scheme_free.append(True)

        # Wobble = Cut
        op = CutOpNode()
        self.default_op.append(op)
        self.secondary_default_op.append(WobbleEffectNode())
        self.color_scheme_free.append(True)

        self.use_image = [False] * len(self.default_op)
        self.use_image[3] = True

        self._freecolor = True

        self.parameters = []
        color_choices = [_("Red"), _("Green"), _("Blue")]

        LABEL_WIDTH = 115

        self.combo_ops = wxComboBox(
            self, id=wx.ID_ANY, choices=opchoices, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.images = []
        self.image_labels = []
        self.image_labels.append(_("Choose image..."))

        for node in self.context.elements.elems():
            if node.type == "elem image":
                imagenode = copy(node)
                bb = imagenode.bounds
                if bb is not None:
                    # Put it back on origin
                    imagenode.matrix.post_translate(-bb[0], -bb[1])
                self.images.append(imagenode)
                w, h = imagenode.active_image.size
                label = f"{w} x {h} Pixel"
                if node.label:
                    label += "(" + node.display_label() + ")"
                self.image_labels.append(label)

        self.combo_images = wxComboBox(
            self,
            id=wx.ID_ANY,
            choices=self.image_labels,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_images.SetToolTip(
            _(
                "Choose from one of the existing images on your canvas to use as the test template"
            )
        )
        self.combo_images.SetSelection(0)
        self.check_labels = wxCheckBox(self, wx.ID_ANY, _("Labels"))
        self.check_values = wxCheckBox(self, wx.ID_ANY, _("Values"))

        self.combo_param_1 = wxComboBox(
            self, id=wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.spin_count_1 = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=100)
        self.text_min_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_max_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_1.set_range(0, 50)
        self.text_delta_1 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_delta_1.set_range(0, 50)
        self.list_options_1 = wxCheckListBox(
            self, wx.ID_ANY, label=_("Pick values"), majorDimension=3
        )

        self.unit_param_1a = wxStaticText(self, wx.ID_ANY, "")
        self.unit_param_1b = wxStaticText(self, wx.ID_ANY, "")

        self.combo_color_1 = wxComboBox(
            self,
            wx.ID_ANY,
            choices=color_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.check_color_direction_1 = wxCheckBox(self, wx.ID_ANY, _("Growing"))

        self.combo_param_2 = wxComboBox(
            self, id=wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.spin_count_2 = wx.SpinCtrl(self, wx.ID_ANY, initial=5, min=1, max=100)
        self.text_min_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_max_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_dim_2.set_range(0, 50)
        self.list_options_2 = wxCheckListBox(
            self, wx.ID_ANY, label=_("Pick values"), majorDimension=3
        )
        self.text_delta_2 = TextCtrl(self, wx.ID_ANY, limited=True, check="float")
        self.text_delta_2.set_range(0, 50)
        self.unit_param_2a = wxStaticText(self, wx.ID_ANY, "")
        self.unit_param_2b = wxStaticText(self, wx.ID_ANY, "")

        self.combo_color_2 = wxComboBox(
            self,
            wx.ID_ANY,
            choices=color_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.check_color_direction_2 = wxCheckBox(self, wx.ID_ANY, _("Growing"))

        self.button_create = wxButton(self, wx.ID_ANY, _("Create Pattern"))
        self.button_create.SetBitmap(
            icons8_detective.GetBitmap(resize=0.5 * get_default_icon_size(self.context))
        )

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_param_optype = wx.BoxSizer(wx.HORIZONTAL)

        self.sizer_param_op = StaticBoxSizer(
            self, wx.ID_ANY, _("Operation to test"), wx.VERTICAL
        )
        mylbl = wxStaticText(self, wx.ID_ANY, _("Operation:"))
        size_it(mylbl, LABEL_WIDTH)
        h1 = wx.BoxSizer(wx.HORIZONTAL)
        h1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        h1.Add(self.combo_ops, 1, wx.EXPAND, 0)
        self.sizer_param_op.Add(h1, 0, wx.EXPAND, 0)
        self.sizer_param_op.Add(self.combo_images, 0, wx.EXPAND, 0)

        sizer_param_check = StaticBoxSizer(
            self, wx.ID_ANY, _("Show Labels / Values"), wx.HORIZONTAL
        )
        sizer_param_check.Add(self.check_labels, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_param_check.Add(self.check_values, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_param_optype.Add(self.sizer_param_op, 1, wx.EXPAND, 0)
        sizer_param_optype.Add(sizer_param_check, 1, wx.EXPAND, 0)

        sizer_param_xy = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_param_x = StaticBoxSizer(
            self, wx.ID_ANY, _("First parameter (X-Axis)"), wx.VERTICAL
        )

        hline_param_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Parameter:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_param_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_param_1.Add(self.combo_param_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.min_max_container_1 = wx.BoxSizer(wx.VERTICAL)
        hline_count_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Count:"))
        size_it(mylbl, LABEL_WIDTH)
        self.info_delta_1 = wxStaticText(self, wx.ID_ANY, "")

        hline_count_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count_1.Add(self.spin_count_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count_1.Add(self.info_delta_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_min_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Minimum:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_min_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_1.Add(self.text_min_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_1.Add(self.unit_param_1a, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_max_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Maximum:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_max_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_1.Add(self.text_max_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_1.Add(self.unit_param_1b, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.min_max_container_1.Add(hline_count_1, 0, wx.EXPAND, 0)
        self.min_max_container_1.Add(hline_min_1, 0, wx.EXPAND, 0)
        self.min_max_container_1.Add(hline_max_1, 0, wx.EXPAND, 0)

        hline_dim_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Width:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_dim_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim_1.Add(self.text_dim_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wxStaticText(self, wx.ID_ANY, "mm")
        hline_dim_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_delta_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Delta:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_delta_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_delta_1.Add(self.text_delta_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wxStaticText(self, wx.ID_ANY, "mm")
        hline_delta_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_color_1 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Color:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_color_1.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_1.Add(self.combo_color_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_1.Add(self.check_color_direction_1, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.sizer_param_x.Add(hline_param_1, 0, wx.EXPAND, 0)
        self.sizer_param_x.Add(self.min_max_container_1, 0, wx.EXPAND, 0)
        self.sizer_param_x.Add(self.list_options_1, 0, wx.EXPAND, 0)
        self.sizer_param_x.Add(hline_dim_1, 0, wx.EXPAND, 0)
        self.sizer_param_x.Add(hline_delta_1, 0, wx.EXPAND, 0)
        self.sizer_param_x.Add(hline_color_1, 0, wx.EXPAND, 0)

        self.sizer_param_y = StaticBoxSizer(
            self, wx.ID_ANY, _("Second parameter (Y-Axis)"), wx.VERTICAL
        )

        hline_param_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Parameter:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_param_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_param_2.Add(self.combo_param_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.min_max_container_2 = wx.BoxSizer(wx.VERTICAL)
        hline_count_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Count:"))
        size_it(mylbl, LABEL_WIDTH)
        self.info_delta_2 = wxStaticText(self, wx.ID_ANY, "")
        hline_count_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count_2.Add(self.spin_count_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_count_2.Add(self.info_delta_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_min_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Minimum:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_min_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_2.Add(self.text_min_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_min_2.Add(self.unit_param_2a, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_max_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Maximum:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_max_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_2.Add(self.text_max_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_max_2.Add(self.unit_param_2b, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.min_max_container_2.Add(hline_count_2, 0, wx.EXPAND, 0)
        self.min_max_container_2.Add(hline_min_2, 0, wx.EXPAND, 0)
        self.min_max_container_2.Add(hline_max_2, 0, wx.EXPAND, 0)

        hline_dim_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Height:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_dim_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_dim_2.Add(self.text_dim_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wxStaticText(self, wx.ID_ANY, "mm")
        hline_dim_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_delta_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Delta:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_delta_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_delta_2.Add(self.text_delta_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        mylbl = wxStaticText(self, wx.ID_ANY, "mm")
        hline_delta_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        hline_color_2 = wx.BoxSizer(wx.HORIZONTAL)
        mylbl = wxStaticText(self, wx.ID_ANY, _("Color:"))
        size_it(mylbl, LABEL_WIDTH)
        hline_color_2.Add(mylbl, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_2.Add(self.combo_color_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hline_color_2.Add(self.check_color_direction_2, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.sizer_param_y.Add(hline_param_2, 0, wx.EXPAND, 0)
        self.sizer_param_y.Add(self.min_max_container_2, 0, wx.EXPAND, 0)
        self.sizer_param_y.Add(self.list_options_2, 0, wx.EXPAND, 0)
        self.sizer_param_y.Add(hline_dim_2, 0, wx.EXPAND, 0)
        self.sizer_param_y.Add(hline_delta_2, 0, wx.EXPAND, 0)
        self.sizer_param_y.Add(hline_color_2, 0, wx.EXPAND, 0)

        sizer_param_xy.Add(self.sizer_param_x, 1, wx.EXPAND, 0)
        sizer_param_xy.Add(self.sizer_param_y, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_param_optype, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_param_xy, 0, wx.EXPAND, 0)
        sizer_main.Add(self.button_create, 0, wx.EXPAND, 0)

        sizer_info = StaticBoxSizer(self, wx.ID_ANY, _("How to use it"), wx.VERTICAL)
        infomsg = _("To provide the best burning results, the parameters of operations")
        infomsg += " " + _(
            "need to be adjusted according to *YOUR* laser and the specific material"
        )
        infomsg += " " + _(
            "you want to work with (e.g. one batch of poplar plywood from one supplier"
        )
        infomsg += " " + _(
            "may respond completely different to a batch of another supplier despite"
        )
        infomsg += " " + _("having the very same specifications on paper).")
        infomsg += "\n" + _(
            "E.g. for a regular CO2 laser you want to optimize the burn speed"
        )
        infomsg += " " + _(
            "for a given power to reduce burn marks or decrease execution time."
        )
        infomsg += "\n" + _(
            "Meerk40t simplifies this task to find out the optimal settings"
        )
        infomsg += " " + _(
            "by creating a testpattern that varies two different parameters."
        )

        info_label = TextCtrl(
            self, wx.ID_ANY, value=infomsg, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_label.SetBackgroundColour(self.GetBackgroundColour())
        sizer_info.Add(info_label, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_info, 1, wx.EXPAND, 0)

        self.button_create.SetToolTip(_("Create a grid with your values"))
        s = _("Operation type for which the testpattern will be generated")
        s += "\n" + _(
            "You can define the common parameters for this operation in the other tabs on top of this window"
        )
        self.combo_ops.SetToolTip(s)
        self.combo_param_1.SetToolTip(
            _("Choose the first parameter that you want to be tested")
        )
        self.combo_param_2.SetToolTip(
            _("Choose the second parameter that you want to be tested")
        )
        self.combo_color_1.SetToolTip(
            _(
                "Choose the color aspect for the first parameter. NB: the colors for both parameters will be combined"
            )
        )
        self.combo_color_2.SetToolTip(
            _(
                "Choose the color aspect for the second parameter. NB: the colors for both parameters will be combined"
            )
        )
        self.check_color_direction_1.SetToolTip(
            _(
                "If checked, then the color aspect will grow from min to max values, if not then shrink"
            )
        )
        self.check_color_direction_2.SetToolTip(
            _(
                "If checked, then the color aspect will grow from min to max values, if not then shrink"
            )
        )
        self.spin_count_1.SetToolTip(
            _(
                "Define how many values you want to test in the interval between min and max"
            )
        )
        self.spin_count_2.SetToolTip(
            _(
                "Define how many values you want to test in the interval between min and max"
            )
        )
        self.check_labels.SetToolTip(
            _("Will create a descriptive label at the sides of the grid")
        )
        self.check_values.SetToolTip(
            _("Will create the corresponding values as labels at the sides of the grid")
        )
        self.text_min_1.SetToolTip(_("Minimum value for 1st parameter"))
        self.text_max_1.SetToolTip(_("Maximum value for 1st parameter"))
        self.text_min_2.SetToolTip(_("Minimum value for 2nd parameter"))
        self.text_max_2.SetToolTip(_("Maximum value for 2nd parameter"))
        self.text_dim_1.SetToolTip(_("Width of the to be created pattern"))
        self.text_dim_2.SetToolTip(_("Height of the to be created pattern"))
        self.text_delta_1.SetToolTip(_("Horizontal gap between patterns"))
        self.text_delta_2.SetToolTip(_("Vertical gap between patterns"))

        self.button_create.Bind(wx.EVT_BUTTON, self.on_button_create_pattern)
        self.combo_ops.Bind(wx.EVT_COMBOBOX, self.set_param_according_to_op)
        self.text_min_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_max_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_min_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_max_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_dim_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_delta_1.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_dim_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.text_delta_2.Bind(wx.EVT_TEXT, self.validate_input)
        self.combo_param_1.Bind(wx.EVT_COMBOBOX, self.on_combo_1)
        self.combo_param_2.Bind(wx.EVT_COMBOBOX, self.on_combo_2)
        self.combo_images.Bind(wx.EVT_COMBOBOX, self.on_combo_image)
        self.spin_count_1.Bind(wx.EVT_SPINCTRL, self.validate_input)
        self.spin_count_2.Bind(wx.EVT_SPINCTRL, self.validate_input)
        self.Bind(wx.EVT_CHECKLISTBOX, self.validate_input, self.list_options_1)
        self.Bind(wx.EVT_CHECKLISTBOX, self.validate_input, self.list_options_2)

        self.SetSizer(sizer_main)
        self.Layout()
        self.setup_settings()
        self.combo_ops.SetSelection(0)
        self.restore_settings()
        self.sync_fields()

    def shortened(self, value, digits):
        result = str(round(value, digits))
        if "." in result:
            while result.endswith("0"):
                result = result[:-1]
        if result.endswith("."):
            if result == ".":
                result = "0"
            else:
                result = result[:-1]
        return result

    def on_combo_image(self, event):
        self.validate_input(event)
        op = self.combo_ops.GetSelection()
        if op != 3:  # No Image?
            return
        idx = self.combo_images.GetSelection() - 1
        if 0 <= idx < len(self.images):
            bb = self.images[idx].bounds
            if bb is not None:
                wd = Length(amount=bb[2] - bb[0], preferred_units="mm")
                ht = Length(amount=bb[3] - bb[1], preferred_units="mm")
                self.text_dim_1.SetValue(f"{wd.mm:.1f}")
                self.text_dim_2.SetValue(f"{ht.mm:.1f}")

    def on_selection_list(self, event):
        return

    def set_callback(self, routine):
        self.callback = routine
        idx = self.combo_ops.GetSelection()
        opnode = None
        secondary_node = None
        if idx >= 0:
            opnode = self.default_op[idx]
            secondary_node = self.secondary_default_op[idx]
        if self.callback is not None and idx >= 0:
            self.callback(opnode, secondary_node)

    def use_percent(self):
        self.context.device.setting(bool, "use_percent_for_power_display", False)
        return self.context.device.use_percent_for_power_display

    def use_mm_min(self):
        self.context.device.setting(bool, "use_mm_min_for_speed_display", False)
        return self.context.device.use_mm_min_for_speed_display

    def set_param_according_to_op(self, event):
        def preset_image_dpi(node=None):
            # Will be called ahead of the modification of the 'op image' dpi variable
            node.overrule_dpi = True

        def preset_passes(node=None):
            # Will be called ahead of the modification of the passes variable
            node.passes_custom = True

        def preset_balor_wobble(node=None):
            # Will be called ahead of the modification of a wobble variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            node.settings["wobble_enabled"] = True

        def preset_balor_rapid(node=None):
            # Will be called ahead of the modification of a rapid variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            node.settings["rapid_enabled"] = True

        def preset_balor_pulse(node=None):
            # Will be called ahead of the modification of a pulse variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            node.settings["pulse_width_enabled"] = True

        def preset_balor_timings(node=None):
            # Will be called ahead of the modification of a timing variable
            # to copy the device defaults
            if node is None or "balor" not in self.context.device.path:
                return
            if not node.settings["timing_enabled"]:
                node.settings["timing_enabled"] = True
                node.settings["delay_laser_on"] = self.context.device.delay_laser_on
                node.settings["delay_laser_off"] = self.context.device.delay_laser_off
                node.settings["delay_polygon"] = self.context.device.delay_polygon

        opidx = self.combo_ops.GetSelection()
        if self.current_op == opidx:
            return
        self.current_op = opidx

        busy = wx.BusyCursor()
        self.Freeze()
        if opidx < 0:
            opnode = None
            secondary_node = None
            self._freecolor = True
            self.combo_images.Show(False)
            self.text_dim_1.Enable(True)
            self.text_dim_2.Enable(True)
        else:
            opnode = self.default_op[opidx]
            secondary_node = self.secondary_default_op[opidx]
            self._freecolor = self.color_scheme_free[opidx]
            self.combo_images.Show(self.use_image[opidx])
            self.text_dim_1.Enable(not self.use_image[opidx])
            self.text_dim_2.Enable(not self.use_image[opidx])

        self.sizer_param_op.Layout()
        if self.callback is not None:
            self.callback(opnode, secondary_node)
        self.combo_color_1.Enable(self._freecolor)
        self.combo_color_2.Enable(self._freecolor)
        self.check_color_direction_1.Enable(self._freecolor)
        self.check_color_direction_2.Enable(self._freecolor)

        # (internal_attribute, secondary_attribute, Label, unit, keep_unit, needs_to_be_positive, choices)
        if self.use_percent():
            ppi = "%"
        else:
            ppi = "ppi"
        if self.use_mm_min():
            speed_unit = "mm/min"
        else:
            speed_unit = "mm/s"
        self.parameters = [
            ("speed", None, _("Speed"), speed_unit, False, True, None),
            ("power", None, _("Power"), ppi, False, True, None),
            ("passes", preset_passes, _("Passes"), "x", False, True, None),
        ]

        if opidx == 0:
            # Cut
            # (internal_attribute, secondary_attribute, Label, unit, keep_unit, needs_to_be_positive, type)
            self.parameters = [
                ("speed", None, _("Speed"), speed_unit, False, True, None, None),
                ("power", None, _("Power"), ppi, False, True, None, None),
                ("passes", preset_passes, _("Passes"), "x", False, True, int, None),
            ]
        elif opidx == 1:
            # Engrave
            self.parameters = [
                ("speed", None, _("Speed"), speed_unit, False, True, None, None),
                ("power", None, _("Power"), ppi, False, True, None, None),
                ("passes", preset_passes, _("Passes"), "x", False, True, int, None),
            ]
        elif opidx == 2:
            # Raster
            self.parameters = [
                ("speed", None, _("Speed"), speed_unit, False, True, None, None),
                ("power", None, _("Power"), ppi, False, True, None, None),
                ("passes", preset_passes, _("Passes"), "x", False, True, int, None),
                ("dpi", None, _("DPI"), "dpi", False, True, int, None),
                ("overscan", None, _("Overscan"), "mm", False, True, None, None),
            ]
        elif opidx == 3:
            # Image
            self.parameters = [
                ("speed", None, _("Speed"), speed_unit, False, True, None, None),
                ("power", None, _("Power"), ppi, False, True, None, None),
                ("passes", preset_passes, _("Passes"), "x", False, True, int, None),
                ("dpi", preset_image_dpi, _("DPI"), "dpi", False, True, int, None),
                ("overscan", None, _("Overscan"), "mm", False, True, None, None),
            ]
        elif opidx == 4:
            # Hatch
            self.parameters = [
                ("speed", None, _("Speed"), speed_unit, False, True, None, None),
                ("power", None, _("Power"), ppi, False, True, None, None),
                ("passes", preset_passes, _("Passes"), "x", False, True, int, None),
                (
                    "hatch_distance",
                    None,
                    _("Hatch Distance"),
                    "mm",
                    False,
                    True,
                    None,
                    None,
                ),
                ("hatch_angle", None, _("Hatch Angle"), "deg", False, True, None, None),
            ]
        elif opidx == 5:
            # Wobble
            # (internal_attribute, secondary_attribute, Label, unit, keep_unit, needs_to_be_positive, type)
            wobble_choices = list(self.context.match("wobble", suffix=True))
            self.parameters = [
                ("speed", None, _("Speed"), speed_unit, False, True, None, None),
                ("power", None, _("Power"), ppi, False, True, None, None),
                ("passes", preset_passes, _("Passes"), "x", False, True, int, None),
                # wobble_radius
                (
                    "wobble_radius",
                    preset_balor_wobble,
                    _("Wobble Radius"),
                    "mm",
                    True,
                    True,
                    None,
                    None,
                ),
                (
                    "wobble_interval",
                    preset_balor_wobble,
                    _("Wobble Interval"),
                    "mm",
                    True,
                    True,
                    None,
                    None,
                ),
                (
                    "wobble_speed",
                    preset_balor_wobble,
                    _("Wobble Speed Multiplier"),
                    "x",
                    False,
                    True,
                    None,
                    None,
                ),
            ]
            if wobble_choices:
                self.parameters.append(
                    (
                        "wobble_type",
                        preset_balor_wobble,
                        _("Wobble Type"),
                        "",
                        True,
                        True,
                        None,
                        wobble_choices,
                    ),
                )

        if "balor" in self.context.device.path:
            balor_choices = [
                ("frequency", None, _("Frequency"), "kHz", False, True, None, None),
                (
                    "rapid_speed",
                    preset_balor_rapid,
                    _("Rapid Speed"),
                    "mm/s",
                    False,
                    True,
                    None,
                    None,
                ),
                (
                    "delay_laser_on",
                    preset_balor_timings,
                    _("Laser On Delay"),
                    "µs",
                    False,
                    False,
                    None,
                    None,
                ),
                (
                    "delay_laser_off",
                    preset_balor_timings,
                    _("Laser Off Delay"),
                    "µs",
                    False,
                    False,
                    None,
                    None,
                ),
                (
                    "delay_polygon",
                    preset_balor_timings,
                    _("Polygon Delay"),
                    "µs",
                    False,
                    False,
                    None,
                    None,
                ),
            ]
            if self.context.device.pulse_width_enabled:
                balor_choices.append(
                    (
                        "pulse_width",
                        preset_balor_pulse,
                        _("Pulse Width"),
                        "ns",
                        False,
                        True,
                        None,
                        None,
                    )
                )

            self.parameters.extend(balor_choices)
        # for p in self.parameters:
        #     if len(p) != 7:
        #         print (f"No good: {p}")
        choices = []
        for entry in self.parameters:
            choices.append(entry[2])
        self.combo_param_1.Clear()
        self.combo_param_1.Set(choices)
        self.combo_param_2.Clear()
        self.combo_param_2.Set(choices)
        idx1 = -1
        idx2 = -1
        if len(self.parameters) > 0:
            idx1 = 0
            idx2 = 0
        if len(self.parameters) > 1:
            idx2 = 1
        self.combo_param_1.SetSelection(idx1)
        self.on_combo_1(None)
        self.combo_param_2.SetSelection(idx2)
        self.on_combo_2(None)
        self.Layout()
        self.Thaw()
        del busy

    def on_combo_1(self, input):
        s_unit = ""
        b_positive = True
        idx = self.combo_param_1.GetSelection()
        # 0 = internal_attribute, 1 = secondary_attribute,
        # 2 = Label, 3 = unit,
        # 4 = keep_unit, 5 = needs_to_be_positive)
        standard_items = True
        choices = []
        if 0 <= idx < len(self.parameters):
            s_unit = self.parameters[idx][3]
            b_positive = self.parameters[idx][5]
            if self.parameters[idx][7] is not None:
                self.context.template_list1 = "|".join(
                    self.list_options_1.GetCheckedStrings()
                )
                standard_items = False
                choices = self.parameters[idx][7]
                self.list_options_1.Set(choices)
                checked_strings = [
                    s for s in self.context.template_list1.split("|") if s
                ]
                if not checked_strings:
                    checked_strings = choices
                self.list_options_1.SetCheckedStrings(checked_strings)

        self.unit_param_1a.SetLabel(s_unit)
        self.unit_param_1b.SetLabel(s_unit)
        self.min_max_container_1.ShowItems(standard_items)
        self.list_options_1.Show(not standard_items)
        self.sizer_param_x.Layout()
        self.Layout()

        # And now enter validation...
        self.validate_input(None)

    def on_combo_2(self, input):
        s_unit = ""
        idx = self.combo_param_2.GetSelection()
        # 0 = internal_attribute, 1 = secondary_attribute,
        # 2 = Label, 3 = unit,
        # 4 = keep_unit, 5 = needs_to_be_positive)
        standard_items = True
        choices = []
        if 0 <= idx < len(self.parameters):
            s_unit = self.parameters[idx][3]
            if self.parameters[idx][7] is not None:
                self.context.template_list2 = "|".join(
                    self.list_options_2.GetCheckedStrings()
                )
                standard_items = False
                choices = self.parameters[idx][7]
                self.list_options_2.Set(choices)
                checked_strings = [
                    s for s in self.context.template_list2.split("|") if s
                ]
                if not checked_strings:
                    checked_strings = choices
                self.list_options_2.SetCheckedStrings(checked_strings)
        self.unit_param_2a.SetLabel(s_unit)
        self.unit_param_2b.SetLabel(s_unit)
        self.min_max_container_2.ShowItems(standard_items)
        self.list_options_2.Show(not standard_items)
        self.sizer_param_y.Layout()
        self.Layout()
        # And now enter validation...
        self.validate_input(None)

    def validate_input(self, event):
        def valid_float(ctrl):
            result = True
            if ctrl.GetValue() == "":
                result = False
            else:
                try:
                    value = float(ctrl.GetValue())
                except ValueError:
                    result = False
            return result

        def check_for_active():
            active = True
            valid_interval_1 = True
            valid_interval_2 = True
            optype = self.combo_ops.GetSelection()
            if optype < 0:
                return False
            if (
                optype == 3 and self.combo_images.GetSelection() < 1
            ):  # image and no valid image chosen
                return False
            idx1 = self.combo_param_1.GetSelection()
            if idx1 < 0:
                return False
            idx2 = self.combo_param_2.GetSelection()
            if idx2 < 0:
                return False
            if idx1 == idx2:
                return False
            # Proper check for standard / non-standard parameters
            if self.parameters[idx1][7] is not None:
                if not self.list_options_1.GetCheckedStrings():
                    active = False
                valid_interval_1 = True
            else:
                if not valid_float(self.text_min_1):
                    active = False
                    valid_interval_1 = False
                if not valid_float(self.text_max_1):
                    active = False
                    valid_interval_1 = False
            if self.parameters[idx2][7] is not None:
                if not self.list_options_2.GetCheckedStrings():
                    active = False
                valid_interval_2 = True
            else:
                if not valid_float(self.text_min_2):
                    active = False
                    valid_interval_2 = False
                if not valid_float(self.text_max_2):
                    active = False
                    valid_interval_2 = False
            if not valid_float(self.text_dim_1):
                active = False
            if not valid_float(self.text_delta_1):
                active = False
            if not valid_float(self.text_dim_2):
                active = False
            if not valid_float(self.text_delta_2):
                active = False
            if valid_interval_1:
                minv = float(self.text_min_1.GetValue())
                maxv = float(self.text_max_1.GetValue())
                count = self.spin_count_1.GetValue()
                delta = maxv - minv
                if count > 1:
                    delta /= count - 1
                s_unit = ""
                idx = self.combo_param_1.GetSelection()
                # 0 = internal_attribute, 1 = secondary_attribute,
                # 2 = Label, 3 = unit,
                # 4 = keep_unit, 5 = needs_to_be_positive)
                if 0 <= idx < len(self.parameters):
                    s_unit = self.parameters[idx][3]
                self.info_delta_1.SetLabel(
                    _("Every {dist}").format(dist=self.shortened(delta, 3) + s_unit)
                )
            else:
                self.info_delta_1.SetLabel("---")
            if valid_interval_2:
                minv = float(self.text_min_2.GetValue())
                maxv = float(self.text_max_2.GetValue())
                count = self.spin_count_2.GetValue()
                delta = maxv - minv
                if count > 1:
                    delta /= count - 1
                s_unit = ""
                idx = self.combo_param_2.GetSelection()
                # 0 = internal_attribute, 1 = secondary_attribute,
                # 2 = Label, 3 = unit,
                # 4 = keep_unit, 5 = needs_to_be_positive)
                if 0 <= idx < len(self.parameters):
                    s_unit = self.parameters[idx][3]
                self.info_delta_2.SetLabel(
                    _("Every {dist}").format(dist=self.shortened(delta, 3) + s_unit)
                )
            else:
                self.info_delta_2.SetLabel("---")
            return active

        active = check_for_active()
        self.button_create.Enable(active)

    def on_device_update(self):
        self.current_op = None
        self.set_param_according_to_op(None)
        # self.on_combo_1(None)
        # self.on_combo_2(None)

    def on_button_create_pattern(self, event):
        def make_color(idx1, max1, idx2, max2, aspect1, growing1, aspect2, growing2):
            if self._freecolor:
                r = 0
                g = 0
                b = 0

                rel = max1 - 1
                if rel < 1:
                    rel = 1
                if growing1:
                    val1 = int(idx1 / rel * 255.0)
                else:
                    val1 = 255 - int(idx1 / rel * 255.0)

                rel = max2 - 1
                if rel < 1:
                    rel = 1
                if growing2:
                    val2 = int(idx2 / rel * 255.0)
                else:
                    val2 = 255 - int(idx2 / rel * 255.0)
                if aspect1 == 1:
                    g = val1
                elif aspect1 == 2:
                    b = val1
                else:
                    r = val1
                if aspect2 == 1:
                    g = val1
                elif aspect2 == 2:
                    b = val2
                else:
                    r = val2
            else:
                r = 0
                g = 0
                b = 0
            mycolor = Color(r, g, b)
            return mycolor

        def clear_all():
            self.context.elements.clear_operations(fast=True)
            self.context.elements.clear_elements(fast=True)

        def create_operations(range1, range2):
            # opchoices = [_("Cut"), _("Engrave"), _("Raster"), _("Image"), _("Hatch")]
            count_1 = len(range1)
            count_2 = len(range2)
            try:
                dimension_1 = float(self.text_dim_1.GetValue())
            except ValueError:
                dimension_1 = -1
            try:
                dimension_2 = float(self.text_dim_2.GetValue())
            except ValueError:
                dimension_2 = -1
            if dimension_1 <= 0:
                dimension_1 = 5
            if dimension_2 <= 0:
                dimension_2 = 5

            try:
                gap_1 = float(self.text_delta_1.GetValue())
            except ValueError:
                gap_1 = -1
            try:
                gap_2 = float(self.text_delta_2.GetValue())
            except ValueError:
                gap_2 = -1

            if gap_1 < 0:
                gap_1 = 0
            if gap_2 < 0:
                gap_2 = 5

            # print (f"Creating operations for {len(range1)} x {len(range2)}")
            display_labels = self.check_labels.GetValue()
            display_values = self.check_values.GetValue()
            color_aspect_1 = max(0, self.combo_color_1.GetSelection())
            color_aspect_2 = max(0, self.combo_color_2.GetSelection())
            color_growing_1 = self.check_color_direction_1.GetValue()
            color_growing_2 = self.check_color_direction_2.GetValue()

            if optype == 3:
                shapetype = "image"
            else:
                shapetype = "rect"
            size_x = float(Length(f"{dimension_1}mm"))
            size_y = float(Length(f"{dimension_2}mm"))
            gap_x = float(Length(f"{gap_1}mm"))
            gap_y = float(Length(f"{gap_2}mm"))
            expected_width = count_1 * size_x + (count_1 - 1) * gap_x
            expected_height = count_2 * size_y + (count_2 - 1) * gap_y
            # Need to be adjusted to allow for centering
            start_x = (
                float(Length(self.context.device.view.width)) - expected_width
            ) / 2
            start_y = (
                float(Length(self.context.device.view.height)) - expected_height
            ) / 2
            operation_branch = self.context.elements._tree.get(type="branch ops")
            element_branch = self.context.elements._tree.get(type="branch elems")

            text_scale_x = min(1.0, size_y / float(Length("20mm")))
            text_scale_y = min(1.0, size_x / float(Length("20mm")))

            # Make one op for text
            if display_labels or display_values:
                text_op_x = RasterOpNode()
                text_op_x.color = Color("black")
                text_op_x.label = "Descriptions X-Axis"
                text_op_y = RasterOpNode()
                text_op_y.color = Color("black")
                text_op_y.label = "Descriptions Y-Axis"
                operation_branch.add_node(text_op_x)
                operation_branch.add_node(text_op_y)
            if display_labels:
                text_x = start_x + expected_width / 2
                text_y = start_y - min(float(Length("10mm")), 3 * gap_y)
                unit_str = f" [{param_unit_1}]" if param_unit_1 else ""
                node = element_branch.add(
                    text=f"{param_name_1}{unit_str}",
                    matrix=Matrix(
                        f"translate({text_x}, {text_y}) scale({2 * max(text_scale_x, text_scale_y) * UNITS_PER_PIXEL})"
                    ),
                    anchor="middle",
                    fill=Color("black"),
                    type="elem text",
                )
                text_op_x.add_reference(node, 0)

                text_x = start_x - min(float(Length("10mm")), 3 * gap_x)
                text_y = start_y + expected_height / 2
                unit_str = f" [{param_unit_2}]" if param_unit_2 else ""
                node = element_branch.add(
                    text=f"{param_name_2}{unit_str}",
                    matrix=Matrix(
                        f"translate({text_x}, {text_y}) scale({2 * max(text_scale_x, text_scale_y) * UNITS_PER_PIXEL})"
                    ),
                    anchor="middle",
                    fill=Color("black"),
                    type="elem text",
                )
                node.matrix.post_rotate(tau * 3 / 4, text_x, text_y)
                node.modified()
                text_op_y.add_reference(node, 0)

            xx = start_x
            for idx1, _p_value_1 in enumerate(range1):
                # print (f"Creating row {idx1} of {len(range1)} with value {_p_value_1}")
                p_value_1 = _p_value_1
                if param_value_type_1 is not None:
                    try:
                        _pp = param_value_type_1(_p_value_1)
                        p_value_1 = _pp
                    except ValueError:
                        pass
                if isinstance(p_value_1, str):
                    pval1 = p_value_1
                else:
                    pval1 = self.shortened(p_value_1, 3)

                yy = start_y

                if display_values:
                    # Add a text above for each column
                    text_x = xx + 0.5 * size_x
                    text_y = yy - min(float(Length("5mm")), 1.5 * gap_y)
                    node = element_branch.add(
                        text=f"{pval1}",
                        matrix=Matrix(
                            f"translate({text_x}, {text_y}) scale({text_scale_x * UNITS_PER_PIXEL})"
                        ),
                        anchor="middle",
                        fill=Color("black"),
                        type="elem text",
                    )
                    # node.matrix.post_rotate(tau / 4, text_x, text_y)
                    node.modified()
                    text_op_x.add_reference(node, 0)

                for idx2, _p_value_2 in enumerate(range2):
                    # print (f"Creating column {idx2} of {len(range2)} with value {_p_value_2}")
                    p_value_2 = _p_value_2
                    if param_value_type_2 is not None:
                        try:
                            _pp = param_value_type_2(_p_value_2)
                            p_value_2 = _pp
                        except ValueError:
                            pass
                    if isinstance(p_value_2, str):
                        pval2 = p_value_2
                    else:
                        pval2 = self.shortened(p_value_2, 3)
                    s_lbl = f"{param_type_1}={pval1}{param_unit_1}"
                    s_lbl += f"- {param_type_2}={pval2}{param_unit_2}"
                    if display_values and idx1 == 0:  # first row, so add a text above
                        text_x = xx - min(float(Length("5mm")), 1.5 * gap_x)
                        text_y = yy + 0.5 * size_y
                        node = element_branch.add(
                            text=f"{pval2}",
                            matrix=Matrix(
                                f"translate({text_x}, {text_y}) scale({text_scale_y * UNITS_PER_PIXEL})"
                            ),
                            anchor="middle",
                            fill=Color("black"),
                            type="elem text",
                        )
                        node.matrix.post_rotate(tau * 3 / 4, text_x, text_y)
                        text_op_y.add_reference(node, 0)
                    if optype == 0:  # Cut
                        this_op = copy(self.default_op[optype])
                        master_op = this_op
                        usefill = False
                    elif optype == 1:  # Engrave
                        this_op = copy(self.default_op[optype])
                        master_op = this_op
                        usefill = False
                    elif optype == 2:  # Raster
                        this_op = copy(self.default_op[optype])
                        master_op = this_op
                        usefill = True
                    elif optype == 3:  # Image
                        this_op = copy(self.default_op[optype])
                        master_op = this_op
                        usefill = False
                    elif optype == 4:  # Hatch
                        master_op = copy(self.default_op[optype])
                        this_op = copy(self.secondary_default_op[optype])
                        master_op.add_node(this_op)

                        # We need to add a hatch node and make this the target for parameter application
                        usefill = False
                    elif optype == 5:  # Wobble
                        # Wobble is a special case, we need to create a master op and a secondary op
                        # We need to add a wobble node and make this the target for parameter application
                        master_op = copy(self.default_op[optype])
                        this_op = copy(self.secondary_default_op[optype])
                        master_op.add_node(this_op)
                        usefill = False
                    else:
                        return
                    this_op.label = s_lbl

                    # Do we need to prep the op?
                    if param_prepper_1 is not None:
                        param_prepper_1(master_op)

                    if param_keep_unit_1:
                        value = str(p_value_1) + param_unit_1
                    else:
                        value = p_value_1
                    if param_type_1 == "power" and self.use_percent():
                        value *= 10.0
                    if param_type_1 == "speed" and self.use_mm_min():
                        value /= 60.0
                    if hasattr(master_op, param_type_1):
                        # quick and dirty
                        if param_type_1 == "passes":
                            value = int(value)
                        if param_type_1 == "hatch_distance" and not str(value).endswith(
                            "mm"
                        ):
                            value = f"{value}mm"
                        setattr(master_op, param_type_1, value)
                    # else:  # Try setting
                    #     master_op.settings[param_type_1] = value
                    if hasattr(this_op, param_type_1):
                        # quick and dirty
                        if param_type_1 == "passes":
                            value = int(value)
                        elif param_type_1 == "hatch_distance" and not str(
                            value
                        ).endswith("mm"):
                            value = f"{value}mm"
                        elif param_type_1 == "hatch_angle" and not str(value).endswith(
                            "deg"
                        ):
                            value = f"{value}deg"
                        setattr(this_op, param_type_1, value)
                    elif hasattr(this_op, "settings"):  # Try setting
                        this_op.settings[param_type_1] = value

                    # Do we need to prep the op?
                    if param_prepper_2 is not None:
                        param_prepper_2(master_op)

                    if param_keep_unit_2:
                        value = str(p_value_2) + param_unit_2
                    else:
                        value = p_value_2
                    if param_type_2 == "power" and self.use_percent():
                        value *= 10.0
                    if param_type_2 == "speed" and self.use_mm_min():
                        value /= 60.0
                    if hasattr(master_op, param_type_2):
                        # quick and dirty
                        if param_type_2 == "passes":
                            value = int(value)
                        if param_type_2 == "hatch_distance" and not str(value).endswith(
                            "mm"
                        ):
                            value = f"{value}mm"
                        setattr(master_op, param_type_2, value)
                    if hasattr(this_op, param_type_2):
                        if param_type_2 == "passes":
                            value = int(value)
                        elif param_type_2 == "hatch_distance" and not str(
                            value
                        ).endswith("mm"):
                            value = f"{value}mm"
                        elif param_type_2 == "hatch_angle" and not str(value).endswith(
                            "deg"
                        ):
                            value = f"{value}deg"
                        setattr(this_op, param_type_2, value)
                    elif hasattr(this_op, "settings"):  # Try setting
                        this_op.settings[param_type_2] = value

                    set_color = make_color(
                        idx1,
                        len(range1),
                        idx2,
                        len(range2),
                        color_aspect_1,
                        color_growing_1,
                        color_aspect_2,
                        color_growing_2,
                    )
                    this_op.color = set_color
                    # Add op to tree.
                    operation_branch.add_node(master_op)
                    # Now add a rectangle to the scene and assign it to the newly created op
                    fill_color = set_color if usefill else None
                    elemnode = None
                    if shapetype == "image":
                        idx = self.combo_images.GetSelection() - 1
                        if 0 <= idx < len(self.images):
                            elemnode = copy(self.images[idx])
                            elemnode.matrix.post_translate(xx, yy)
                            elemnode.modified()
                            element_branch.add_node(elemnode)
                    elif shapetype == "rect":
                        elemnode = element_branch.add(
                            x=xx,
                            y=yy,
                            width=size_x,
                            height=size_y,
                            stroke=set_color,
                            fill=fill_color,
                            type="elem rect",
                        )
                    elif shapetype == "circle":
                        elemnode = element_branch.add(
                            cx=xx + size_x / 2,
                            cy=yy + size_y / 2,
                            rx=size_x / 2,
                            ry=size_y / 2,
                            stroke=set_color,
                            fill=fill_color,
                            type="elem ellipse",
                        )
                    if elemnode is not None:
                        elemnode.label = s_lbl
                        this_op.add_reference(elemnode, 0)
                    yy = yy + gap_y + size_y
                xx = xx + gap_x + size_x

        # Read the parameters and user input
        optype = self.combo_ops.GetSelection()
        if optype < 0:
            return
        idx1 = self.combo_param_1.GetSelection()
        if idx1 < 0:
            return
        # 0 = internal_attribute, 1 = secondary_attribute,
        # 2 = Label, 3 = unit,
        # 4 = keep_unit, 5 = needs_to_be_positive)
        param_name_1 = self.parameters[idx1][2]
        param_type_1 = self.parameters[idx1][0]
        param_value_type_1 = self.parameters[idx1][6]
        param_prepper_1 = self.parameters[idx1][1]
        if param_prepper_1 == "":
            param_prepper_1 = None
        param_unit_1 = self.parameters[idx1][3]
        param_keep_unit_1 = self.parameters[idx1][4]

        idx2 = self.combo_param_2.GetSelection()
        if idx2 < 0:
            return
        param_name_2 = self.parameters[idx2][2]
        param_type_2 = self.parameters[idx2][0]
        param_value_type_2 = self.parameters[idx2][6]
        param_prepper_2 = self.parameters[idx2][1]
        if param_prepper_2 == "":
            param_prepper_2 = None
        param_unit_2 = self.parameters[idx2][3]
        param_keep_unit_2 = self.parameters[idx2][4]
        if param_type_1 == param_type_2:
            return

        def get_range(isx: bool, idx: int) -> list:
            value_range = []
            if idx < 0 or idx >= len(self.parameters):
                return value_range
            if self.parameters[idx][7] is not None:
                # Non-standard parameter, so we need to get the checked strings
                value_range = (
                    self.list_options_1.GetCheckedStrings()
                    if isx
                    else self.list_options_2.GetCheckedStrings()
                )
                if not value_range:
                    return []
            else:
                param_unit = self.parameters[idx][3]
                param_positive = self.parameters[idx][5]
                if isx:
                    text_min = self.text_min_1.GetValue()
                    text_max = self.text_max_1.GetValue()
                    text_count = self.spin_count_1.GetValue()
                else:
                    text_min = self.text_min_2.GetValue()
                    text_max = self.text_max_2.GetValue()
                    text_count = self.spin_count_2.GetValue()
                if text_min == "" or text_max == "" or text_count <= 0:
                    return value_range
                try:
                    min_value = float(text_min)
                    max_value = float(text_max)
                    count = int(text_count)
                except ValueError:
                    return value_range
                if param_unit == "deg":
                    min_value = float(text_min)
                    max_value = float(text_max)
                elif param_unit == "ppi":
                    min_value = max(min_value, 0)
                    max_value = min(max_value, 1000)
                elif param_unit == "%":
                    min_value = max(min_value, 0)
                    max_value = min(max_value, 100)
                else:
                    # > 0
                    if param_positive:
                        min_value = max(min_value, 0)
                        max_value = max(max_value, 0)
                delta = (max_value - min_value) / (count - 1) if count > 1 else 0
                if delta == 0:
                    value_range = [min_value]
                else:
                    value_range = [min_value + i * delta for i in range(count)]

            return value_range

        valid_range_1 = get_range(True, idx1)
        valid_range_2 = get_range(False, idx2)
        # print (valid_range_1)
        # print (valid_range_2)

        if len(valid_range_1) == 0 or len(valid_range_2) == 0:
            return

        message = _("This will delete all existing operations and elements") + "\n"
        message += (
            _("and replace them by the test-pattern! Are you really sure?") + "\n"
        )
        message += _("(Yes=Empty and Create, No=Keep existing)")
        caption = _("Create Test-Pattern")
        dlg = wx.MessageDialog(
            self,
            message,
            caption,
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
        )
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_YES:
            clear_all()
        elif result == wx.ID_CANCEL:
            return

        create_operations(range1=valid_range_1, range2=valid_range_2)

        self.context.signal("rebuild_tree")
        self.context.signal("refresh_scene", "Scene")
        self.save_settings()

    def setup_settings(self):
        self.context.setting(int, "template_optype", 0)
        self.context.setting(int, "template_param1", 0)
        self.context.setting(int, "template_param2", 1)
        self.context.setting(str, "template_min1", "")
        self.context.setting(str, "template_max1", "")
        self.context.setting(str, "template_min2", "")
        self.context.setting(str, "template_max2", "")
        self.context.setting(int, "template_count1", 5)
        self.context.setting(int, "template_count2", 5)
        self.context.setting(str, "template_dim_1", "10")
        self.context.setting(str, "template_dim_2", "10")
        self.context.setting(str, "template_gap_1", "5")
        self.context.setting(str, "template_gap_2", "5")
        self.context.setting(bool, "template_show_labels", True)
        self.context.setting(bool, "template_show_values", True)
        self.context.setting(int, "template_color1", 0)
        self.context.setting(int, "template_color2", 2)
        self.context.setting(bool, "template_coldir1", False)
        self.context.setting(bool, "template_coldir2", False)
        self.context.setting(str, "template_list1", "")
        self.context.setting(str, "template_list2", "")

    def _set_settings(self, templatename):
        info_field = (
            self.context.template_show_values,
            self.context.template_show_labels,
            self.context.template_optype,
            self.context.template_param1,
            self.context.template_param2,
            self.context.template_min1,
            self.context.template_max1,
            self.context.template_min2,
            self.context.template_max2,
            self.context.template_count1,
            self.context.template_count2,
            self.context.template_dim_1,
            self.context.template_dim_2,
            self.context.template_gap_1,
            self.context.template_gap_2,
            self.context.template_color1,
            self.context.template_color2,
            self.context.template_coldir1,
            self.context.template_coldir2,
            self.context.template_list1,
            self.context.template_list2,
        )
        # print (f"Save data to {templatename}, infofield-len={len(info_field)}")
        key = f"{templatename}"
        self.storage.write_persistent("materialtest", key, info_field)
        self.storage.write_configuration()

    def _get_settings(self, templatename):
        key = f"{templatename}"
        info_field = self.storage.read_persistent(tuple, "materialtest", key, None)
        if (
            info_field is not None
            and isinstance(info_field, (tuple, list))
            and len(info_field) >= 19
        ):

            def get_setting(idx, default):
                try:
                    return info_field[idx]
                except IndexError:
                    return default

            # print (f"Load data from {templatename}")
            self.context.template_show_values = get_setting(0, True)
            self.context.template_show_labels = get_setting(1, True)
            self.context.template_optype = info_field[2]
            self.context.template_param1 = info_field[3]
            self.context.template_param2 = info_field[4]
            self.context.template_min1 = get_setting(5, 0)
            self.context.template_max1 = get_setting(6, 100)
            self.context.template_min2 = get_setting(7, 0)
            self.context.template_max2 = get_setting(8, 100)
            self.context.template_count1 = get_setting(9, 5)
            self.context.template_count2 = get_setting(10, 5)
            self.context.template_dim_1 = info_field[11]
            self.context.template_dim_2 = info_field[12]
            self.context.template_gap_1 = info_field[13]
            self.context.template_gap_2 = info_field[14]
            self.context.template_color1 = info_field[15]
            self.context.template_color2 = info_field[16]
            self.context.template_coldir1 = info_field[17]
            self.context.template_coldir2 = info_field[18]
            self.context.template_list1 = get_setting(19, "")
            self.context.template_list2 = get_setting(20, "")

    def save_settings(self, templatename=None):
        self.context.template_show_values = self.check_values.GetValue()
        self.context.template_show_labels = self.check_labels.GetValue()
        self.context.template_optype = self.combo_ops.GetSelection()
        self.context.template_param1 = self.combo_param_1.GetSelection()
        self.context.template_param2 = self.combo_param_2.GetSelection()
        self.context.template_min1 = self.text_min_1.GetValue()
        self.context.template_max1 = self.text_max_1.GetValue()
        self.context.template_min2 = self.text_min_2.GetValue()
        self.context.template_max2 = self.text_max_2.GetValue()
        self.context.template_count1 = self.spin_count_1.GetValue()
        self.context.template_count2 = self.spin_count_2.GetValue()
        self.context.template_dim_1 = self.text_dim_1.GetValue()
        self.context.template_dim_2 = self.text_dim_2.GetValue()
        self.context.template_gap_1 = self.text_delta_1.GetValue()
        self.context.template_gap_2 = self.text_delta_2.GetValue()
        self.context.template_color1 = self.combo_color_1.GetSelection()
        self.context.template_color2 = self.combo_color_2.GetSelection()
        self.context.template_coldir1 = self.check_color_direction_1.GetValue()
        self.context.template_coldir2 = self.check_color_direction_2.GetValue()
        self.context.template_list1 = "|".join(self.list_options_1.GetCheckedStrings())
        self.context.template_list2 = "|".join(self.list_options_2.GetCheckedStrings())
        if templatename:
            # let's try to restore the settings
            self._set_settings(templatename)

    def restore_settings(self, templatename=None):
        if templatename:
            # let's try to restore the settings
            self._get_settings(templatename)
        try:
            self.check_color_direction_1.SetValue(self.context.template_coldir1)
            self.check_color_direction_2.SetValue(self.context.template_coldir2)
            self.combo_color_1.SetSelection(
                min(self.context.template_color1, self.combo_color_1.GetCount() - 1)
            )
            self.combo_color_2.SetSelection(
                min(self.context.template_color2, self.combo_color_2.GetCount() - 1)
            )
            self.check_values.SetValue(self.context.template_show_values)
            self.check_labels.SetValue(self.context.template_show_labels)
            self.combo_ops.SetSelection(
                min(self.context.template_optype, self.combo_ops.GetCount() - 1)
            )
            self.combo_param_1.SetSelection(
                min(self.context.template_param1, self.combo_param_1.GetCount() - 1)
            )
            self.combo_param_2.SetSelection(
                min(self.context.template_param2, self.combo_param_2.GetCount() - 1)
            )
            self.text_min_1.SetValue(self.context.template_min1)
            self.text_max_1.SetValue(self.context.template_max1)
            self.text_min_2.SetValue(self.context.template_min2)
            self.text_max_2.SetValue(self.context.template_max2)
            self.spin_count_1.SetValue(self.context.template_count1)
            self.spin_count_2.SetValue(self.context.template_count2)
            self.text_dim_1.SetValue(self.context.template_dim_1)
            self.text_dim_2.SetValue(self.context.template_dim_2)
            self.text_delta_1.SetValue(self.context.template_gap_1)
            self.text_delta_2.SetValue(self.context.template_gap_2)
            self.list_options_1.SetCheckedStrings(
                self.context.template_list1.split("|")
            )
            self.list_options_2.SetCheckedStrings(
                self.context.template_list2.split("|")
            )
        except (AttributeError, ValueError):
            pass

    def sync_fields(self):
        # Repopulate combos
        self.set_param_according_to_op(None)
        # And then setting it back to the defaults...
        self.combo_param_1.SetSelection(
            min(self.context.template_param1, self.combo_param_1.GetCount() - 1)
        )
        # Make sure units appear properly
        self.on_combo_1(None)
        self.combo_param_2.SetSelection(
            min(self.context.template_param2, self.combo_param_2.GetCount() - 1)
        )
        # Make sure units appear properly
        self.on_combo_2(None)

    @signal_listener("activate;device")
    def on_activate_device(self, origin, device):
        self.set_param_according_to_op(None)


class TemplateTool(MWindow):
    """
    Material-/Parameter Test routines
    """

    def __init__(self, *args, **kwds):
        super().__init__(720, 750, submenu="Laser-Tools", *args, **kwds)

        self.storage = Settings(self.context.kernel.name, "templates.cfg")
        self.storage.read_configuration()
        self.panel_instances = []
        self.primary_prop_panels = []
        self.panel_template = TemplatePanel(
            self,
            wx.ID_ANY,
            context=self.context,
            storage=self.storage,
        )

        self.panel_saveload = SaveLoadPanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )

        self.notebook_main = aui.AuiNotebook(
            self,
            -1,
            style=aui.AUI_NB_TAB_EXTERNAL_MOVE
            | aui.AUI_NB_SCROLL_BUTTONS
            | aui.AUI_NB_TAB_SPLIT
            | aui.AUI_NB_TAB_MOVE
            | aui.AUI_NB_BOTTOM,
        )
        # ARGGH, the color setting via the ArtProvider does only work
        # if you set the tabs to the bottom! wx.aui.AUI_NB_BOTTOM
        self.window_context.themes.set_window_colors(self.notebook_main)
        bg_std = self.window_context.themes.get("win_bg")
        bg_active = self.window_context.themes.get("highlight")
        self.notebook_main.GetArtProvider().SetColour(bg_std)
        self.notebook_main.GetArtProvider().SetActiveColour(bg_active)
        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)
        self.notebook_main.AddPage(self.panel_template, _("Generator"))

        self.panel_template.set_callback(self.set_node)
        self.add_module_delegate(self.panel_template)

        self.notebook_main.AddPage(self.panel_saveload, _("Templates"))
        self.panel_saveload.set_callback(self.callback_templates)
        self.add_module_delegate(self.panel_saveload)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_detective.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Parameter-Test"))
        self.restore_aspect()

    def callback_templates(self, command, param):
        # print (f"callback called with {command}, {param}")
        if command == "load":
            if param:
                self.panel_template.restore_settings(param)
                self.panel_template.sync_fields()
                return True
        elif command == "save":
            if param:
                self.panel_template.save_settings(param)
                return True
        elif command == "delete":
            if param:
                key = f"{param}"
                self.storage.delete_persistent("materialtest", key)
                self.storage.write_configuration()
                return True
        elif command == "get":
            choices = []
            for section in list(self.storage.keylist("materialtest")):
                choices.append(section)
            return choices

        return None

    def set_node(self, primary_node, secondary_node=None):
        def sort_priority(prop):
            prop_sheet, node = prop
            return (
                getattr(prop_sheet, "priority")
                if hasattr(prop_sheet, "priority")
                else 0
            )

        if primary_node is None:
            return
        busy = wx.BusyCursor()
        self.Freeze()
        primary_panels = []
        secondary_panels = []
        for property_sheet in self.context.lookup_all(
            f"property/{primary_node.__class__.__name__}/.*"
        ):
            if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                primary_node
            ):
                primary_panels.append((property_sheet, primary_node))
        found = len(primary_panels) > 0
        # If we did not have any hits and the node is a reference
        # then we fall back to the master. So if in the future we
        # would have a property panel dealing with reference-nodes
        # then this would no longer apply.
        if primary_node.type == "reference" and not found:
            snode = primary_node.node
            found = False
            for property_sheet in self.context.lookup_all(
                f"property/{snode.__class__.__name__}/.*"
            ):
                if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                    snode
                ):
                    primary_panels.append((property_sheet, snode))
        if secondary_node is not None:
            for property_sheet in self.context.lookup_all(
                f"property/{secondary_node.__class__.__name__}/.*"
            ):
                if not hasattr(property_sheet, "accepts") or property_sheet.accepts(
                    secondary_node
                ):
                    secondary_panels.append((property_sheet, secondary_node))

        primary_panels.sort(key=sort_priority, reverse=True)
        secondary_panels.sort(key=sort_priority, reverse=True)
        pages_to_instance = primary_panels + secondary_panels

        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
            self.remove_module_delegate(p)
        self.panel_instances.clear()

        # Delete all but the first and last page...
        while self.notebook_main.GetPageCount() > 2:
            self.notebook_main.DeletePage(1)
        # print(
        #     f"Adding {len(pages_to_instance)} pages to the notebook, remaining {self.notebook_main.GetPageCount()} pages: content={self.notebook_main.GetPageText(0)} and {self.notebook_main.GetPageText(1)}"
        # )
        # Add the primary property panels
        for prop_sheet, instance in pages_to_instance:
            page_panel = prop_sheet(
                self.notebook_main, wx.ID_ANY, context=self.context, node=instance
            )
            try:
                name = prop_sheet.name
            except AttributeError:
                name = instance.__class__.__name__

            self.notebook_main.InsertPage(1, page_panel, _(name))
            try:
                page_panel.set_widgets(instance)
            except AttributeError:
                pass
            self.add_module_delegate(page_panel)
            self.panel_instances.append(page_panel)
            try:
                page_panel.pane_show()
            except AttributeError:
                pass
            page_panel.Layout()
            try:
                page_panel.SetupScrolling()
            except AttributeError:
                pass

        self.Layout()
        self.Thaw()
        self.notebook_main.SetSelection(1)
        self.notebook_main.SetSelection(0)
        del busy

    def window_open(self):
        pass

    def window_close(self):
        for p in self.panel_instances:
            try:
                p.pane_hide()
            except AttributeError:
                pass
        # We do not remove the delegates, they will detach with the closing of the module.
        self.panel_instances.clear()

    @signal_listener("power_percent")
    @signal_listener("speed_min")
    @lookup_listener("service/device/active")
    def on_device_update(self, *args):
        self.panel_template.on_device_update()

    @staticmethod
    def submenu():
        return "Laser-Tools", "Parameter-Test"

    @staticmethod
    def helptext():
        return _("Figure out the right settings for your material")

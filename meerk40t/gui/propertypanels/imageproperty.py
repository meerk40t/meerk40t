# import threading
from copy import copy

import numpy as np
import wx
from PIL import Image, ImageEnhance, ImageOps

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH

# from meerk40t.gui.icons import icon_ignore
# from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.propertypanels.attributes import (
    IdPanel,
    PositionSizePanel,
    PreventChangePanel,
)
from meerk40t.gui.wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxListCtrl,
    wxRadioBox,
    wxStaticBitmap,
    wxStaticText,
)
from meerk40t.image.imagetools import img_to_polygons, img_to_rectangles
from meerk40t.kernel.kernel import Job
from meerk40t.svgelements import Color, Matrix

_ = wx.GetTranslation

# The default value needs to be true, as the static method will be called before init happened...
HAS_VECTOR_ENGINE = True


class ContourPanel(wx.Panel):
    name = _("Contour recognition")
    priority = 96

    @staticmethod
    def accepts(node):
        return hasattr(node, "as_image")

    def __init__(
        self,
        *args,
        context=None,
        node=None,
        simplified=False,
        direct_mode=False,
        **kwds,
    ):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.direct_mode = direct_mode
        self.check_enable_contrast = wxCheckBox(self, wx.ID_ANY, _("Enable"))
        self.button_reset_contrast = wxButton(self, wx.ID_ANY, _("Reset"))
        self.slider_contrast_contrast = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_contrast_contrast = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.slider_contrast_brightness = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_contrast_brightness = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.check_invert = wxCheckBox(self, wx.ID_ANY, _("Invert"))
        self.check_original = wxCheckBox(self, wx.ID_ANY, _("Original picture"))

        if simplified:
            self.check_original.Hide()

        self.text_minimum = TextCtrl(self, wx.ID_ANY, "", limited=True, check="float")
        self.text_maximum = TextCtrl(self, wx.ID_ANY, "", limited=True, check="float")
        self.check_inner = wxCheckBox(self, wx.ID_ANY, _("Ignore inner"))
        self.radio_simplify = wxRadioBox(
            self,
            wx.ID_ANY,
            label=_("Contour simplification"),
            choices=(_("None"), _("Visvalingam"), _("Douglas-Peucker")),
        )
        self.radio_method = wxRadioBox(
            self,
            wx.ID_ANY,
            label=_("Detection Method"),
            choices=(_("Polygons"), _("Bounding rectangles")),
        )

        self.check_auto = wxCheckBox(self, wx.ID_ANY, _("Automatic update"))
        self.button_update = wxButton(self, wx.ID_ANY, _("Update"))
        self.button_create = wxButton(self, wx.ID_ANY, _("Generate contours"))
        self.button_create_placement = wxButton(
            self, wx.ID_ANY, _("Generate placements")
        )
        placement_choices = (
            _("Edge (prefer short side)"),
            _("Edge (prefer long side)"),
            _("Center (unrotated)"),
            _("Center (rotated)"),
        )
        self.combo_placement = wxComboBox(
            self,
            wx.ID_ANY,
            choices=placement_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )

        self.bitmap_preview = wxStaticBitmap(self, wx.ID_ANY)
        self.label_info = wxStaticText(self, wx.ID_ANY)
        self.list_contours = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
            context=self.context,
            list_name="list_contours",
        )
        self.update_job = Job(
            process=self.refresh_preview_job,
            job_name="imageprop_contour",
            interval=0.5,
            times=1,
            run_main=True,
        )

        self.image = None
        self.matrix = None
        self.contours = []
        self.auto_update = self.context.setting(bool, "contour_autoupdate", True)
        self._changed = True
        self.make_raster = self.context.lookup("render-op/make_raster")
        self.parameters = {}
        self._pane_is_active = False
        self.__set_properties()
        self.__do_layout()
        self.__do_logic()
        self.set_widgets(self.node)

    def __do_logic(self):
        self.check_auto.Bind(wx.EVT_CHECKBOX, self.on_auto_check)
        self.check_original.Bind(wx.EVT_CHECKBOX, self.on_control_update)
        self.button_update.Bind(wx.EVT_BUTTON, self.on_refresh)
        self.button_create.Bind(wx.EVT_BUTTON, self.on_creation)
        self.button_create_placement.Bind(wx.EVT_BUTTON, self.on_creation_placement)
        self.button_reset_contrast.Bind(wx.EVT_BUTTON, self.on_button_reset_contrast)
        self.check_invert.Bind(wx.EVT_CHECKBOX, self.on_control_update)
        self.check_inner.Bind(wx.EVT_CHECKBOX, self.on_control_update)
        self.check_enable_contrast.Bind(wx.EVT_CHECKBOX, self.on_control_update)
        self.slider_contrast_brightness.Bind(
            wx.EVT_SLIDER, self.on_slider_contrast_brightness
        )
        self.slider_contrast_contrast.Bind(
            wx.EVT_SLIDER, self.on_slider_contrast_contrast
        )
        self.radio_method.Bind(wx.EVT_RADIOBOX, self.on_control_update)
        self.radio_simplify.Bind(wx.EVT_RADIOBOX, self.on_control_update)
        self.text_minimum.SetActionRoutine(self.on_control_update)
        self.text_maximum.SetActionRoutine(self.on_control_update)
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.list_contours.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list_selection)
        self.list_contours.Bind(wx.EVT_LIST_COL_CLICK, self.on_list_selection)
        self.list_contours.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(sizer_left, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_right, 2, wx.EXPAND, 0)

        sizer_right.Add(self.bitmap_preview, 4, wx.EXPAND, 0)
        sizer_right.Add(self.list_contours, 1, wx.EXPAND, 0)

        sizer_param_picture = StaticBoxSizer(self, wx.ID_ANY, _("Image:"), wx.VERTICAL)
        sizer_contrast = StaticBoxSizer(self, wx.ID_ANY, _("Contrast"), wx.VERTICAL)

        sizer_contrast_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_contrast_main.Add(self.check_enable_contrast, 0, 0, 0)
        sizer_contrast_main.Add(self.button_reset_contrast, 0, 0, 0)

        sizer_contrast_contrast = StaticBoxSizer(
            self, wx.ID_ANY, _("Contrast Amount"), wx.HORIZONTAL
        )
        sizer_contrast_contrast.Add(self.slider_contrast_contrast, 5, wx.EXPAND, 0)
        sizer_contrast_contrast.Add(self.text_contrast_contrast, 1, 0, 0)

        sizer_contrast_brightness = StaticBoxSizer(
            self, wx.ID_ANY, _("Brightness Amount"), wx.HORIZONTAL
        )
        sizer_contrast_brightness.Add(self.slider_contrast_brightness, 5, wx.EXPAND, 0)
        sizer_contrast_brightness.Add(self.text_contrast_brightness, 1, 0, 0)

        sizer_contrast.Add(sizer_contrast_main, 0, wx.EXPAND, 0)
        sizer_contrast.Add(sizer_contrast_contrast, 0, wx.EXPAND, 0)
        sizer_contrast.Add(sizer_contrast_brightness, 0, wx.EXPAND, 0)

        sizer_param_picture.Add(sizer_contrast, 0, wx.EXPAND, 0)
        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        option_sizer.Add(self.check_invert, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        option_sizer.Add(self.check_original, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_param_picture.Add(option_sizer, 0, wx.EXPAND, 0)

        sizer_param_contour = StaticBoxSizer(
            self, wx.ID_ANY, _("Parameters:"), wx.VERTICAL
        )

        min_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Minimal size:"), wx.HORIZONTAL)
        label1 = wxStaticText(self, wx.ID_ANY, "%")
        min_sizer.Add(self.text_minimum, 1, wx.EXPAND, 0)
        min_sizer.Add(label1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        max_sizer = StaticBoxSizer(self, wx.ID_ANY, _("Maximal size:"), wx.HORIZONTAL)
        label2 = wxStaticText(self, wx.ID_ANY, "%")
        max_sizer.Add(self.text_maximum, 1, wx.EXPAND, 0)
        max_sizer.Add(label2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        minmax_sizer = wx.BoxSizer(wx.HORIZONTAL)
        minmax_sizer.Add(min_sizer, 1, wx.EXPAND, 0)
        minmax_sizer.Add(max_sizer, 1, wx.EXPAND, 0)
        sizer_param_contour.Add(minmax_sizer, 0, wx.EXPAND, 0)

        sizer_param_contour.Add(self.check_inner, 0, wx.EXPAND, 0)
        sizer_param_contour.Add(self.radio_method, 0, wx.EXPAND, 0)
        sizer_param_contour.Add(self.radio_simplify, 0, wx.EXPAND, 0)

        sizer_param_update = StaticBoxSizer(
            self, wx.ID_ANY, _("Update:"), wx.HORIZONTAL
        )
        sizer_param_update.Add(self.check_auto, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_param_update.Add(self.button_update, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_generation = wx.BoxSizer(wx.HORIZONTAL)
        sizer_generation.Add(self.button_create, 0, wx.EXPAND, 0)
        sizer_generation.Add(self.button_create_placement, 0, wx.EXPAND, 0)
        sizer_generation.Add(self.combo_placement, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_left.Add(sizer_param_picture, 0, wx.EXPAND, 0)
        sizer_left.Add(sizer_param_contour, 0, wx.EXPAND, 0)
        sizer_left.Add(sizer_param_update, 0, wx.EXPAND, 0)
        sizer_left.Add(sizer_generation, 0, wx.EXPAND, 0)
        sizer_left.Add(self.label_info, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)

        self.__do_defaults()
        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def __do_defaults(self):
        self.check_auto.SetValue(self.auto_update)
        self.button_update.Enable(not self.auto_update)
        last_val = self.context.setting(
            int, "contour_placement", 1
        )  # Long side is default preference
        if last_val < 0 or last_val >= self.combo_placement.GetCount():
            last_val = 0
        self.combo_placement.SetSelection(last_val)

    def __set_properties(self):
        self.check_invert.SetToolTip(_("Invert the image before processing"))
        self.check_original.SetToolTip(
            _("Use the original image instead of the dithered one")
        )
        self.check_auto.SetToolTip(_("Automatically update the preview"))
        self.button_update.SetToolTip(_("Update the preview"))
        self.button_create.SetToolTip(_("Creates the recognized contour elements"))
        self.button_create_placement.SetToolTip(
            _("Creates the corresponding placements")
        )
        self.combo_placement.SetToolTip(_("Select the placement position"))
        self.check_enable_contrast.SetToolTip(_("Enable Contrast"))
        self.check_enable_contrast.SetValue(False)
        self.button_reset_contrast.SetToolTip(_("Reset Contrast"))
        self.slider_contrast_contrast.SetToolTip(_("Contrast amount"))
        self.text_contrast_contrast.SetToolTip(
            _("Contrast the lights and darks by how much?")
        )
        self.slider_contrast_brightness.SetToolTip(_("Brightness amount"))
        self.text_contrast_brightness.SetToolTip(
            _("Make the image how much more bright?")
        )
        self.text_minimum.SetToolTip(
            _(
                "What is the minimal size of objects (as percentage of the overall area)?"
            )
        )
        self.text_maximum.SetToolTip(
            _(
                "What is the maximal size of objects (as percentage of the overall area)?"
            )
        )
        self.check_inner.SetToolTip(
            _("Do you want to recognize objects inside of another object?")
        )
        self.radio_method.SetToolTip(
            _(
                "Do you want to create the contour itself or the minimal rectangle enclosing it?"
            )
        )
        self.radio_simplify.SetToolTip(
            _("Shall we try to reduce the number of points for the created contour?")
        )

        self.slider_contrast_brightness.SetMaxSize(wx.Size(200, -1))
        self.slider_contrast_contrast.SetMaxSize(wx.Size(200, -1))
        self.text_contrast_brightness.SetMaxSize(wx.Size(50, -1))
        self.text_contrast_contrast.SetMaxSize(wx.Size(50, -1))

        self.list_contours.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=55)
        self.list_contours.AppendColumn(
            _("Area"), format=wx.LIST_FORMAT_LEFT, width=100
        )
        self.list_contours.resize_columns()

        self.text_minimum.SetValue("2")
        self.text_maximum.SetValue("95")
        self.radio_method.SetSelection(0)
        self.radio_simplify.SetSelection(0)
        self.reset_contrast()

    def pane_hide(self):
        self.list_contours.save_column_widths()
        try:
            self.context.contour_placement = self.combo_placement.GetSelection()
        except RuntimeError:
            # Might have already been deleted...
            pass

    def pane_deactive(self):
        self._pane_is_active = False

    def pane_active(self):
        self._pane_is_active = True
        if self.auto_update and self._pane_is_active:
            self.refresh_preview()

    def pane_show(self):
        if self.auto_update and self._pane_is_active:
            self.refresh_preview()

    def _set_widgets_hidden(self):
        self.Hide()

    def set_widgets(self, node):
        self.node = node
        if self.node is None:
            return
        self.refresh_preview()

    def reset_contrast(self):
        contrast = 0
        brightness = 0
        self.slider_contrast_contrast.SetValue(contrast)
        self.text_contrast_contrast.SetValue(str(contrast))
        self.slider_contrast_brightness.SetValue(brightness)
        self.text_contrast_brightness.SetValue(str(brightness))

    def on_button_reset_contrast(self, event=None):
        self.reset_contrast()
        self.on_control_update(None)

    def on_slider_contrast_contrast(self, event=None):
        contrast = int(self.slider_contrast_contrast.GetValue())
        self.text_contrast_contrast.SetValue(str(contrast))
        if event and (
            not self.context.process_while_sliding and wx.GetMouseState().LeftIsDown()
        ):
            event.Skip()
            return

        self.on_control_update(None)

    def on_slider_contrast_brightness(self, event=None):
        brightness = int(self.slider_contrast_brightness.GetValue())
        self.text_contrast_brightness.SetValue(str(brightness))
        if event and (
            not self.context.process_while_sliding and wx.GetMouseState().LeftIsDown()
        ):
            event.Skip()
            return
        self.on_control_update(None)

    def on_auto_check(self, event):
        self.auto_update = self.check_auto.GetValue()
        self.context.contour_autoupdate = self.auto_update

        self.button_update.Enable(not self.auto_update)
        if self.auto_update:
            self.refresh_preview()

    def on_creation(self, event):
        for idx, (geom, area) in enumerate(self.contours):
            node = PathNode(
                geometry=geom,
                stroke=Color("blue"),
                label=f"Contour {self.node.display_label()} #{idx+1}",
            )
            self.context.elements.elem_branch.add_node(node)
            # print (f"Having added: {node.display_label()}")
        self.context.elements.signal("refresh_scene", "Scene")

    def on_creation_placement(self, event):
        def get_place_parameters(geom, method):
            points = list(geom.as_points())
            nx = None
            mx = None
            ny = None
            my = None
            for pt in points:
                if nx is None:
                    nx = pt.real
                    mx = pt.real
                    ny = pt.imag
                    my = pt.imag
                else:
                    nx = min(nx, pt.real)
                    mx = max(mx, pt.real)
                    ny = min(ny, pt.imag)
                    my = max(my, pt.imag)

            # The geometry points are order in such a way,
            # that the point with the smallest X-value comes first and then follows the rectangle clockwise
            side1 = geom.distance(points[0], points[1])
            side2 = geom.distance(points[1], points[2])
            if method in (0, 1):
                if method == 0:
                    # If the preference is for a long side then our reference point is pt0 if side1 is long and pt1 if side1 is short
                    refidx = 0 if side1 < side2 else 1
                else:
                    # If the preference is for a short side then our reference point is pt1 if side1 is long and pt0 if side1 is short
                    refidx = 1 if side1 < side2 else 0
                ref_x = points[refidx].real
                ref_y = points[refidx].imag
                rotation_angle = geom.angle(points[refidx], points[refidx + 1])
                place_corner = 0
            elif method == 2:  # center - unrotated
                ref_x = (nx + mx) / 2
                ref_y = (ny + my) / 2
                rotation_angle = 0
                place_corner = 4
            elif method == 3:  # center - rotated
                ref_x = (nx + mx) / 2
                ref_y = (ny + my) / 2
                rotation_angle = geom.angle(points[0], points[1])
                place_corner = 4
            return ref_x, ref_y, rotation_angle, place_corner

        method = self.combo_placement.GetSelection()
        if method < 0:
            return
        for idx, (geom, area) in enumerate(self.contours):
            ref_x, ref_y, rotation_angle, place_corner = get_place_parameters(
                geom, method
            )
            self.context.elements.op_branch.add(
                type="place point",
                label=f"Contour #{idx+1}",
                x=ref_x,
                y=ref_y,
                rotation=rotation_angle,
                corner=place_corner,
            )

        self.context.elements.signal("refresh_scene")

    def on_refresh(self, event):
        self._changed = True
        self.refresh_preview()

    def on_control_update(self, event=None):
        self._changed = True
        # The following controls will only be used
        # if we have surrounding rectangles selected
        flag = self.radio_method.GetSelection() == 0
        for ctrl in (self.radio_simplify,):
            ctrl.Enable(flag)
        for ctrl in (self.button_create_placement, self.combo_placement):
            ctrl.Enable(not flag)
        if self.auto_update and self._pane_is_active:
            self.refresh_preview()

    def refresh_preview_job(self):
        if self.make_raster is None or not self._changed:
            return
        # That job may come too late, when the panel has already be destroyed,
        # so just a simple check:
        try:
            _dummy = self.check_invert.GetValue()
        except RuntimeError:
            return
        self.gather_parameters()
        self.update_image()
        self.calculate_contours()
        self.populate_list()
        self.display_contours()
        self._changed = False

    def refresh_preview(self):
        if self._pane_is_active:
            if self.direct_mode:
                self.update_job()
            else:
                self.context.schedule(self.update_job)

    def gather_parameters(self):
        self.parameters["img_invert"] = self.check_invert.GetValue()
        self.parameters["img_original"] = self.check_original.GetValue()
        self.parameters["img_usecontrast"] = self.check_enable_contrast.GetValue()
        self.parameters["img_contrast"] = self.slider_contrast_contrast.GetValue()
        self.parameters["img_brightness"] = self.slider_contrast_brightness.GetValue()
        self.parameters["cnt_method"] = self.radio_method.GetSelection()
        self.parameters["cnt_ignoreinner"] = self.check_inner.GetValue()
        try:
            self.parameters["cnt_minimum"] = float(self.text_minimum.GetValue())
        except ValueError:
            self.parameters["cnt_minimum"] = 2
        try:
            self.parameters["cnt_maximum"] = float(self.text_maximum.GetValue())
        except ValueError:
            self.parameters["cnt_maximum"] = 95
        self.parameters["cnt_simplify"] = self.radio_simplify.GetSelection()
        # We are on pixel level
        self.parameters["cnt_threshold"] = 0.25

    def update_image(self):
        if self.parameters["img_original"]:
            if self.image.mode == "I":
                image = self.image._as_convert_image_to_grayscale()
            else:
                image = self.node.image.convert("L")
            self.matrix = self.node.matrix
        else:
            reapply = False
            remembered_dither = self.node.dither
            if remembered_dither:
                reapply = True
                self.node.dither = False
                self.node.update(None)

            image = self.node.active_image
            if image is None:
                if reapply:
                    self.node.dither = remembered_dither
                self.image = None
                return
            self.matrix = self.node.active_matrix
            if reapply:
                self.node.dither = remembered_dither
                self.node.update(None)

        if self.parameters["img_invert"]:
            image = ImageOps.invert(image)
        if self.parameters["img_usecontrast"]:
            try:
                contrast = ImageEnhance.Contrast(image)
                c = (self.parameters["img_contrast"] + 128.0) / 128.0
                image = contrast.enhance(c)
            except ValueError:
                # Not available for this type of image
                pass

            try:
                brightness = ImageEnhance.Brightness(image)
                b = (self.parameters["img_brightness"] + 128.0) / 128.0
                image = brightness.enhance(b)
            except ValueError:
                # Not available for this type of image
                pass
        self.image = image

    def calculate_contours(self):
        import time

        self.contours.clear()
        if self.image is None:
            return
        t_a = time.perf_counter()

        method = self.parameters["cnt_method"]
        if method == 0:
            self.contours = img_to_polygons(
                self.image,
                minimal=self.parameters["cnt_minimum"],
                maximal=self.parameters["cnt_maximum"],
                ignoreinner=self.parameters["cnt_ignoreinner"],
                needs_invert=True,
            )
        else:
            self.contours = img_to_rectangles(
                self.image,
                minimal=self.parameters["cnt_minimum"],
                maximal=self.parameters["cnt_maximum"],
                ignoreinner=self.parameters["cnt_ignoreinner"],
                needs_invert=True,
            )
        if len(self.contours) == 0 or len(self.contours[0]) != 2:
            self.label_info.SetLabel(_("No contours found."))
            return
        for idx, (geom, area) in enumerate(self.contours):
            if method == 0:
                simple = self.parameters["cnt_simplify"]
                # We are on pixel level
                threshold = self.parameters["cnt_threshold"]
                if simple == 1:
                    # Let's try Visvalingam line simplification
                    geom = geom.simplify_geometry(threshold=threshold)
                elif simple == 2:
                    # Use Douglas-Peucker instead
                    geom = geom.simplify(threshold)
            geom.transform(self.matrix)
            self.contours[idx] = (geom, area)

        t_b = time.perf_counter()

        self.label_info.SetLabel(
            _("Contours generated: {count} in {duration}").format(
                count=len(self.contours), duration=f"{t_b-t_a:.2f} sec"
            )
        )

    def on_resize(self, event):
        event.Skip()
        if self.auto_update and self._pane_is_active:
            idx = self.list_contours.GetFirstSelected()
            self.display_contours(highlight_index=idx)

    def on_right_click(self, event):
        def compare_contour(operation, index, this_area, idx, area):
            if operation == "this":
                return idx == index
            elif operation == "others":
                return idx != index
            elif operation == "smaller":
                return area < this_area
            elif operation == "bigger":
                return area > this_area
            return False

        def delete_contours(operation, index):
            def handler(event):
                this_area = self.contours[index][1]
                to_be_deleted = [
                    idx
                    for idx, (_, area) in enumerate(self.contours)
                    if compare_contour(operation, index, this_area, idx, area)
                ]
                for idx in reversed(to_be_deleted):
                    self.contours.pop(idx)
                self.populate_list()
                self.display_contours()

            return handler

        index = self.list_contours.GetFirstSelected()
        if index < 0:
            return
        menu = wx.Menu()
        operations = [
            ("this", _("Delete this contour")),
            ("others", _("Delete all others")),
            ("bigger", _("Delete all bigger")),
            ("smaller", _("Delete all smaller")),
        ]

        for op, label in operations:
            item = menu.Append(wx.ID_ANY, label)
            self.Bind(wx.EVT_MENU, delete_contours(op, index), item)

        self.PopupMenu(menu)
        menu.Destroy()

    def populate_list(self):
        self.list_contours.DeleteAllItems()
        for idx, (geom, area) in enumerate(self.contours):
            list_id = self.list_contours.InsertItem(
                self.list_contours.GetItemCount(), f"#{idx + 1}"
            )
            self.list_contours.SetItem(list_id, 1, f"{area:.2f}%")

    def display_contours(self, highlight_index=-1):
        if self.make_raster is None:
            return
        if self.image is None:
            self.bitmap_preview.SetBitmap(wx.NullBitmap)
            return
        copynode = ImageNode(
            image=self.image, matrix=self.matrix, dither=False, prevent_crop=True
        )
        data = [copynode]
        for idx, (geom, area) in enumerate(self.contours):
            node = PathNode(
                geometry=geom,
                stroke=Color("red") if highlight_index == idx else Color("blue"),
                fill=Color("yellow") if highlight_index == idx else None,
                label=f"Contour {self.node.display_label()} #{idx+1} [{area:.2f}%]",
            )
            data.append(node)
        bounds = Node.union_bounds(data, attr="bounds")
        width, height = self.bitmap_preview.GetClientSize()
        while width > 1024 or height > 1024:
            width = width // 2
            height = height // 2
        width = max(1, width)
        height = max(1, height)
        try:
            bit_map = self.make_raster(
                data,
                bounds,
                width=width,
                height=height,
                bitmap=True,
                keep_ratio=True,
            )
        except Exception:
            return
        self.bitmap_preview.SetBitmap(bit_map)

    def on_list_selection(self, event):
        idx = self.list_contours.GetFirstSelected()
        self.display_contours(highlight_index=idx)


class KeyholePanel(wx.Panel):
    name = _("Keyhole")
    priority = 5

    @staticmethod
    def accepts(node):
        return hasattr(node, "as_image")

    def __init__(self, *args, context=None, node=None, **kwds):
        # begin wxGlade: LayerSettingPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.button_release = wxButton(self, wx.ID_ANY, _("Remove keyhole"))
        self.__set_properties()
        self.__do_layout()
        self.button_release.Bind(wx.EVT_BUTTON, self.on_release)
        self.set_widgets(self.node)

    def __do_layout(self):
        # begin wxGlade: PositionPanel.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_release = StaticBoxSizer(self, wx.ID_ANY, _("Keyhole:"), wx.HORIZONTAL)
        sizer_release.Add(self.button_release, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_main.Add(sizer_release, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def __set_properties(self):
        self.button_release.SetToolTip(
            _("Remove the keyhole and show the complete image")
        )

    def pane_hide(self):
        pass

    def pane_show(self):
        pass

    def _set_widgets_hidden(self):
        self.Hide()

    def set_widgets(self, node):
        self.node = node
        if self.node.keyhole_reference is None:
            self.button_release.Enable(False)
        else:
            self.button_release.Enable(True)
        self.Show()

    def on_release(self, event):
        elements = self.context.elements
        rid = self.node.keyhole_reference
        elements.deregister_keyhole(rid, self.node)
        self.set_widgets(self.node)
        elements.process_keyhole_updates(self.context)


class CropPanel(wx.Panel):
    name = _("Crop")
    priority = 5

    @staticmethod
    def accepts(node):
        if not hasattr(node, "as_image"):
            return False
        return any(n.get("name") == "crop" for n in node.operations)

    def __init__(self, *args, context=None, node=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self._width = None
        self._height = None
        self._bounds = None
        self._cropleft = 0
        self._cropright = 0
        self._cropbottom = 0
        self._croptop = 0
        self.op = None
        self._no_update = False

        self.check_enable_crop = wxCheckBox(self, wx.ID_ANY, _("Enable"))
        self.button_reset = wxButton(self, wx.ID_ANY, _("Reset"))

        self.label_info = wxStaticText(self, wx.ID_ANY, "--")

        self.slider_left = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.slider_right = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.slider_top = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.slider_bottom = wx.Slider(
            self, wx.ID_ANY, 0, -127, 127, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_left = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.text_right = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.text_top = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)
        self.text_bottom = TextCtrl(self, wx.ID_ANY, style=wx.TE_READONLY)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_reset, self.button_reset)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_enable_crop, self.check_enable_crop)
        self.Bind(wx.EVT_SLIDER, self.on_slider_left, self.slider_left)
        self.Bind(wx.EVT_SLIDER, self.on_slider_right, self.slider_right)
        self.Bind(wx.EVT_SLIDER, self.on_slider_top, self.slider_top)
        self.Bind(wx.EVT_SLIDER, self.on_slider_bottom, self.slider_bottom)

        flag = False
        self.activate_controls(flag)
        self.set_widgets(node)

    def activate_controls(self, flag):
        self.button_reset.Enable(flag)
        self.slider_left.Enable(flag)
        self.slider_right.Enable(flag)
        self.slider_top.Enable(flag)
        self.slider_bottom.Enable(flag)

    def set_widgets(self, node):
        if self.node is None:
            self.label_info.SetLabel("")
            self.Hide()
            return
        else:
            self.Show()
        self._no_update = True
        self.node = node
        self.op = None
        self._width, self._height = self.node.image.size
        for ctl in (self.slider_left, self.slider_right):
            ctl.SetMin(0)
            ctl.SetMax(self._width)
        for ctl in (self.slider_top, self.slider_bottom):
            ctl.SetMin(0)
            ctl.SetMax(self._height)

        self._bounds = [0, 0, self._width, self._height]
        flag = False
        for n in node.operations:
            if n.get("name") == "crop":
                self.op = n
                break
        self._width, self._height = self.node.image.size
        self.label_info.SetLabel(f"{self._width} x {self._height} px")
        if self.op is not None:
            flag = self.op["enable"]
            self._bounds = self.op["bounds"]
            if self._bounds is None:
                self._bounds = [0, 0, self._width, self._height]
                self.op["bounds"] = self._bounds

        self.check_enable_crop.SetValue(flag)
        self.activate_controls(flag)
        # We need to set the internal variables, as otherwise recalc will take place
        self._cropleft = self._bounds[0]
        self._cropright = self._width - self._bounds[2]

        self._croptop = self._bounds[1]
        self._cropbottom = self._height - self._bounds[3]
        # print (f"From {self._bounds} to l={self.cropleft}, r={self.cropright}, t={self.croptop}, b={self.cropbottom}")

        self.set_slider_limits("lrtb", False)

        self._no_update = False

    def __set_properties(self):
        self.slider_left.SetToolTip(
            _("How many pixels do you want to crop from the left?")
        )
        self.slider_right.SetToolTip(
            _("How many pixels do you want to crop from the right?")
        )
        self.slider_top.SetToolTip(
            _("How many pixels do you want to crop from the top?")
        )
        self.slider_bottom.SetToolTip(
            _("How many pixels do you want to crop from the bottom?")
        )

    def __do_layout(self):
        # begin wxGlade: ContrastPanel.__do_layout
        sizer_main = StaticBoxSizer(self, wx.ID_ANY, _("Image-Dimensions"), wx.VERTICAL)
        sizer_info = wx.BoxSizer(wx.HORIZONTAL)
        sizer_info.Add(self.check_enable_crop, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_info.Add(self.button_reset, 0, wx.EXPAND, 0)
        sizer_info.Add(self.label_info, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_left = wx.BoxSizer(wx.HORIZONTAL)
        sizer_right = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bottom = wx.BoxSizer(wx.HORIZONTAL)

        lbl_left = wxStaticText(self, wx.ID_ANY, _("Left"))
        lbl_left.SetMinSize(dip_size(self, 60, -1))
        lbl_right = wxStaticText(self, wx.ID_ANY, _("Right"))
        lbl_right.SetMinSize(dip_size(self, 60, -1))
        lbl_bottom = wxStaticText(self, wx.ID_ANY, _("Bottom"))
        lbl_bottom.SetMinSize(dip_size(self, 60, -1))
        lbl_top = wxStaticText(self, wx.ID_ANY, _("Top"))
        lbl_top.SetMinSize(dip_size(self, 60, -1))

        self.text_left.SetMaxSize(dip_size(self, 60, -1))
        self.text_right.SetMaxSize(dip_size(self, 60, -1))
        self.text_top.SetMaxSize(dip_size(self, 60, -1))
        self.text_bottom.SetMaxSize(dip_size(self, 60, -1))

        sizer_left.Add(lbl_left, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_left.Add(self.slider_left, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_left.Add(self.text_left, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_right.Add(lbl_right, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_right.Add(self.slider_right, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_right.Add(self.text_right, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_top.Add(lbl_top, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_top.Add(self.slider_top, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_top.Add(self.text_top, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_bottom.Add(lbl_bottom, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_bottom.Add(self.slider_bottom, 4, wx.ALIGN_CENTER_VERTICAL)
        sizer_bottom.Add(self.text_bottom, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer_main.Add(sizer_info, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_left, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_right, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_top, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_bottom, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

    def on_button_reset(self, event):
        if self.node is None:
            return
        w, h = self.node.image.size
        self._bounds = [0, 0, w, h]
        self._cropleft = 0
        self._cropright = 0
        self._croptop = 0
        self._cropbottom = 0
        self.op["bounds"] = self._bounds
        self.set_slider_limits("lrtb")
        self.context.elements.do_image_update(self.node, self.context)

    def on_check_enable_crop(self, event=None):
        flag = self.check_enable_crop.GetValue()
        if flag:
            if self.op is None:
                w, h = self.node.image.size
                self._width = w
                self._height = h
                self.op = {"name": "crop", "enable": True, "bounds": [0, 0, w, h]}
                self.node.operations.append(self.op)
                self.set_slider_limits("lrtb", False)
                last = self._no_update
                self._no_update = True
                self.cropleft = 0
                self.cropright = 0
                self.croptop = 0
                self.cropbottom = 0
                self._no_update = last
            else:
                self.op["enable"] = flag
        else:
            if self.op is not None:
                self.op["enable"] = flag
        if self.op is not None and not self._no_update:
            self.context.elements.do_image_update(self.node, self.context)

        self.activate_controls(flag)

    def on_slider_left(self, event=None):
        if event and (
            not self.context.process_while_sliding and wx.GetMouseState().LeftIsDown()
        ):
            event.Skip()
            return
        self.cropleft = self.slider_left.GetValue()

    def on_slider_right(self, event=None):
        if event and (
            not self.context.process_while_sliding and wx.GetMouseState().LeftIsDown()
        ):
            event.Skip()
            return
        self.cropright = self.slider_right.GetValue()

    def on_slider_top(self, event=None):
        # Wait until the user has stopped to move the slider
        if event and (
            not self.context.process_while_sliding and wx.GetMouseState().LeftIsDown()
        ):
            event.Skip()
            return
        self.croptop = self.slider_top.GetValue()

    def on_slider_bottom(self, event=None):
        if event and (
            not self.context.process_while_sliding and wx.GetMouseState().LeftIsDown()
        ):
            event.Skip()
            return
        self.cropbottom = self.slider_bottom.GetValue()

    def set_slider_limits(self, pattern, constraint=True):
        if "l" in pattern:
            value = self._width - self.cropright
            self.slider_left.SetMin(0)
            self.slider_left.SetMax(value - 1 if constraint else self._width)
            if self.cropleft != self.slider_left.GetValue():
                self.slider_left.SetValue(int(self.cropleft))
                dvalue = self.cropleft
                if dvalue == 0:
                    self.text_left.SetValue("---")
                else:
                    self.text_left.SetValue(f"> {dvalue} px")
        if "r" in pattern:
            value = self._width - self.cropleft
            self.slider_right.SetMin(0)
            self.slider_right.SetMax(value - 1 if constraint else self._width)
            if self.cropright != self.slider_right.GetValue():
                self.slider_right.SetValue(int(self.cropright))
                dvalue = self.cropright
                if dvalue == 0:
                    self.text_right.SetValue("---")
                else:
                    self.text_right.SetValue(f"> {dvalue} px")
        if "t" in pattern:
            value = self._height - self.cropbottom
            self.slider_top.SetMin(0)
            self.slider_top.SetMax(value - 1 if constraint else self._height)
            if self.croptop != self.slider_top.GetValue():
                self.slider_top.SetValue(int(self.croptop))
                dvalue = self.croptop
                if dvalue == 0:
                    self.text_top.SetValue("---")
                else:
                    self.text_top.SetValue(f"> {dvalue} px")
        if "b" in pattern:
            value = self._height - self.croptop
            self.slider_bottom.SetMin(0)
            self.slider_bottom.SetMax(value - 1 if constraint else self._height)
            if self.cropbottom != self.slider_bottom.GetValue():
                self.slider_bottom.SetValue(int(self.cropbottom))
                dvalue = self.cropbottom
                if dvalue == 0:
                    self.text_bottom.SetValue("---")
                else:
                    self.text_bottom.SetValue(f"> {dvalue} px")

    def _setbounds(self):
        if self.op is None:
            return

        self.op["bounds"][0] = self.cropleft
        self.op["bounds"][2] = self._width - self.cropright
        self.op["bounds"][1] = self.croptop
        self.op["bounds"][3] = self._height - self.cropbottom
        self._bounds = self.op["bounds"]
        # print (f"width: {self._width} from left: {self.cropleft}, from right {self.cropright}: {self.op['bounds'][0]} - {self.op['bounds'][2]}")
        # print (f"height: {self._height} from top: {self.croptop}, from bottom {self.cropbottom}: {self.op['bounds'][1]} - {self.op['bounds'][3]}")
        if not self._no_update:
            self.context.elements.do_image_update(self.node, self.context)

    @property
    def cropleft(self):
        return self._cropleft

    @cropleft.setter
    def cropleft(self, value):
        self._cropleft = value
        if self.slider_left.GetValue() != value:
            self.slider_left.SetValue(int(value))
        if value == 0:
            self.text_left.SetValue("---")
        else:
            self.text_left.SetValue(f"> {value} px")
        # We need to adjust the boundaries of the right slider.
        self.set_slider_limits("r")
        self._setbounds()

    @property
    def cropright(self):
        return self._cropright

    @cropright.setter
    def cropright(self, value):
        self._cropright = value
        if self.slider_right.GetValue() != value:
            self.slider_right.SetValue(int(value))
        if value == 0:
            self.text_right.SetValue("---")
        else:
            self.text_right.SetValue(f"{value} px <")
        # We need to adjust the boundaries of the left slider.
        self.set_slider_limits("l")
        self._setbounds()

    @property
    def croptop(self):
        return self._croptop

    @croptop.setter
    def croptop(self, value):
        # print(f"Set top to: {value}")
        self._croptop = value
        if self.slider_top.GetValue() != value:
            self.slider_top.SetValue(int(value))
        if value == 0:
            self.text_top.SetValue("---")
        else:
            self.text_top.SetValue(f"> {value} px")
        # We need to adjust the boundaries of the bottom slider.
        self.set_slider_limits("b")
        self._setbounds()

    @property
    def cropbottom(self):
        return self._cropbottom

    @cropbottom.setter
    def cropbottom(self, value):
        # print(f"Set top to: {value}")
        self._cropbottom = value
        if self.slider_bottom.GetValue() != value:
            self.slider_bottom.SetValue(int(value))
        if value == 0:
            self.text_bottom.SetValue("---")
        else:
            self.text_bottom.SetValue(f"{value} px <")
        # We need to adjust the boundaries of the top slider.
        self.set_slider_limits("t")
        self._setbounds()


class ImageModificationPanel(ScrolledPanel):
    name = _("Modification")
    priority = 90

    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.scripts = []
        choices = []
        for entry in list(self.context.match("raster_script/.*", suffix=True)):
            self.scripts.append(entry)
            choices.append(_("Apply {entry}").format(entry=entry))
        self.combo_scripts = wxComboBox(
            self, wx.ID_ANY, choices=choices, style=wx.CB_READONLY | wx.CB_DROPDOWN
        )
        self.combo_scripts.SetSelection(0)
        self.button_apply = wxButton(self, wx.ID_ANY, _("Apply Script"))
        self.button_apply.SetToolTip(
            _("Apply image modification script\nRight click: append to existing script")
        )
        self.button_clear = wxButton(self, wx.ID_ANY, _("Clear"))
        self.button_clear.SetToolTip(_("Remove all image operations"))
        self.list_operations = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
            context=self.context,
            list_name="list_imageoperations",
        )

        self._do_layout()
        self._do_logic()
        self.set_widgets(node)

    def _do_layout(self):
        self.list_operations.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_operations.AppendColumn(
            _("Action"), format=wx.LIST_FORMAT_LEFT, width=65
        )
        self.list_operations.AppendColumn(
            _("Active"), format=wx.LIST_FORMAT_LEFT, width=25
        )
        self.list_operations.AppendColumn(
            _("Parameters"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_operations.resize_columns()
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_script = StaticBoxSizer(
            self, wx.ID_ANY, _("Raster-Wizard"), wx.HORIZONTAL
        )

        sizer_script.Add(self.combo_scripts, 1, wx.EXPAND, 0)
        sizer_script.Add(self.button_apply, 0, wx.EXPAND, 0)
        sizer_script.Add(self.button_clear, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_script, 0, wx.EXPAND, 0)
        sizer_main.Add(self.list_operations, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()

    def _do_logic(self):
        self.button_apply.Bind(wx.EVT_BUTTON, self.on_apply_replace)
        self.button_apply.Bind(wx.EVT_RIGHT_DOWN, self.on_apply_append)
        self.button_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        self.list_operations.Bind(wx.EVT_RIGHT_DOWN, self.on_list_menu)

    @staticmethod
    def accepts(node):
        return hasattr(node, "as_image")

    def set_widgets(self, node=None):
        self.node = node
        if node is None:
            return
        self.fill_operations()

    def fill_operations(self):
        self.list_operations.DeleteAllItems()
        idx = 0
        for op in self.node.operations:
            idx += 1
            list_id = self.list_operations.InsertItem(
                self.list_operations.GetItemCount(), f"#{idx}"
            )
            self.list_operations.SetItem(list_id, 1, op["name"])
            self.list_operations.SetItem(list_id, 2, "x" if op["enable"] else "-")
            self.list_operations.SetItem(list_id, 3, str(op))

    def on_clear(self, event):
        self.node.operations = []
        self.update_node()

    def apply_script(self, index, addition):
        if index < 0 or index >= len(self.scripts):
            return
        script = self.scripts[index]
        raster_script = self.context.lookup(f"raster_script/{script}")
        if not addition:
            self.node.operations = []
        for entry in raster_script:
            self.node.operations.append(entry)
        self.update_node()

    def update_node(self):
        self.context.elements.emphasized()
        self.context.elements.do_image_update(self.node, self.context)
        self.context.signal("element_property_force", self.node)
        # self.context.signal("selected", self.node)
        self.fill_operations()

    def on_apply_replace(self, event):
        idx = self.combo_scripts.GetSelection()
        if idx >= 0:
            self.apply_script(idx, False)

    def on_apply_append(self, event):
        idx = self.combo_scripts.GetSelection()
        if idx >= 0:
            self.apply_script(idx, True)

    def on_list_menu(self, event):
        def on_delete(index):
            def check(event):
                self.node.operations.pop(index)
                self.update_node()

            return check

        def on_enable(index):
            def check(event):
                self.node.operations[index]["enable"] = not self.node.operations[index][
                    "enable"
                ]
                self.update_node()

            return check

        def on_op_insert(index, op):
            def check(event):
                self.node.operations.insert(index, op)
                self.update_node()

            return check

        def on_op_append(index, op):
            def check(event):
                self.node.operations.append(op)
                self.update_node()

            return check

        selected = self.list_operations.GetFirstSelected()

        possible_ops = [
            {"name": "crop", "enable": True, "bounds": None},
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            },
            {"name": "auto_contrast", "enable": True, "cutoff": 3},
            {"name": "contrast", "enable": True, "contrast": 25, "brightness": 25},
            {
                "name": "unsharp_mask",
                "enable": True,
                "percent": 500,
                "radius": 4,
                "threshold": 0,
            },
            {
                "name": "tone",
                "type": "spline",
                "enable": True,
                "values": [[0, 0], [100, 150], [255, 255]],
            },
            {"name": "gamma", "enable": True, "factor": 3.5},
            {"name": "edge_enhance", "enable": False},
            {
                "name": "halftone",
                "enable": True,
                "black": True,
                "sample": 10,
                "angle": 22,
                "oversample": 2,
            },
            {"name": "dither", "enable": True, "type": "Floyd-Steinberg"},
        ]
        devmode = self.context.root.setting(bool, "developer_mode", False)
        menu = wx.Menu()
        if selected >= 0:
            # Edit-Part
            menuitem = menu.Append(
                wx.ID_ANY, _("Delete item"), _("Will delete the current entry")
            )
            self.Bind(wx.EVT_MENU, on_delete(selected), id=menuitem.GetId())

            menuitem = menu.Append(
                wx.ID_ANY,
                _("Enable"),
                _("Toggles enable-status of operation"),
                kind=wx.ITEM_CHECK,
            )
            menuitem.Check(self.node.operations[selected]["enable"])
            self.Bind(wx.EVT_MENU, on_enable(selected), id=menuitem.GetId())
            if devmode:
                menu.AppendSeparator()
                for op in possible_ops:
                    menuitem = menu.Append(
                        wx.ID_ANY,
                        _("Insert {op}").format(op=op["name"]),
                        _("Will insert this operation before the current entry"),
                    )
                    self.Bind(
                        wx.EVT_MENU, on_op_insert(selected, op), id=menuitem.GetId()
                    )
                menu.AppendSeparator()
        if devmode:
            for op in possible_ops:
                menuitem = menu.Append(
                    wx.ID_ANY,
                    _("Append {op}").format(op=op["name"]),
                    _("Will append this operation to the end of the list"),
                )
                self.Bind(wx.EVT_MENU, on_op_append(selected, op), id=menuitem.GetId())

        if menu.MenuItemCount != 0:
            self.PopupMenu(menu)
            menu.Destroy()

    def pane_show(self):
        self.list_operations.load_column_widths()
        self.fill_operations()

    def pane_active(self):
        self.fill_operations()

    def pane_hide(self):
        self.list_operations.save_column_widths()

    def signal(self, signalstr, myargs):
        return


class ImageVectorisationPanel(ScrolledPanel):
    name = _("Vectorisation")
    priority = 95

    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # self.vector_lock = threading.Lock()
        # self.alive = True
        # Only display if we have a vector engine
        self._pane_is_active = False
        make_vector = self.context.kernel.lookup("render-op/make_vector")
        if make_vector:
            global HAS_VECTOR_ENGINE
            HAS_VECTOR_ENGINE = True
        if not make_vector:
            main_sizer.Add(
                wxStaticText(
                    self, wx.ID_ANY, "No vector engine installed, you need potrace"
                ),
                1,
                wx.EXPAND,
                0,
            )
            self.SetSizer(main_sizer)
            main_sizer.Fit(self)
            self.Layout()
            self.Centre()
            return

        sizer_options = StaticBoxSizer(self, wx.ID_ANY, _("Options"), wx.VERTICAL)
        main_sizer.Add(sizer_options, 1, wx.EXPAND, 0)

        sizer_turn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(sizer_turn, 0, wx.EXPAND, 0)

        label_turn = wxStaticText(self, wx.ID_ANY, _("Turnpolicy"))
        label_turn.SetMinSize(dip_size(self, 70, -1))
        sizer_turn.Add(label_turn, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.turn_choices = [
            "Black",
            "White",
            "Left",
            "Right",
            "Minority",
            "Majority",
            "Random",
        ]
        self.combo_turnpolicy = wxComboBox(
            self,
            wx.ID_ANY,
            choices=self.turn_choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_turnpolicy.SetToolTip(
            _(
                "This parameter determines how to resolve ambiguities during decomposition of bitmaps into paths.\n\n"
                + "BLACK: prefers to connect black (foreground) components.\n"
                + "WHITE: prefers to connect white (background) components.\n"
                + "LEFT: always take a left turn.\n"
                + "RIGHT: always take a right turn.\n"
                + "MINORITY: prefers to connect the color (black or white) that occurs least frequently in a local neighborhood of the current position.\n"
                + "MAJORITY: prefers to connect the color (black or white) that occurs most frequently in a local neighborhood of the current position.\n"
                + "RANDOM: choose randomly."
            )
        )
        self.combo_turnpolicy.SetSelection(4)
        sizer_turn.Add(self.combo_turnpolicy, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_turd = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(sizer_turd, 0, wx.EXPAND, 0)

        label_turd = wxStaticText(self, wx.ID_ANY, _("Despeckle"))
        label_turd.SetMinSize(dip_size(self, 70, -1))
        sizer_turd.Add(label_turd, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_turdsize = wx.Slider(self, wx.ID_ANY, 2, 0, 10)
        self.slider_turdsize.SetToolTip(
            _("Suppress speckles of up to this size (default 2 px)")
        )
        sizer_turd.Add(self.slider_turdsize, 1, wx.EXPAND, 0)

        sizer_alphamax = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(sizer_alphamax, 0, wx.EXPAND, 0)

        label_alphamax = wxStaticText(self, wx.ID_ANY, _("Corners"))
        label_alphamax.SetMinSize(dip_size(self, 70, -1))
        sizer_alphamax.Add(label_alphamax, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_alphamax = wx.Slider(self, wx.ID_ANY, 9, 0, 12)
        self.slider_alphamax.SetToolTip(
            _(
                "This parameter is a threshold for the detection of corners. It controls the smoothness of the traced curve."
            )
        )
        sizer_alphamax.Add(self.slider_alphamax, 1, wx.EXPAND, 0)

        sizer_opticurve = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(sizer_opticurve, 0, wx.EXPAND, 0)

        label_opticurve = wxStaticText(self, wx.ID_ANY, _("Simplify"))
        label_opticurve.SetMinSize(dip_size(self, 70, -1))
        sizer_opticurve.Add(label_opticurve, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.check_opticurve = wxCheckBox(self, wx.ID_ANY, "")
        self.check_opticurve.SetToolTip(
            _(
                "Try to 'simplify' the final curve by reducing the number of Bezier curve segments."
            )
        )
        self.check_opticurve.SetValue(1)
        sizer_opticurve.Add(self.check_opticurve, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_opttolerance = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(sizer_opttolerance, 0, wx.EXPAND, 0)

        label_opttolerance = wxStaticText(self, wx.ID_ANY, _("Tolerance"))
        label_opttolerance.SetMinSize(dip_size(self, 70, -1))
        sizer_opttolerance.Add(label_opttolerance, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_tolerance = wx.Slider(self, wx.ID_ANY, 20, 0, 150)
        self.slider_tolerance.SetToolTip(
            _(
                "This defines the amount of error allowed in this simplification.\n"
                + "Larger values tend to decrease the number of segments, at the expense of less accuracy."
            )
        )
        sizer_opttolerance.Add(self.slider_tolerance, 1, wx.EXPAND, 0)

        sizer_blacklevel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(sizer_blacklevel, 0, wx.EXPAND, 0)

        label_blacklevel = wxStaticText(self, wx.ID_ANY, _("Black-Level"))
        label_blacklevel.SetMinSize(dip_size(self, 70, -1))
        sizer_blacklevel.Add(label_blacklevel, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.slider_blacklevel = wx.Slider(
            self, wx.ID_ANY, 50, 0, 100, style=wx.SL_HORIZONTAL | wx.SL_LABELS
        )
        self.slider_blacklevel.SetToolTip(_("Establish when 'black' starts"))
        sizer_blacklevel.Add(self.slider_blacklevel, 1, wx.EXPAND, 0)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(sizer_buttons, 1, wx.EXPAND, 0)

        self.button_vector = wxButton(self, wx.ID_ANY, _("Vectorize"))
        sizer_buttons.Add(self.button_vector, 0, 0, 0)

        label_spacer = wxStaticText(self, wx.ID_ANY, " ")
        sizer_buttons.Add(label_spacer, 1, 0, 0)

        self.button_generate = wxButton(self, wx.ID_ANY, _("Preview"))
        self.button_generate.SetToolTip(_("Generate a preview of the result"))
        sizer_buttons.Add(self.button_generate, 0, 0, 0)

        sizer_preview = StaticBoxSizer(self, wx.ID_ANY, _("Preview"), wx.VERTICAL)
        main_sizer.Add(sizer_preview, 2, wx.EXPAND, 0)

        self.bitmap_preview = wxStaticBitmap(self, wx.ID_ANY, wx.NullBitmap)
        sizer_preview.Add(self.bitmap_preview, 1, wx.EXPAND, 0)

        self.vector_preview = wxStaticBitmap(self, wx.ID_ANY, wx.NullBitmap)
        sizer_preview.Add(self.vector_preview, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)

        # self._preview = True
        # self._need_updates = False

        # self.check_generate.SetValue(self._preview)

        self.wximage = wx.NullBitmap
        self.wxvector = wx.NullBitmap

        self.Layout()
        self.Centre()
        self.Bind(wx.EVT_BUTTON, self.on_button_create, self.button_vector)
        # self.Bind(wx.EVT_CHECKBOX, self.on_check_preview, self.check_generate)
        self.Bind(wx.EVT_BUTTON, self.on_changes, self.button_generate)
        self.Bind(wx.EVT_SIZE, self.on_size)
        # self.Bind(wx.EVT_SLIDER, self.on_changes, self.slider_alphamax)
        # self.Bind(wx.EVT_SLIDER, self.on_changes, self.slider_blacklevel)
        # self.Bind(wx.EVT_SLIDER, self.on_changes, self.slider_tolerance)
        # self.Bind(wx.EVT_SLIDER, self.on_changes, self.slider_turdsize)
        # self.Bind(wx.EVT_COMBOBOX, self.on_changes, self.combo_turnpolicy)
        # self.stop = None
        # self._update_thread = self.context.threaded(
        #         self.generate_preview, result=self.stop, daemon=True
        #     )

        self.set_widgets(node)

    # def on_check_preview(self, event):
    #     self._preview = self.check_generate.GetValue()

    def on_size(self, event):
        self.set_images(True)

    def pane_active(self):
        self._pane_is_active = True
        self.set_images(True)

    def pane_deactive(self):
        self._pane_is_active = False

    def on_changes(self, event):
        # self._need_updates = True
        self.generate_preview()

    def on_button_create(self, event):
        ipolicy = self.combo_turnpolicy.GetSelection()
        turnpolicy = self.turn_choices[ipolicy].lower()
        # slider 0 .. 10 translate to 0 .. 10
        turdsize = self.slider_turdsize.GetValue()
        # slider 0 .. 100 translate to 0 .. 1
        blacklevel = (
            self.slider_blacklevel.GetValue() / self.slider_blacklevel.GetMax() * 1.0
        )
        # slider 0 .. 150 translate to 0 .. 1.5
        opttolerance = (
            self.slider_tolerance.GetValue() / self.slider_tolerance.GetMax() * 1.5
        )
        # slider 0 .. 12 translate to 0 .. 1.333
        alphamax = (
            self.slider_alphamax.GetValue() / self.slider_alphamax.GetMax() * 4.0 / 3.0
        )
        opticurve = self.check_opticurve.GetValue()
        cmd = f"vectorize -z {turnpolicy} -t {turdsize} -a {alphamax}{' -n' if opticurve else ''} -O {opttolerance} -k {blacklevel}\n"
        self.context(cmd)

    def set_images(self, refresh=False):
        def opaque(source):
            img = source
            if img is not None and img.mode == "RGBA":
                r, g, b, a = img.split()
                background = Image.new("RGB", img.size, "white")
                background.paste(img, mask=a)
                img = background
            return img

        if not self._pane_is_active:
            return
        if self.node is None or self.node.image is None:
            self.wximage = wx.NullBitmap
        else:
            if refresh:
                source_image = self.node.active_image
                source_image = opaque(source_image)
                pw, ph = self.bitmap_preview.GetSize()
                iw, ih = source_image.size
                wfac = pw / iw
                hfac = ph / ih
                # The smaller of the two decide how to scale the picture
                if wfac < hfac:
                    factor = wfac
                else:
                    factor = hfac
                # print (f"Window: {pw} x {ph}, Image= {iw} x {ih}, factor={factor:.3f}")
                if factor < 1.0:
                    image = source_image.resize((int(iw * factor), int(ih * factor)))
                else:
                    image = source_image
                self.wximage = self.img_2_wx(image)

        self.bitmap_preview.SetBitmap(self.wximage)

    def generate_preview(self):
        # from time import sleep
        make_vector = self.context.kernel.lookup("render-op/make_vector")
        make_raster = self.context.kernel.lookup("render-op/make_raster")
        # while self.alive:
        if not self._pane_is_active:
            return
        self.wxvector = wx.NullBitmap

        if self.node is not None and self.node.image is not None:
            matrix = self.node.matrix
            # image = self.node.opaque_image
            ipolicy = self.combo_turnpolicy.GetSelection()
            # turnpolicy = self.turn_choices[ipolicy].lower()
            # slider 0 .. 10 translate to 0 .. 10
            turdsize = self.slider_turdsize.GetValue()
            # slider 0 .. 100 translate to 0 .. 1
            blacklevel = (
                self.slider_blacklevel.GetValue()
                / self.slider_blacklevel.GetMax()
                * 1.0
            )
            # slider 0 .. 150 translate to 0 .. 1.5
            opttolerance = (
                self.slider_tolerance.GetValue() / self.slider_tolerance.GetMax() * 1.5
            )
            # slider 0 .. 12 translate to 0 .. 1.333
            alphamax = (
                self.slider_alphamax.GetValue()
                / self.slider_alphamax.GetMax()
                * 4.0
                / 3.0
            )
            opticurve = self.check_opticurve.GetValue()
            bounds = self.node.paint_bounds
            if bounds is None:
                bounds = self.node.bounds
            if bounds is None:
                return
            xmin, ymin, xmax, ymax = bounds
            width = xmax - xmin
            height = ymax - ymin
            dpi = 250
            dots_per_units = dpi / UNITS_PER_INCH
            new_width = width * dots_per_units
            new_height = height * dots_per_units
            new_height = max(new_height, 1)
            new_width = max(new_width, 1)
            self.context.kernel.busyinfo.start(msg=_("Generating..."))
            try:
                image = make_raster(
                    self.node,
                    bounds=bounds,
                    width=new_width,
                    height=new_height,
                )
                path = make_vector(
                    image=image,
                    interpolationpolicy=ipolicy,
                    turdsize=turdsize,
                    alphamax=alphamax,
                    opticurve=opticurve,
                    opttolerance=opttolerance,
                    blacklevel=blacklevel,
                )
            except:
                self.context.kernel.busyinfo.end()
                return
            self.context.kernel.busyinfo.end()
            path.transform *= Matrix(matrix)
            dummynode = PathNode(
                path=abs(path),
                stroke_width=500,
                stroke_scaled=False,
                fillrule=0,  # Fillrule.FILLRULE_NONZERO
            )
            if dummynode is None:
                return
            bounds = dummynode.paint_bounds
            if bounds is None:
                bounds = dummynode.bounds
            if bounds is None:
                return
            pw, ph = self.vector_preview.GetSize()
            # iw, ih = self.node.image.size
            # wfac = pw / iw
            # hfac = ph / ih
            # The smaller of the two decide how to scale the picture
            # if wfac < hfac:
            #     factor = wfac
            # else:
            #     factor = hfac
            image = make_raster(
                dummynode,
                bounds,
                width=pw,
                height=ph,
                keep_ratio=True,
            )
            # rw, rh = image.size
            # print (f"Area={pw}x{ph}, Org={iw}x{ih}, Raster={rw}x{rh}")
            # if factor < 1.0:
            #     image = image.resize((int(iw * factor), int(ih * factor)))
            self.wxvector = self.img_2_wx(image)

        self.vector_preview.SetBitmap(self.wxvector)

    @staticmethod
    def accepts(node):
        # Changing the staticmethod into a regular method will cause a crash
        # Not the nicest thing in the world, as we need to instantiate the class once to reset the status flag
        global HAS_VECTOR_ENGINE
        return hasattr(node, "as_image") and HAS_VECTOR_ENGINE

    def img_2_wx(self, image):
        width, height = image.size
        newimage = image.convert("RGB")
        return wx.Bitmap.FromBuffer(width, height, newimage.tobytes())

    def set_widgets(self, node=None):
        self.node = node
        if node is not None:
            self._need_updates = True
        self.set_images()

    def signal(self, signalstr, myargs):
        return


class ImagePropertyPanel(ScrolledPanel):
    def __init__(self, *args, context=None, node=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.subpanels = list()
        self.context = context
        self.context.themes.set_window_colors(self)
        self.node = node
        self.panel_id = IdPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.SetHelpText("imageproperty")
        self.subpanels.append(self.panel_id)
        self.text_dpi = TextCtrl(
            self,
            wx.ID_ANY,
            "500",
            style=wx.TE_PROCESS_ENTER,
            check="float",
            limited=True,
            nonzero=True,
        )
        self.text_dpi.set_default_values(
            [
                (str(dpi), _("Set DPI to {value}").format(value=str(dpi)))
                for dpi in self.context.device.view.get_sensible_dpi_values()
            ]
        )
        self.check_keep_size = wxCheckBox(self, wx.ID_ANY, _("Keep size on change"))
        self.check_keep_size.SetValue(True)
        self.check_prevent_crop = wxCheckBox(self, wx.ID_ANY, _("No final crop"))

        self.panel_lock = PreventChangePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.subpanels.append(self.panel_lock)

        self.panel_keyhole = KeyholePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.subpanels.append(self.panel_keyhole)

        self.panel_xy = PositionSizePanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.subpanels.append(self.panel_xy)

        self.panel_crop = CropPanel(
            self, id=wx.ID_ANY, context=self.context, node=self.node
        )
        self.subpanels.append(self.panel_crop)
        self.check_enable_dither = wxCheckBox(self, wx.ID_ANY, _("Dither"))
        self.choices = [
            "Floyd-Steinberg",
            "Legacy-Floyd-Steinberg",
            "Atkinson",
            "Jarvis-Judice-Ninke",
            "Stucki",
            "Burkes",
            "Sierra3",
            "Sierra2",
            "Sierra-2-4a",
            "Shiau-Fan",
            "Shiau-Fan-2",
            "Bayer",
            "Bayer-Blue",
        ]
        self.combo_dither = wxComboBox(
            self,
            wx.ID_ANY,
            choices=self.choices,
            style=wx.CB_READONLY | wx.CB_DROPDOWN,
        )
        self.check_enable_depthmap = wxCheckBox(self, wx.ID_ANY, _("Depthmap"))
        resolutions = list((f"{2**p} - {p}bit" for p in range(8, 1, -1)))
        self.combo_depthmap = wxComboBox(
            self,
            wx.ID_ANY,
            choices=resolutions,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )

        # self.op_choices = []
        # self.image_ops = []
        # self.op_choices.append(_("Choose a script to apply"))
        # self.op_choices.append(_("Set to None"))
        # for op in list(self.context.elements.match("raster_script", suffix=True)):
        #     self.op_choices.append(_("Apply: {script}").format(script=op))
        #     self.image_ops.append(op)

        # self.combo_operations = wxComboBox(
        #     self,
        #     wx.ID_ANY,
        #     choices=self.op_choices,
        #     style=wx.CB_DROPDOWN,
        # )

        self.check_invert_grayscale = wxCheckBox(self, wx.ID_ANY, _("Invert"))
        self.btn_reset_grayscale = wxButton(self, wx.ID_ANY, _("Reset"))

        self.slider_grayscale_red = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_red = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.slider_grayscale_green = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_green = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.slider_grayscale_blue = wx.Slider(
            self, wx.ID_ANY, 0, -1000, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_blue = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.slider_grayscale_lightness = wx.Slider(
            self, wx.ID_ANY, 500, 0, 1000, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL
        )
        self.text_grayscale_lightness = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_dither, self.check_enable_dither)
        self.Bind(wx.EVT_COMBOBOX, self.on_dither, self.combo_dither)

        self.Bind(wx.EVT_CHECKBOX, self.on_depthmap, self.check_enable_depthmap)
        self.Bind(wx.EVT_COMBOBOX, self.on_depthmap, self.combo_depthmap)
        # self.Bind(wx.EVT_COMBOBOX, self.on_combo_operation, self.combo_operations)

        self.Bind(wx.EVT_TEXT_ENTER, self.on_dither, self.combo_dither)

        self.text_dpi.SetActionRoutine(self.on_text_dpi)

        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_invert_grayscale, self.check_invert_grayscale
        )
        self.Bind(wx.EVT_BUTTON, self.on_reset_grayscale, self.btn_reset_grayscale)
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_lightness,
        )
        self.Bind(
            wx.EVT_SLIDER, self.on_slider_grayscale_component, self.slider_grayscale_red
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_green,
        )
        self.Bind(
            wx.EVT_SLIDER,
            self.on_slider_grayscale_component,
            self.slider_grayscale_blue,
        )
        self.check_prevent_crop.Bind(wx.EVT_CHECKBOX, self.on_crop_option)

        # self.check_enable_grayscale.SetValue(op["enable"])
        if node.invert is None:
            node.invert = False
        self.set_grayscale_values()
        self.set_widgets()

    @staticmethod
    def accepts(node):
        return hasattr(node, "as_image")

    def set_grayscale_values(self):
        self.check_invert_grayscale.SetValue(self.node.invert)

        self.slider_grayscale_red.SetValue(int(self.node.red * 500.0))
        self.text_grayscale_red.SetValue(str(self.node.red))

        self.slider_grayscale_green.SetValue(int(self.node.green * 500.0))
        self.text_grayscale_green.SetValue(str(self.node.green))

        self.slider_grayscale_blue.SetValue(int(self.node.blue * 500.0))
        self.text_grayscale_blue.SetValue(str(self.node.blue))

        self.slider_grayscale_lightness.SetValue(int(self.node.lightness * 500.0))
        self.text_grayscale_lightness.SetValue(str(self.node.lightness))

    def set_widgets(self, node=None):
        if node is None:
            node = self.node
        for p in self.subpanels:
            p.set_widgets(node)
        self.node = node
        if node is None:
            return
        if self.node.type == "elem image":
            self.check_keep_size.Show(True)
        else:
            self.check_keep_size.Show(True)
        self.text_dpi.SetValue(str(node.dpi))
        self.check_enable_dither.SetValue(node.dither)
        self.combo_dither.SetValue(node.dither_type)
        self.combo_dither.Enable(bool(node.dither))
        self.check_enable_depthmap.SetValue(node.is_depthmap)
        resolutions = list((2**p for p in range(8, 1, -1)))
        try:
            idx = resolutions.index(node.depth_resolution)
        except (IndexError, AttributeError, ValueError) as e:
            # print(f"Caught error {e} for value {node.depth_resolution}")
            idx = 0
        self.combo_depthmap.SetSelection(idx)
        self.combo_depthmap.Enable(bool(node.is_depthmap))

        self.check_prevent_crop.SetValue(node.prevent_crop)

    def __set_properties(self):
        self.check_keep_size.SetToolTip(
            _("Enabled: Keep size and amend internal resolution")
            + "\n"
            + _("Disabled: Keep internal resolution and change size")
        )
        self.check_prevent_crop.SetToolTip(_("Prevent final crop after all operations"))
        self.check_enable_dither.SetToolTip(_("Enable Dither"))
        self.check_enable_dither.SetValue(True)
        self.combo_dither.Enable(True)
        self.combo_dither.SetToolTip(_("Select dither algorithm to use"))
        self.combo_dither.SetSelection(0)
        # self.combo_operations.SetToolTip(_("Select image enhancement script to apply"))
        # self.combo_operations.SetSelection(0)
        self.check_invert_grayscale.SetToolTip(_("Invert Grayscale"))
        self.slider_grayscale_red.SetToolTip(_("Red component amount"))
        self.text_grayscale_red.SetToolTip(_("Red Factor"))
        self.slider_grayscale_green.SetToolTip(_("Green component control"))
        self.text_grayscale_green.SetToolTip(_("Green Factor"))
        self.slider_grayscale_blue.SetToolTip(_("Blue component control"))
        self.text_grayscale_blue.SetToolTip(_("Blue Factor"))
        self.slider_grayscale_lightness.SetToolTip(_("Lightness control"))
        self.text_grayscale_lightness.SetToolTip(_("Lightness"))
        self.btn_reset_grayscale.SetToolTip(
            _("Reset the grayscale modifiers to standard values")
        )

        DEPTH_FLAG_TOOLTIP = _(
            "Do you want to treat this bitmap as depthmap where every greyscal-level corresponds to the amount of times this pixel will be burnt"
        )
        self.check_enable_depthmap.SetToolTip(DEPTH_FLAG_TOOLTIP)
        self.check_enable_depthmap.SetValue(False)
        DEPTH_RES_TOOLTIP = (
            _("How many grayscales do you want to distinguish?")
            + "\n"
            + _(
                "This operation will step through the image and process it per defined grayscale resolution."
            )
            + "\n"
            + _(
                "So for full resolution every grayscale level would be processed individually: a black line (or a white line if inverted) would be processed 255 times, a line with grayscale value 128 would be processed 128 times."
            )
            + "\n"
            + _(
                "You can define a coarser resolution e.g. 64: then very faint lines (grayscale 1-4) would be burned just once, very strong lines (level 252-255) would be burned 64 times."
            )
        )
        self.combo_depthmap.SetToolTip(DEPTH_RES_TOOLTIP)
        self.combo_depthmap.SetSelection(0)
        self.combo_depthmap.Enable(False)
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ImageProperty.__do_layout
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.panel_id, 0, wx.EXPAND, 0)
        sizer_main.Add(self.panel_crop, 0, wx.EXPAND, 0)

        sizer_dpi_crop = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dpi = StaticBoxSizer(self, wx.ID_ANY, _("DPI:"), wx.HORIZONTAL)
        self.text_dpi.SetToolTip(_("Dots Per Inch"))
        sizer_dpi.Add(self.text_dpi, 1, wx.EXPAND, 0)
        sizer_dpi.Add(self.check_keep_size, 0, wx.EXPAND, 0)

        sizer_dpi_crop.Add(sizer_dpi, 1, wx.EXPAND, 0)

        sizer_crop = StaticBoxSizer(self, wx.ID_ANY, _("Auto-Crop:"), wx.HORIZONTAL)
        sizer_crop.Add(self.check_prevent_crop, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_dpi_crop.Add(sizer_crop, 1, wx.EXPAND, 0)

        sizer_dither_depth = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dither = StaticBoxSizer(self, wx.ID_ANY, _("Dither"), wx.HORIZONTAL)
        sizer_dither.Add(self.check_enable_dither, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_dither.Add(self.combo_dither, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_dither_depth.Add(sizer_dither, 1, wx.EXPAND, 0)
        sizer_depth = StaticBoxSizer(self, wx.ID_ANY, _("3D-Treatment"), wx.HORIZONTAL)
        sizer_depth.Add(self.check_enable_depthmap, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_depth.Add(self.combo_depthmap, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_dither_depth.Add(sizer_depth, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_dpi_crop, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_dither_depth, 0, wx.EXPAND, 0)

        sizer_rg = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_grayscale = StaticBoxSizer(self, wx.ID_ANY, _("Grayscale"), wx.VERTICAL)
        sizer_inversion_reset = wx.BoxSizer(wx.HORIZONTAL)
        sizer_inversion_reset.Add(
            self.check_invert_grayscale, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        sizer_inversion_reset.AddStretchSpacer(1)
        sizer_inversion_reset.Add(
            self.btn_reset_grayscale, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )

        sizer_grayscale_lightness = StaticBoxSizer(
            self, wx.ID_ANY, _("Lightness"), wx.HORIZONTAL
        )
        sizer_grayscale_blue = StaticBoxSizer(self, wx.ID_ANY, _("Blue"), wx.HORIZONTAL)
        sizer_grayscale_green = StaticBoxSizer(
            self, wx.ID_ANY, _("Green"), wx.HORIZONTAL
        )
        sizer_grayscale_red = StaticBoxSizer(self, wx.ID_ANY, _("Red"), wx.HORIZONTAL)
        sizer_grayscale.Add(sizer_inversion_reset, 0, wx.EXPAND, 0)
        sizer_grayscale_red.Add(self.slider_grayscale_red, 1, wx.EXPAND, 0)
        sizer_grayscale_red.Add(self.text_grayscale_red, 1, 0, 0)
        sizer_rg.Add(sizer_grayscale_red, 1, wx.EXPAND, 0)
        sizer_grayscale_green.Add(self.slider_grayscale_green, 1, wx.EXPAND, 0)
        sizer_grayscale_green.Add(self.text_grayscale_green, 1, 0, 0)
        sizer_rg.Add(sizer_grayscale_green, 1, wx.EXPAND, 0)
        sizer_grayscale_blue.Add(self.slider_grayscale_blue, 1, wx.EXPAND, 0)
        sizer_grayscale_blue.Add(self.text_grayscale_blue, 1, 0, 0)
        sizer_bl.Add(sizer_grayscale_blue, 1, wx.EXPAND, 0)
        sizer_grayscale_lightness.Add(self.slider_grayscale_lightness, 1, wx.EXPAND, 0)
        sizer_grayscale_lightness.Add(self.text_grayscale_lightness, 1, 0, 0)
        sizer_bl.Add(sizer_grayscale_lightness, 1, wx.EXPAND, 0)
        sizer_grayscale.Add(sizer_rg, 5, wx.EXPAND, 0)
        sizer_grayscale.Add(sizer_bl, 5, wx.EXPAND, 0)

        self.text_grayscale_red.SetMaxSize(dip_size(self, 70, -1))
        self.text_grayscale_green.SetMaxSize(dip_size(self, 70, -1))
        self.text_grayscale_blue.SetMaxSize(dip_size(self, 70, -1))
        self.text_grayscale_lightness.SetMaxSize(dip_size(self, 70, -1))

        sizer_main.Add(sizer_grayscale, 0, wx.EXPAND, 0)

        hor_sizer = wx.BoxSizer(wx.HORIZONTAL)
        hor_sizer.Add(self.panel_lock, 1, wx.EXPAND, 0)
        hor_sizer.Add(self.panel_keyhole, 1, wx.EXPAND, 0)

        sizer_main.Add(hor_sizer, 0, wx.EXPAND, 0)
        sizer_main.Add(self.panel_xy, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self.Centre()
        # end wxGlade

    def node_update(self):
        self.node.set_dirty_bounds()
        self.context.elements.do_image_update(self.node, self.context)
        self.context.elements.emphasized()
        self.context.signal("element_property_update", self.node)

    def on_text_dpi(self):
        old_step = self.node.dpi
        new_step = float(self.text_dpi.GetValue())
        if old_step == new_step:
            return
        if self.node.type == "elem image":
            keep_size = self.check_keep_size.GetValue()
            if not keep_size:
                # We need to rescale the image
                img_scale = old_step / new_step
                bb = self.node.bounds
                self.node.matrix.post_scale(img_scale, img_scale, bb[0], bb[1])
        self.node.dpi = new_step
        self.node_update()

    def on_crop_option(self, event):
        self.node.prevent_crop = self.check_prevent_crop.GetValue()
        self.node_update()

    def on_dither(self, event=None):
        # Dither can be set by two different means:
        # a. directly
        # b. via a script
        dither_op = None
        for op in self.node.operations:
            if op["name"] == "dither":
                dither_op = op
                break
        dither_flag = self.check_enable_dither.GetValue()
        self.combo_dither.Enable(dither_flag)
        dither_type = self.choices[self.combo_dither.GetSelection()]
        if dither_op is not None:
            dither_op["enable"] = dither_flag
            dither_op["type"] = dither_type
        self.node.dither = dither_flag
        self.node.dither_type = dither_type
        if dither_flag:
            self.node.is_depthmap = False
            self.check_enable_depthmap.SetValue(False)
            self.combo_depthmap.Enable(False)
        self.node_update()
        self.context.signal("nodetype")

    def on_depthmap(self, event=None):
        depth_flag = self.check_enable_depthmap.GetValue()
        self.combo_depthmap.Enable(depth_flag)
        resolutions = (256, 128, 64, 32, 16, 8, 4)
        idx = self.combo_depthmap.GetSelection()
        if idx < 1:
            idx = 0
        depth_res = resolutions[idx]
        self.node.is_depthmap = depth_flag
        self.node.depth_resolution = depth_res
        if depth_flag:
            self.node.dither = False
            self.check_enable_dither.SetValue(False)
            self.combo_dither.Enable(False)
        self.node_update()
        self.context.signal("nodetype")

    def on_reset_grayscale(self, event):
        self.node.invert = False
        self.node.red = 1.0
        self.node.green = 1.0
        self.node.blue = 1.0
        self.node.lightness = 1.0
        self.node_update()
        self.set_grayscale_values()

    def on_check_invert_grayscale(
        self, event=None
    ):  # wxGlade: RasterWizard.<event_handler>
        self.node.invert = self.check_invert_grayscale.GetValue()
        self.node_update()

    def on_slider_grayscale_component(
        self, event=None
    ):  # wxGlade: GrayscalePanel.<event_handler>
        if event and (
            not self.context.process_while_sliding and wx.GetMouseState().LeftIsDown()
        ):
            event.Skip()
            return

        self.node.red = float(int(self.slider_grayscale_red.GetValue()) / 500.0)
        self.text_grayscale_red.SetValue(str(self.node.red))

        self.node.green = float(int(self.slider_grayscale_green.GetValue()) / 500.0)
        self.text_grayscale_green.SetValue(str(self.node.green))

        self.node.blue = float(int(self.slider_grayscale_blue.GetValue()) / 500.0)
        self.text_grayscale_blue.SetValue(str(self.node.blue))

        self.node.lightness = float(
            int(self.slider_grayscale_lightness.GetValue()) / 500.0
        )
        self.text_grayscale_lightness.SetValue(str(self.node.lightness))
        self.node_update()

    def signal(self, signalstr, myargs):
        for p in self.subpanels:
            if hasattr(p, "signal"):
                p.signal(signalstr, myargs)

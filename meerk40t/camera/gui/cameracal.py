"""
Camera Calibration — guided bed overlay setup for Meerkat.

Walks through perspective corners on the live camera feed, pushes the
flattened image to the main scene bed, and can place corner test marks.
"""

import wx

from meerk40t.core.units import Length
from meerk40t.gui.icons import icons8_image_in_frame
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import StaticBoxSizer, wxButton, wxStaticText, TextCtrl
from meerk40t.svgelements import Color

_ = wx.GetTranslation


def _bed_bbox(device):
    """Return bed bounds in scene units (x0, y0, x1, y1)."""
    try:
        return device.view.source_bbox()
    except AttributeError:
        return 0.0, 0.0, 405.0, -285.0


def _corner_positions(x0, y0, x1, y1, margin, size):
    """Place test squares inset from each bed corner."""
    x_left = min(x0, x1)
    x_right = max(x0, x1)
    y_top = max(y0, y1)
    y_bot = min(y0, y1)
    return (
        (_("Calib TL"), x_left + margin, y_top - margin - size),
        (_("Calib TR"), x_right - margin - size, y_top - margin - size),
        (_("Calib BR"), x_right - margin - size, y_bot + margin),
        (_("Calib BL"), x_left + margin, y_bot + margin),
    )


class CameraCalibWindow(MWindow):
    """Step-by-step helper for camera perspective and bed background."""

    def __init__(self, *args, **kwds):
        super().__init__(480, 640, *args, **kwds)

        steps = StaticBoxSizer(self, wx.ID_ANY, _("Steps"), wx.VERTICAL)
        self.lbl_steps = wxStaticText(
            self,
            wx.ID_ANY,
            _(
                "1. Home the machine ($HY then $HX).\n"
                "2. Open the camera window — live feed on the bed.\n"
                "   If TL is on the wrong corner, click Flip camera 180°.\n"
                "3. Click Reset perspective, then drag the large\n"
                "   coloured TL/TR/BR/BL circles to each bed corner\n"
                "   (Correct Perspective OFF).\n"
                "4. Turn Correct Perspective ON in the camera window.\n"
                "5. Right-click camera → link your DLC32 device.\n"
                "6. Update Background — bed photo appears on the main scene.\n"
                "7. Add corner test marks, run a low-power cut.\n"
                "8. Use Fine alignment (mm) to nudge the overlay — no GRBL change."
            ),
        )
        steps.Add(self.lbl_steps, 0, wx.EXPAND, 0)

        cam_box = StaticBoxSizer(self, wx.ID_ANY, _("Camera"), wx.VERTICAL)
        row_cam = wx.BoxSizer(wx.HORIZONTAL)
        row_cam.Add(wxStaticText(self, wx.ID_ANY, _("Index")), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.spin_camera = wx.SpinCtrl(self, wx.ID_ANY, min=0, max=8, initial=0)
        row_cam.Add(self.spin_camera, 0, wx.LEFT, 4)
        self.btn_open = wxButton(self, wx.ID_ANY, _("Open camera window"))
        row_cam.Add(self.btn_open, 0, wx.LEFT, 8)
        cam_box.Add(row_cam, 0, wx.EXPAND, 0)

        row_uri = wx.BoxSizer(wx.HORIZONTAL)
        self.text_camera_uri = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.text_camera_uri.SetToolTip(
            _(
                "Paste: 0 (USB), rtsp://user:pass@IP:8554/stream1,\n"
                "user:pass@IP, or bare IP (defaults to rtsp://IP:8554/profile0)."
            )
        )
        self.btn_connect = wxButton(self, wx.ID_ANY, _("Connect"))
        row_uri.Add(self.text_camera_uri, 1, wx.EXPAND, 0)
        row_uri.Add(self.btn_connect, 0, wx.LEFT, 4)
        cam_box.Add(row_uri, 0, wx.EXPAND | wx.TOP, 4)

        actions = StaticBoxSizer(self, wx.ID_ANY, _("Actions"), wx.VERTICAL)
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_reset = wxButton(self, wx.ID_ANY, _("Reset perspective"))
        self.btn_flip180 = wxButton(self, wx.ID_ANY, _("Flip camera 180°"))
        row1.Add(self.btn_reset, 1, wx.EXPAND, 0)
        row1.Add(self.btn_flip180, 1, wx.LEFT | wx.EXPAND, 4)
        actions.Add(row1, 0, wx.EXPAND, 0)

        row1b = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_background = wxButton(self, wx.ID_ANY, _("Update background"))
        row1b.Add(self.btn_background, 1, wx.EXPAND, 0)
        actions.Add(row1b, 0, wx.EXPAND | wx.TOP, 4)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_corners = wxButton(self, wx.ID_ANY, _("Add corner test marks"))
        self.btn_fit = wxButton(self, wx.ID_ANY, _("Zoom scene to bed"))
        row2.Add(self.btn_corners, 1, wx.EXPAND, 0)
        row2.Add(self.btn_fit, 1, wx.LEFT | wx.EXPAND, 4)
        actions.Add(row2, 0, wx.EXPAND | wx.TOP, 4)

        align_box = StaticBoxSizer(self, wx.ID_ANY, _("Fine alignment (mm)"), wx.VERTICAL)
        align_hint = wxStaticText(
            self,
            wx.ID_ANY,
            _(
                "Shift the bed photo vs the laser grid (steps/mm unchanged).\n"
                "If the burn is right of the mark → Overlay →. Left of mark → Overlay ←.\n"
                "Below the mark → Overlay ↓. Above the mark → Overlay ↑."
            ),
        )
        align_box.Add(align_hint, 0, wx.EXPAND | wx.BOTTOM, 4)

        row_ax = wx.BoxSizer(wx.HORIZONTAL)
        row_ax.Add(wxStaticText(self, wx.ID_ANY, _("Offset X")), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.spin_align_x = wx.SpinCtrl(self, wx.ID_ANY, min=-100, max=100, initial=0)
        row_ax.Add(self.spin_align_x, 1, wx.LEFT | wx.EXPAND, 4)
        align_box.Add(row_ax, 0, wx.EXPAND, 0)

        row_ay = wx.BoxSizer(wx.HORIZONTAL)
        row_ay.Add(wxStaticText(self, wx.ID_ANY, _("Offset Y")), 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.spin_align_y = wx.SpinCtrl(self, wx.ID_ANY, min=-100, max=100, initial=0)
        row_ay.Add(self.spin_align_y, 1, wx.LEFT | wx.EXPAND, 4)
        align_box.Add(row_ay, 0, wx.EXPAND | wx.TOP, 4)

        row_nudge = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_align_left = wxButton(self, wx.ID_ANY, _("Overlay ←"))
        self.btn_align_right = wxButton(self, wx.ID_ANY, _("Overlay →"))
        self.btn_align_up = wxButton(self, wx.ID_ANY, _("Overlay ↑"))
        self.btn_align_down = wxButton(self, wx.ID_ANY, _("Overlay ↓"))
        for btn in (
            self.btn_align_left,
            self.btn_align_right,
            self.btn_align_up,
            self.btn_align_down,
        ):
            row_nudge.Add(btn, 1, wx.EXPAND, 0)
        align_box.Add(row_nudge, 0, wx.EXPAND | wx.TOP, 4)

        row_nudge2 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_align_apply = wxButton(self, wx.ID_ANY, _("Apply offset"))
        self.btn_align_reset = wxButton(self, wx.ID_ANY, _("Reset offset"))
        row_nudge2.Add(self.btn_align_apply, 1, wx.EXPAND, 0)
        row_nudge2.Add(self.btn_align_reset, 1, wx.LEFT | wx.EXPAND, 4)
        align_box.Add(row_nudge2, 0, wx.EXPAND | wx.TOP, 4)
        actions.Add(align_box, 0, wx.EXPAND | wx.TOP, 8)

        bed_box = StaticBoxSizer(self, wx.ID_ANY, _("Bed"), wx.VERTICAL)
        self.lbl_bed = wxStaticText(self, wx.ID_ANY, "")
        bed_box.Add(self.lbl_bed, 0, wx.EXPAND, 0)

        self.sizer.Add(steps, 0, wx.EXPAND | wx.ALL, 8)
        self.sizer.Add(cam_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.sizer.Add(actions, 0, wx.EXPAND | wx.ALL, 8)
        self.sizer.Add(bed_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.btn_open.Bind(wx.EVT_BUTTON, self.on_open_camera)
        self.btn_connect.Bind(wx.EVT_BUTTON, self.on_connect_camera)
        self.text_camera_uri.Bind(wx.EVT_TEXT_ENTER, self.on_connect_camera)
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset_perspective)
        self.btn_flip180.Bind(wx.EVT_BUTTON, self.on_flip180)
        self.btn_background.Bind(wx.EVT_BUTTON, self.on_update_background)
        self.btn_corners.Bind(wx.EVT_BUTTON, self.on_add_corners)
        self.btn_fit.Bind(wx.EVT_BUTTON, self.on_fit_scene)
        self.btn_align_left.Bind(wx.EVT_BUTTON, lambda e: self.on_nudge_align(-1, 0))
        self.btn_align_right.Bind(wx.EVT_BUTTON, lambda e: self.on_nudge_align(1, 0))
        self.btn_align_up.Bind(wx.EVT_BUTTON, lambda e: self.on_nudge_align(0, 1))
        self.btn_align_down.Bind(wx.EVT_BUTTON, lambda e: self.on_nudge_align(0, -1))
        self.btn_align_apply.Bind(wx.EVT_BUTTON, self.on_apply_align)
        self.btn_align_reset.Bind(wx.EVT_BUTTON, self.on_reset_align)

        self.Layout()
        self.refresh_bed_info()
        self.refresh_align_spins()
        self._load_saved_camera_uri()
        self._ensure_window_fits_content()

    def _load_saved_camera_uri(self):
        from meerk40t.camera.camera import _camera_service_for_index

        cam = _camera_service_for_index(self.context.kernel, self._camera_index())
        if cam is not None and getattr(cam, "uri", None) is not None:
            self.text_camera_uri.SetValue(str(cam.uri))

    def _ensure_window_fits_content(self):
        self.Layout()
        self.sizer.Fit(self)
        need_w, need_h = self.GetSize()
        try:
            dip = self.FromDIP(wx.Size(480, 680))
            need_w = max(need_w, dip[0])
            need_h = max(need_h, dip[1])
        except AttributeError:
            need_w = max(need_w, 480)
            need_h = max(need_h, 680)
        self.SetMinSize((need_w, need_h))
        cur_w, cur_h = self.GetSize()
        if cur_h < need_h or cur_w < need_w:
            self.SetSize((max(cur_w, need_w), max(cur_h, need_h)))

    def _camera_index(self):
        return self.spin_camera.GetValue()

    def refresh_bed_info(self):
        device = self.context.device
        x0, y0, x1, y1 = _bed_bbox(device)
        try:
            label = device.label
            w = device.view.width
            h = device.view.height
        except AttributeError:
            label = _("(no device)")
            w = "405mm"
            h = "285mm"
        self.lbl_bed.SetLabel(
            _("Device: {label}\nBed: {w} × {h}\nScene bounds: X {x0:.1f}…{x1:.1f}, Y {y0:.1f}…{y1:.1f}").format(
                label=label,
                w=w,
                h=h,
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
            )
        )

    def refresh_align_spins(self):
        try:
            cam = self._camera_service()
        except AttributeError:
            return
        self.spin_align_x.SetValue(int(round(float(cam.align_offset_x or 0.0))))
        self.spin_align_y.SetValue(int(round(float(cam.align_offset_y or 0.0))))

    def _save_align_from_spins(self):
        cam = self._camera_service()
        cam.align_offset_x = float(self.spin_align_x.GetValue())
        cam.align_offset_y = float(self.spin_align_y.GetValue())

    def _refresh_overlay(self):
        self.context.signal("refresh_scene")

    def on_nudge_align(self, dx_mm, dy_mm, event=None):
        try:
            cam = self._camera_service()
        except AttributeError:
            wx.MessageBox(
                _("Open the camera window first."),
                _("Fine alignment"),
                wx.OK | wx.ICON_WARNING,
                parent=self,
            )
            return
        cam.nudge_align(dx_mm, dy_mm)
        self.refresh_align_spins()
        self._refresh_overlay()

    def on_apply_align(self, event=None):
        try:
            self._save_align_from_spins()
        except AttributeError:
            wx.MessageBox(
                _("Open the camera window first."),
                _("Fine alignment"),
                wx.OK | wx.ICON_WARNING,
                parent=self,
            )
            return
        self._refresh_overlay()

    def on_reset_align(self, event=None):
        try:
            cam = self._camera_service()
        except AttributeError:
            return
        cam.align_offset_x = 0.0
        cam.align_offset_y = 0.0
        self.refresh_align_spins()
        self._refresh_overlay()

    def on_open_camera(self, event=None):
        idx = self._camera_index()
        self.context(f"camwin {idx}\n")

    def on_connect_camera(self, event=None):
        from meerk40t.camera.camera import connect_camera_from_paste

        raw = self.text_camera_uri.GetValue()
        if not str(raw).strip():
            wx.MessageBox(
                _("Paste a camera address (USB 0, rtsp://…, user:pass@IP, or IP)."),
                _("Connect camera"),
                wx.OK | wx.ICON_INFORMATION,
                parent=self,
            )
            return
        idx = self._camera_index()
        uri = connect_camera_from_paste(self.context.kernel, idx, raw, start=True)
        if uri is None:
            return
        self.text_camera_uri.SetValue(str(uri) if not isinstance(uri, int) else str(uri))
        self.context(f"camwin {idx}\n")

    def _camera_service(self):
        from meerk40t.camera.camera import _camera_service_for_index

        return _camera_service_for_index(self.context.kernel, self._camera_index())

    def on_flip180(self, event=None):
        try:
            cam = self._camera_service()
        except AttributeError:
            wx.MessageBox(
                _("Camera not available yet. Open the camera window first."),
                _("Flip camera"),
                wx.OK | wx.ICON_WARNING,
                parent=self,
            )
            return
        cam.set_image_flip(flip_x=True, flip_y=True)
        wx.MessageBox(
            _(
                "Camera image flipped 180° (horizontal + vertical).\n\n"
                "Perspective corners were reset — drag TL/TR/BR/BL\n"
                "to the matching bed corners again."
            ),
            _("Flip camera 180°"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )

    def on_reset_perspective(self, event=None):
        idx = self._camera_index()
        self.context(f"camera{idx} perspective reset\n")
        wx.MessageBox(
            _(
                "Perspective corners reset.\n\n"
                "In the camera window: leave Correct Perspective OFF,\n"
                "drag each large labelled circle (TL, TR, BR, BL)\n"
                "onto a bed corner, then turn Correct Perspective ON."
            ),
            _("Perspective reset"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )

    def on_update_background(self, event=None):
        idx = self._camera_index()
        self.context(f"camera{idx} background\n")
        wx.MessageBox(
            _(
                "Background sent to the main scene.\n\n"
                "If nothing appears: link your laser device in the camera\n"
                "right-click menu (...refresh → device), then try again."
            ),
            _("Background updated"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )

    def on_add_corners(self, event=None):
        elements = self.context.elements
        device = self.context.device
        x0, y0, x1, y1 = _bed_bbox(device)
        margin = float(Length("15mm"))
        size = float(Length("12mm"))
        stroke = Color("red")
        corners = _corner_positions(x0, y0, x1, y1, margin, size)
        branch = elements.op_branch
        for label, cx, cy in corners:
            node = branch.add(
                x=cx,
                y=cy,
                width=size,
                height=size,
                stroke=stroke,
                fill=None,
                type="elem rect",
            )
            node.label = label
        elements.signal("refresh_scene")
        wx.MessageBox(
            _(
                "Four small red squares were added near the bed corners.\n"
                "Assign them to a low-power Cut operation and run a test.\n"
                "If marks are off, nudge camera corners and Update background again."
            ),
            _("Corner marks added"),
            wx.OK | wx.ICON_INFORMATION,
            parent=self,
        )

    def on_fit_scene(self, event=None):
        self.context("scene focus -5% -5% 105% 105%\n")

    def window_open(self):
        self.refresh_bed_info()
        self.refresh_align_spins()
        self._load_saved_camera_uri()
        self._ensure_window_fits_content()
        self.Raise()

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/preparation/CameraCalib",
            {
                "label": _("Camera Calib"),
                "icon": icons8_image_in_frame,
                "tip": _("Guided camera bed calibration"),
                "help": "cameracal",
                "action": lambda v: kernel.console("window toggle CameraCalib\n"),
                "priority": 4,
            },
        )

    @staticmethod
    def submenu():
        return "Editing", "Camera", True

    @staticmethod
    def helptext():
        return _("Guide perspective calibration and bed background overlay from the camera")

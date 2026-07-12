import math

from meerk40t.core.units import UNITS_PER_MM, UNITS_PER_PIXEL
from meerk40t.kernel import lookup_listener, signal_listener
from meerk40t.rotary.rotary_cam import (
    bed_height_mm,
    bed_length_mm,
    calibrate_rotary_steps,
    circumference_mm,
    length_scale_x,
    suggest_rotary_steps_per_mm,
    wrap_scale_y,
    y_steps_factor,
)
from meerk40t.svgelements import Matrix

_FIT_MIN_MM = 0.5
_FIT_MIN_SCALE = 0.01
_FIT_MAX_SCALE = 100.0
_FIT_MAX_DIM_MM = 2000.0


def _laser_renderer(kernel):
    try:
        import wx

        if not wx.GetApp():
            return None
        from meerk40t.gui.laserrender import LaserRender

        return LaserRender(kernel.root)
    except (ImportError, RuntimeError, AttributeError):
        return None


def _measure_text_nodes(elems, kernel):
    renderer = _laser_renderer(kernel)
    if renderer is None:
        return None
    text_nodes = [n for n in elems if getattr(n, "type", None) == "elem text"]
    if text_nodes:
        renderer.validate_text_nodes(text_nodes, translate_variables=False)
    return renderer


def _native_extent_to_mm(native_extent):
    return native_extent / UNITS_PER_MM


def _repair_text_matrix(node, renderer=None):
    """
    MeerK40t text uses translate(x,y) + scale(UNITS_PER_PIXEL) on the matrix.
    Only *extra* scale (from old matrix-fit bugs) is folded into font_size.
    """
    m = node.matrix
    if m is None:
        node.matrix = Matrix(f"scale({UNITS_PER_PIXEL})")
        return False
    sx = math.hypot(float(m.a), float(m.b))
    sy = math.hypot(float(m.c), float(m.d))
    expected = UNITS_PER_PIXEL
    if expected <= 0:
        return False
    extra = ((sx / expected) + (sy / expected)) / 2.0
    if 0.98 <= extra <= 1.02:
        return False
    if extra <= 0 or not math.isfinite(extra):
        extra = 1.0
    try:
        node.font_size = float(node.font_size) * extra
    except (TypeError, ValueError):
        node.font_size = 12.0 * extra
    try:
        node.line_height = float(node.line_height) * extra
    except (TypeError, ValueError):
        pass
    tx, ty = float(m.e), float(m.f)
    node.matrix = Matrix(f"translate({tx},{ty}) scale({UNITS_PER_PIXEL})")
    node.set_dirty_bounds()
    if renderer is not None:
        renderer.measure_text(node)
        node.set_dirty_bounds()
    return True


def _prepare_fit_selection(elems, elements, kernel):
    renderer = _measure_text_nodes(elems, kernel)
    for node in elems:
        if getattr(node, "type", None) == "elem text":
            _repair_text_matrix(node, renderer)
    elements.validate_selected_area()
    return renderer


def _scale_text_uniform(node, scale, pivot_x, pivot_y, renderer):
    _repair_text_matrix(node, renderer)
    bb = node.bounds
    if bb is None:
        return
    ocx = (bb[0] + bb[2]) / 2
    ocy = (bb[1] + bb[3]) / 2
    target_cx = (ocx - pivot_x) * scale + pivot_x
    target_cy = (ocy - pivot_y) * scale + pivot_y
    try:
        node.font_size = float(node.font_size) * scale
    except (TypeError, ValueError):
        node.font_size = 12.0 * scale
    try:
        node.line_height = float(node.line_height) * scale
    except (TypeError, ValueError):
        pass
    node.set_dirty_bounds()
    if renderer is not None:
        renderer.measure_text(node)
    node.set_dirty_bounds()
    nbb = node.bounds
    if nbb is None:
        return
    ncx = (nbb[0] + nbb[2]) / 2
    ncy = (nbb[1] + nbb[3]) / 2
    if node.matrix is None:
        node.matrix = Matrix(f"scale({UNITS_PER_PIXEL})")
    node.matrix.post_translate(target_cx - ncx, target_cy - ncy)


def _apply_uniform_scale(node, scale, pivot_x, pivot_y, renderer=None):
    if getattr(node, "type", None) == "elem text":
        _scale_text_uniform(node, scale, pivot_x, pivot_y, renderer)
        return
    matrix = Matrix(f"scale({scale}, {scale}, {pivot_x}, {pivot_y})")
    try:
        if node.matrix is None:
            node.matrix = matrix
        else:
            node.matrix *= matrix
    except AttributeError:
        pass


def plugin(service, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "service":
        return (
            "provider/device/lhystudios",
            "provider/device/grbl",
            "provider/device/balor",
            "provider/device/newly",
            "provider/device/moshi",
        )
    elif lifecycle == "added":
        service.add_service_delegate(Rotary(service, 0))


class Rotary:
    """
    Rotary service for Y-motor-swap chuck rotaries on GRBL and other devices.

    Combines wrap scaling (diameter / length), optional Y steps compensation
    (software or firmware $101), and homing guards.
    """

    def __init__(self, service, index=0, *args, **kwargs):
        self.index = index
        self.service = service
        self.service.rotary = self

        _ = service._
        choices = [
            {
                "attr": "rotary_active",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _(
                    "Enable when the Y motor drives a rotary chuck (flat-bed Y unplugged). "
                    "Leave off for normal 400×285 mm cutting."
                ),
                "signals": "device;modified",
            },
            {
                "attr": "rotary_diameter_mm",
                "object": service,
                "default": 80.0,
                "type": float,
                "label": _("Outside diameter (mm)"),
                "tip": _("Cylinder OD for wrap math. Circumference = π × diameter."),
                "conditional": (service, "rotary_active"),
                "subsection": _("Object"),
            },
            {
                "attr": "rotary_length_mm",
                "object": service,
                "default": 200.0,
                "type": float,
                "label": _("Usable length (mm)"),
                "tip": _("Engravable length along the cylinder axis (X on the machine)."),
                "conditional": (service, "rotary_active"),
                "subsection": _("Object"),
            },
            {
                "attr": "rotary_auto_wrap_scale",
                "object": service,
                "default": True,
                "type": bool,
                "label": _("Auto Y wrap from diameter"),
                "tip": _(
                    "When on, Fit selection and the hint use π × diameter as the "
                    "wrap height. The scene stays normal mm — no preview distortion."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Object"),
            },
            {
                "attr": "rotary_auto_length_scale",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Auto X scale from length"),
                "tip": _(
                    "When on, X-Scale = usable length ÷ bed width. Usually leave off and "
                    "size artwork manually."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Object"),
            },
            {
                "attr": "rotary_flat_y_steps",
                "object": service,
                "default": 159.6,
                "type": float,
                "label": _("Flat-bed Y $101"),
                "tip": _(
                    "GRBL Y steps/mm for the gantry motor (Andre DLC32: 159.600). "
                    "Used to restore $101 or for software compensation."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Y steps"),
            },
            {
                "attr": "rotary_y_steps",
                "object": service,
                "default": 80.0,
                "type": float,
                "label": _("Rotary Y steps/mm"),
                "tip": _(
                    "Steps/mm for the rotary motor on the Y driver. Calibrate with "
                    "rotarycal after a test line, or use rotarysuggest."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Y steps"),
            },
            {
                "attr": "rotary_steps_compensate",
                "object": service,
                "default": True,
                "type": bool,
                "label": _("Software Y steps compensate"),
                "tip": _(
                    "Recommended: scale Y in the driver so GRBL can keep flat-bed $101. "
                    "Disable if you write rotary $101 to the board instead."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Y steps"),
            },
            {
                "attr": "rotary_firmware_steps",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Write $101 at job start"),
                "tip": _(
                    "Optional: send $101=rotary value before the job and restore flat-bed "
                    "$101 after. Turns off software compensation automatically."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Y steps"),
            },
            {
                "attr": "rotary_cal_test_mm",
                "object": service,
                "default": 100.0,
                "type": float,
                "label": _("Calibration test length (mm)"),
                "tip": _("Length of the test line you burned before rotarycal."),
                "conditional": (service, "rotary_active"),
                "subsection": _("Y steps"),
            },
            {
                "attr": "rotary_scale_x",
                "object": service,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale (manual)"),
                "tip": _("Manual X scale when Auto X scale is off."),
                "conditional": (service, "rotary_active"),
                "subsection": _("Scale (manual)"),
            },
            {
                "attr": "rotary_scale_y",
                "object": service,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale (manual)"),
                "tip": _("Manual Y scale when Auto Y wrap is off."),
                "conditional": (service, "rotary_active"),
                "subsection": _("Scale (manual)"),
            },
            {
                "attr": "suppress_home",
                "object": service,
                "default": True,
                "type": bool,
                "label": _("Ignore Home (G28)"),
                "tip": _(
                    "Skip soft home while rotary is active. Use with Y motor on chuck."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Homing"),
            },
            {
                "attr": "rotary_home_x_only",
                "object": service,
                "default": True,
                "type": bool,
                "label": _("Physical home: X only ($HX)"),
                "tip": _(
                    "If you use physical homing while rotary is on, run $HX only — never $HY."
                ),
                "conditional": (service, "rotary_active"),
                "subsection": _("Homing"),
            },
            {
                "attr": "rotary_flip_x",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (service, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "rotary_flip_y",
                "object": service,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror spin direction on the Y-Axis"),
                "conditional": (service, "rotary_active"),
                "subsection": _("Mirror Output"),
            },
        ]
        service.register_choices("rotary", choices)

        @service.console_command(
            "rotary",
            help=_("Show rotary status"),
            output_type="rotary",
        )
        def rotary(command, channel, _, data=None, **kwargs):
            self._print_status(channel)
            return "rotary", None

        @service.console_command("rotaryscale", help=_("Rotary Scale selected elements"))
        def apply_rotary_scale(*args, **kwargs):
            sx = self.effective_scale_x()
            sy = self.effective_scale_y()
            x, y = service.device.current
            matrix = Matrix(f"scale({sx}, {sy}, {x}, {y})")
            for node in service.elements.elems():
                if hasattr(node, "rotary_scale"):
                    return
                try:
                    node.rotary_scale = sx, sy
                    node.matrix *= matrix
                    node.modified()
                except AttributeError:
                    pass

        @service.console_argument(
            "measured",
            type=float,
            help=_("Measured length of calibration line (mm)"),
        )
        @service.console_command(
            "rotarycal",
            help=_("Calibrate rotary Y steps/mm from a test burn"),
        )
        def rotary_calibrate(channel, _, measured=None, **kwargs):
            if measured is None:
                channel(_("Usage: rotarycal <measured_mm>"))
                return
            cmd = float(service.rotary_cal_test_mm)
            new_val = calibrate_rotary_steps(
                float(service.rotary_y_steps), cmd, float(measured)
            )
            service.rotary_y_steps = new_val
            channel(
                _("Rotary Y steps/mm updated to {value:.3f} (test {cmd:.1f} mm, measured {meas:.3f} mm)").format(
                    value=new_val, cmd=cmd, meas=measured
                )
            )

        @service.console_argument("diameter", type=float, help=_("Object diameter mm"))
        @service.console_argument(
            "motor_steps", type=int, help=_("Full steps per rev (usually 200)")
        )
        @service.console_argument("microsteps", type=int, help=_("Driver microsteps"))
        @service.console_argument(
            "ratio", type=float, help=_("Gear ratio motor:chuck (e.g. 1.0)")
        )
        @service.console_command(
            "rotarysuggest",
            help=_("Suggest rotary Y steps/mm from motor and diameter"),
        )
        def rotary_suggest(channel, _, diameter=None, motor_steps=200, microsteps=16, ratio=1.0, **kwargs):
            if diameter is None:
                diameter = float(service.rotary_diameter_mm)
            val = suggest_rotary_steps_per_mm(
                int(motor_steps), int(microsteps), float(ratio), float(diameter)
            )
            channel(
                _("Suggested rotary Y steps/mm: {value:.3f} (D={d:.1f} mm)").format(
                    value=val, d=diameter
                )
            )

        @service.console_command(
            "rotaryfit",
            help=_("Scale emphasized elements to fit length × circumference"),
        )
        def rotary_fit(channel, _, **kwargs):
            self.fit_selection(channel)

    def fit_selection(self, channel=None):
        """
        Scale emphasized elements to fit rotary length × circumference.

        @param channel: optional console channel for messages
        @return: (success, message)
        """
        _ = self.service._
        if not self.active:
            msg = _("Enable rotary mode first.")
            if channel is not None:
                channel(msg)
            return False, msg
        elems = list(self.service.elements.elems(emphasized=True))
        if not elems:
            msg = _("Select artwork on the scene, then click Fit selection.")
            if channel is not None:
                channel(msg)
            return False, msg
        length = float(self.service.rotary_length_mm)
        circ = circumference_mm(float(self.service.rotary_diameter_mm))
        if length <= 0 or circ <= 0:
            msg = _("Set outside diameter and usable length first.")
            if channel is not None:
                channel(msg)
            return False, msg
        renderer = _prepare_fit_selection(
            elems, self.service.elements, self.service.kernel
        )
        bb = self.service.elements.selected_area()
        if bb is None:
            msg = _("Could not get selection bounds.")
            if channel is not None:
                channel(msg)
            return False, msg
        w_mm = _native_extent_to_mm(bb[2] - bb[0])
        h_mm = _native_extent_to_mm(bb[3] - bb[1])
        if w_mm <= 0 or h_mm <= 0:
            msg = _("Selection has no size.")
            if channel is not None:
                channel(msg)
            return False, msg
        if w_mm > _FIT_MAX_DIM_MM or h_mm > _FIT_MAX_DIM_MM:
            msg = _(
                "Selection bounds look wrong ({w:.1f} × {h:.1f} mm). "
                "Delete the text and add it again, or use Undo."
            ).format(w=w_mm, h=h_mm)
            if channel is not None:
                channel(msg)
            return False, msg
        if w_mm < _FIT_MIN_MM or h_mm < _FIT_MIN_MM:
            msg = _(
                "Selection is too small ({w:.2f} × {h:.2f} mm). "
                "Use Undo, delete the broken text, and add it again before Fit."
            ).format(w=w_mm, h=h_mm)
            if channel is not None:
                channel(msg)
            return False, msg
        sx = length / w_mm
        sy = circ / h_mm
        scale = min(sx, sy)
        if scale < _FIT_MIN_SCALE or scale > _FIT_MAX_SCALE:
            msg = _(
                "Fit scale {s:.4f} is out of range — check selection size "
                "({w:.1f} × {h:.1f} mm)."
            ).format(s=scale, w=w_mm, h=h_mm)
            if channel is not None:
                channel(msg)
            return False, msg
        cx = (bb[0] + bb[2]) / 2
        cy = (bb[1] + bb[3]) / 2
        with self.service.elements.undoscope("Rotary fit"):
            for node in elems:
                _apply_uniform_scale(node, scale, cx, cy, renderer)
                try:
                    node.modified()
                except AttributeError:
                    pass
        self.service.signal("refresh_scene", "Scene")
        msg = _("Fitted selection to {len:.1f} × {circ:.1f} mm (scale {s:.3f})").format(
            len=length, circ=circ, s=scale
        )
        if channel is not None:
            channel(msg)
        return True, msg

    def _print_status(self, channel):
        _ = self.service._
        d = float(self.service.rotary_diameter_mm)
        circ = circumference_mm(d)
        channel(_("Rotary active: {flag}").format(flag=self.active))
        channel(_("Diameter: {d:.2f} mm  →  circumference: {c:.2f} mm").format(d=d, c=circ))
        channel(
            _("Length: {l:.2f} mm  |  Y steps: {ry:.3f}  |  flat $101: {fy:.3f}").format(
                l=float(self.service.rotary_length_mm),
                ry=float(self.service.rotary_y_steps),
                fy=float(self.service.rotary_flat_y_steps),
            )
        )
        channel(
            _("Effective scale X={sx:.4f} Y={sy:.4f}  |  Y GRBL factor={yf:.4f}").format(
                sx=self.effective_scale_x(),
                sy=self.effective_scale_y(),
                yf=self.y_grbl_factor(),
            )
        )

    def effective_scale_x(self):
        if self.service.rotary_auto_length_scale:
            bw = bed_length_mm(self.service)
            return length_scale_x(float(self.service.rotary_length_mm), bw)
        return float(self.service.rotary_scale_x)

    def effective_scale_y(self):
        if self.service.rotary_auto_wrap_scale:
            bh = bed_height_mm(self.service)
            return wrap_scale_y(float(self.service.rotary_diameter_mm), bh)
        return float(self.service.rotary_scale_y)

    def y_grbl_factor(self):
        if not self.active:
            return 1.0
        if self.service.rotary_firmware_steps:
            return 1.0
        if not self.service.rotary_steps_compensate:
            return 1.0
        return y_steps_factor(
            float(self.service.rotary_flat_y_steps),
            float(self.service.rotary_y_steps),
        )

    def apply_firmware_steps(self, driver):
        if not self.active or not self.service.rotary_firmware_steps:
            return False
        driver(f"$101={float(self.service.rotary_y_steps):.3f}{driver.line_end}")
        driver.wait_finish()
        return True

    def restore_firmware_steps(self, driver):
        if not self.service.rotary_firmware_steps:
            return
        driver(f"$101={float(self.service.rotary_flat_y_steps):.3f}{driver.line_end}")
        driver.wait_finish()

    @property
    def scale_x(self):
        return self.effective_scale_x()

    @property
    def scale_y(self):
        return self.effective_scale_y()

    @property
    def active(self):
        return self.service.rotary_active

    @property
    def flip_x(self):
        return self.service.rotary_flip_x

    @property
    def flip_y(self):
        return self.service.rotary_flip_y

    @property
    def suppress_home(self):
        return self.service.suppress_home

    @property
    def home_x_only(self):
        return self.service.rotary_home_x_only

    @lookup_listener("service/device/active")
    @signal_listener("rotary_scale_x")
    @signal_listener("rotary_scale_y")
    @signal_listener("rotary_active")
    @signal_listener("rotary_flip_x")
    @signal_listener("rotary_flip_y")
    @signal_listener("rotary_diameter_mm")
    @signal_listener("rotary_length_mm")
    @signal_listener("rotary_auto_wrap_scale")
    @signal_listener("rotary_auto_length_scale")
    @signal_listener("rotary_flat_y_steps")
    @signal_listener("rotary_y_steps")
    @signal_listener("rotary_steps_compensate")
    @signal_listener("rotary_firmware_steps")
    def rotary_settings_changed(self, origin=None, *args):
        if origin is not None and origin != self.service.path:
            return
        device = self.service.device
        device.realize()
        self.service.signal("refresh_scene", "Scene")

    @signal_listener("view;realized")
    def realize(self, origin=None, *args):
        """
        Do not warp device.view — that breaks scene rendering (text/paths).
        Wrap and steps apply at job time in the GRBL driver only.
        """
        return

    def service_detach(self, *args, **kwargs):
        pass

    def service_attach(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass

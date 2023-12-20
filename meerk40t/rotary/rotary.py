from meerk40t.kernel import signal_listener, Module
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "preregister":
        kernel.register("module/Rotary", Rotary)


class Rotary(Module):
    """
    Rotary Module provides rotary information about the selected rotary you intend to use.
    """

    def __init__(self, context, name, index=0):
        self.parent = context
        context = context.derive(f"rotary{index}")
        Module.__init__(self, context, name)
        self.index = index
        _ = context._
        choices = [
            {
                "attr": "active",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Rotary-Mode active"),
                "tip": _("Is the rotary mode active for this device"),
            },
            # {
            #     "attr": "axis",
            #     "object": rotary,
            #     "default": 1,
            #     "type": int,
            #     "label": _("Rotary Axis:"),
            #     "tip": _("Which axis does the rotary use?"),
            # },
            {
                "attr": "scale_x",
                "object": context,
                "default": 1.0,
                "type": float,
                "label": _("X-Scale"),
                "tip": _("Scale that needs to be applied to the X-Axis"),
                "conditional": (context, "active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "scale_y",
                "object": context,
                "default": 1.0,
                "type": float,
                "label": _("Y-Scale"),
                "tip": _("Scale that needs to be applied to the Y-Axis"),
                "conditional": (context, "active"),
                "subsection": _("Scale"),
            },
            {
                "attr": "supress_home",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Ignore Home"),
                "tip": _("Ignore Home-Command"),
                "conditional": (self, "active"),
            },
            {
                "attr": "flip_x",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Mirror X"),
                "tip": _("Mirror the elements on the X-Axis"),
                "conditional": (context, "active"),
                "subsection": _("Mirror Output"),
            },
            {
                "attr": "flip_y",
                "object": context,
                "default": False,
                "type": bool,
                "label": _("Mirror Y"),
                "tip": _("Mirror the elements on the Y-Axis"),
                "conditional": (context, "active"),
                "subsection": _("Mirror Output"),
            },
        ]
        self.parent.register_choices("rotary", choices)

        @context.console_command(
            "rotary",
            help=_("Rotary base command"),
            output_type="rotary",
        )
        def rotary(command, channel, _, data=None, **kwargs):
            channel(
                f"Rotary {self.index} set to scale: {context.scale_x}, scale:{context.scale_y}"
            )
            return "rotary", None

        @context.console_command(
            "rotaryscale", help=_("Rotary Scale selected elements")
        )
        def apply_rotary_scale(*args, **kwargs):
            sx = context.scale_x
            sy = context.scale_y
            x, y = context.device.current
            matrix = Matrix(f"scale({sx}, {sy}, {x}, {y})")
            for node in context.elements.elems():
                if hasattr(node, "rotary_scale"):
                    # This element is already scaled
                    return
                try:
                    node.rotary_scale = sx, sy
                    node.matrix *= matrix
                    node.modified()
                except AttributeError:
                    pass

    @property
    def scale_x(self):
        return self.context.scale_x

    @property
    def scale_y(self):
        return self.context.scale_y

    @property
    def active(self):
        return self.context.active

    @property
    def flip_x(self):
        return self.context.flip_x

    @property
    def flip_y(self):
        return self.context.flip_y

    @signal_listener("scale_x")
    @signal_listener("scale_y")
    @signal_listener("active")
    @signal_listener("flip_x")
    @signal_listener("flip_y")
    def rotary_settings_changed(self, origin=None, *args):
        """
        Rotary settings were changed. We force the current device to realize

        @param origin:
        @param args:
        @return:
        """
        if origin is not None and origin != self.context.path:
            return
        device = self.context.device
        device.realize()

    @signal_listener("view;realized")
    def realize(self, origin=None, *args):
        """
        Realization of current device requires that device to be additionally updated with rotary
        @param origin:
        @param args:
        @return:
        """
        if not self.context.active:
            return
        device = self.context.device
        device.view.scale(self.context.scale_x, self.context.scale_y)
        if self.context.flip_x:
            device.view.flip_x()
        if self.context.flip_y:
            device.view.flip_y()

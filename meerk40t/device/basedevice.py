from ..kernel import Modifier

INTERPRETER_STATE_RAPID = 0
INTERPRETER_STATE_FINISH = 1
INTERPRETER_STATE_PROGRAM = 2
INTERPRETER_STATE_RASTER = 3
INTERPRETER_STATE_MODECHANGE = 4

PLOT_FINISH = 256
PLOT_RAPID = 4
PLOT_JOG = 2
PLOT_SETTING = 128
PLOT_AXIS = 64
PLOT_DIRECTION = 32


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        pass
        # context = kernel.get_context('/')

        # @context.console_option("path", "p", type=str, help="Path to Device")
        # @context.console_command(
        #     "device",
        #     help="device",
        #     output_type="device"
        # )
        # def device(channel, _, path=None, **kwargs):
        #     if path is None:
        #         return None
        #     else:
        #         device_context = context.get_context(path)
        #     if not hasattr(device_context, "spooler"):
        #         device_context.activate("modifier/Spooler")
        #     return "device", device_context

        # @context.console_command(
        #     "list",
        #     help="list devices",
        #     input_type="device",
        #     output_type="device",
        # )
        # def list(channel, _, data, **kwargs):
        #     channel(_("----------"))
        #     channel(_("Devices:"))
        #     for i, ctx_name in enumerate(kernel.contexts):
        #         ctx = kernel.contexts[ctx_name]
        #         if hasattr(ctx, "spooler"):
        #             channel("Device: %s, %s" % (ctx._path, str(ctx)))
        #     channel("----------")
        #     return "device", data

        # @context.console_command(
        #     "type",
        #     help="list device types",
        #     input_type="device",
        #     output_type="device",
        # )
        # def list_type(channel, _, data, **kwargs):
        #     channel(_("----------"))
        #     channel(_("Backends permitted:"))
        #     for i, name in enumerate(context.match("device/", suffix=True)):
        #         channel("%d: %s" % (i + 1, name))
        #     channel(_("----------"))
        #     return "device", data

        #
        # @context.console_command(
        #     "activate",
        #     help="activate device",
        #     input_type="device",
        #     output_type="device",
        # )
        # def activate(channel, _, data, **kwargs):
        #     channel(_("Device at context '%s' activated" % data._path))
        #     return "device", data
        #
        # @context.console_argument("device", help="Device to initialize...")
        # @context.console_command(
        #     "init",
        #     help="init <device>, eg. init Lhystudios",
        #     input_type="device",
        #     output_type="device",
        # )
        # def init(channel, _, data, device=None, **kwargs):
        #     if device is None:
        #         raise SyntaxError
        #     try:
        #         data.activate("device/%s" % device)
        #     except KeyError:
        #         channel(_("Device %s is not valid type. 'device type' for a list of valid types."))
        #         return
        #     channel(_("Device %s, initialized at %s" % (device, data._path)))
        #     return "device", data


# class Device(Modifier):
#     def __init__(
#         self, context, interpreter=None, name=None, channel=None, *args, **kwargs
#     ):
#         Modifier.__init__(self, context, name, channel)
#         self.context.activate("modifier/Spooler")
#         self.spooler = self.context.spooler
#         if interpreter is not None:
#             self.context.activate(interpreter)
#         else:
#             self.interpreter = None
#         self.pipes = []
#
#     def __repr__(self):
#         return "Spooler()"
#
#     def attach(self, *a, **kwargs):
#         """Overloaded attach to demand .spooler attribute."""
#         self.context.spooler = self.spooler
#         self.context.pipes = self.pipes
#         self.context.interpreter = self.interpreter
#

from meerk40t.gui.icons import icons8_move_50, icons8_route_50, icons8_connected_50, icons8_opened_folder_50, \
    icons8_save_50, icons8_laser_beam_52, icons8_laser_beam_hazard2_50, icons8_fantasy_50, icons8_comments_50, \
    icons8_console_50, icons8_camera_50, icons8_pause_50, icons8_emergency_stop_button_50, icons8_manager_50, \
    icons8_computer_support_50, icons8_administrative_tools_50, icons8_keyboard_50, icons8_roll_50
from meerk40t.gui.legacy.configuration import Configuration
from meerk40t.gui.legacy.controller import Controller
from meerk40t.gui.legacy.file.fileoutput import FileOutput
from meerk40t.gui.legacy.lhystudios.lhystudiosaccel import LhystudiosAccelerationChart
from meerk40t.gui.legacy.lhystudios.lhystudioscontrollergui import (
    LhystudiosControllerGui,
)
from meerk40t.gui.legacy.lhystudios.lhystudiosdrivergui import LhystudiosDriverGui
from meerk40t.gui.legacy.moshi.moshicontrollergui import MoshiControllerGui
from meerk40t.gui.legacy.moshi.moshidrivergui import MoshiDriverGui
from meerk40t.gui.legacy.devicespanel import DeviceManager
from meerk40t.gui.legacy.tcp.tcpcontroller import TCPController
from meerk40t.gui.legacy.usbconnect import UsbConnect

from meerk40t.kernel import Module

try:
    import wx
except ImportError as e:
    from meerk40t.core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("module/LegacyGui", LegacyGui)
    elif lifecycle == "boot":
        kernel.get_context("legacy").add_service_delegate(
            kernel.get_context("legacy").open("module/LegacyGui")
        )


class LegacyGui(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)

    def attach(self):
        pass

    def detach(self):
        pass

    def initialize(self, *a, **kwargs):
        self.context.listen("active", self.on_active_switch)
        self.context.listen("controller", self.on_controller)

    def finalize(self, *args, **kwargs):
        self.context.unlisten("active", self.on_active_switch)
        self.context.unlisten("controller", self.on_controller)

    def on_controller(self, origin, original_origin, *args):
        split = original_origin.split("/")
        if split[0] == "lhystudios":
            self.context(
                "window -p %s open %s/Controller\n" % (original_origin, split[0])
            )

    def on_active_switch(self, origin, *args):
        legacy_device = self.context
        output = legacy_device.default_output()
        if output is None:
            legacy_device.register("window/Controller", Controller)
            Controller.required_path = legacy_device.root.path
        elif output.type == "lhystudios":
            legacy_device.register("window/Controller", "window/lhystudios/Controller")
            LhystudiosControllerGui.required_path = output.context.path
            legacy_device.register(
                "window/AccelerationChart", "window/lhystudios/AccelerationChart"
            )
            LhystudiosAccelerationChart.required_path = output.context.path
        elif output.type == "moshi":
            legacy_device.register("window/Controller", "window/moshi/Controller")
            MoshiControllerGui.required_path = output.context.path
        elif output.type == "tcp":
            legacy_device.register("window/Controller", "window/tcp/Controller")
            TCPController.required_path = output.context.path
        elif output.type == "file":
            legacy_device.register("window/Controller", "window/file/Controller")
            FileOutput.required_path = output.context.path

        driver = legacy_device.default_driver()
        if driver is None:
            legacy_device.register("window/Configuration", Configuration)
            Configuration.required_path = legacy_device.root.path
        elif driver.type == "lhystudios":
            legacy_device.register(
                "window/Configuration", "window/lhystudios/Configuration"
            )
            LhystudiosDriverGui.required_path = output.context.path
        elif driver.type == "moshi":
            legacy_device.register("window/Configuration", "window/moshi/Configuration")
            MoshiDriverGui.required_path = output.context.path

    @staticmethod
    def sub_register(kernel):
        legacy_device = kernel.get_context("legacy")
        legacy_device.register("window/Controller", Controller)
        legacy_device.register("window/Configuration", Configuration)
        legacy_device.register("window/DeviceManager", DeviceManager)
        legacy_device.register("window/UsbConnect", UsbConnect)

        legacy_device.register("window/default/Controller", Controller)
        legacy_device.register("window/default/Configuration", Configuration)
        legacy_device.register("window/lhystudios/Controller", LhystudiosControllerGui)
        legacy_device.register("window/lhystudios/Configuration", LhystudiosDriverGui)
        legacy_device.register(
            "window/lhystudios/AccelerationChart", LhystudiosAccelerationChart
        )
        legacy_device.register("window/moshi/Controller", MoshiControllerGui)
        legacy_device.register("window/moshi/Configuration", MoshiDriverGui)
        legacy_device.register("window/tcp/Controller", TCPController)
        legacy_device.register("window/file/Controller", FileOutput)
        _ = kernel.translation

        context = legacy_device
        legacy_device.register(
            "button/project/Open",
            {
                "label": _("Open"),
                "icon": icons8_opened_folder_50,
                "tip": _("Opens new project"),
                "action": lambda e: context(".dialog_load\n"),
            },
        )
        legacy_device.register(
            "button/project/Save",
            {
                "label": _("Save"),
                "icon": icons8_save_50,
                "tip": _("Saves a project to disk"),
                "action": lambda e: context(".dialog_save\n"),
            },
        )
        #
        # legacy_device.register(
        #     "button/project/ExecuteJob",
        #     {
        #         "label": _("Execute Job"),
        #         "icon": icons8_laser_beam_52,
        #         "tip": _("Execute the current laser project"),
        #         "action": lambda v: context("window toggle ExecuteJob 0\n"),
        #     },
        # )

        # def open_simulator(v=None):
        #     with wx.BusyInfo(_("Preparing simulation...")):
        #         context(
        #             "plan0 copy preprocess validate blob preopt optimize\nwindow toggle Simulation 0\n"
        #         ),
        #
        # legacy_device.register(
        #     "button/project/Simulation",
        #     {
        #         "label": _("Simulate"),
        #         "icon": icons8_laser_beam_hazard2_50,
        #         "tip": _("Simulate the current laser job"),
        #         "action": open_simulator
        #     },
        # )

        # legacy_device.register(
        #     "button/project/RasterWizard",
        #     {
        #         "label": _("RasterWizard"),
        #         "icon": icons8_fantasy_50,
        #         "tip": _("Run RasterWizard"),
        #         "action": lambda v: context("window toggle RasterWizard\n"),
        #     },
        # )

        # legacy_device.register(
        #     "button/project/Notes",
        #     {
        #         "label": _("Notes"),
        #         "icon": icons8_comments_50,
        #         "tip": _("Open Notes Window"),
        #         "action": lambda v: context("window toggle Notes\n"),
        #     },
        # )
        # legacy_device.register(
        #     "button/project/Console",
        #     {
        #         "label": _("Console"),
        #         "icon": icons8_console_50,
        #         "tip": _("Open Console Window"),
        #         "action": lambda v: context("window toggle Console\n"),
        #     },
        # )

        # ==========
        # CONTROL PANEL
        # ==========

        # legacy_device.register(
        #     "button/control/Navigation",
        #     {
        #         "label": _("Navigation"),
        #         "icon": icons8_move_50,
        #         "tip": _("Opens Navigation Window"),
        #         "action": lambda v: legacy_device("window toggle Navigation\n"),
        #     },
        # )

        # legacy_device.register(
        #     "button/control/Camera",
        #     {
        #         "label": _("Camera"),
        #         "icon": icons8_camera_50,
        #         "tip": _("Opens Camera Window"),
        #         "action": context("window toggle CameraInterface %d\n" % 1),
        #     },
        # )

        # legacy_device.register(
        #     "button/control/Spooler",
        #     {
        #         "label": _("Spooler"),
        #         "icon": icons8_route_50,
        #         "tip": _("Opens Spooler Window"),
        #         "action": lambda v: legacy_device("window toggle JobSpooler\n"),
        #     },
        # )
        # legacy_device.register(
        #     "button/control/Controller",
        #     {
        #         "label": _("Controller"),
        #         "icon": icons8_connected_50,
        #         "tip": _("Opens Controller Window"),
        #         "action": lambda v: legacy_device("window toggle Controller\n"),
        #     },
        # )

        legacy_device.register(
            "button/control/Pause",
            {
                "label": _("Pause"),
                "icon": icons8_emergency_stop_button_50,
                "tip": _("Pause the laser"),
                "action": lambda v: context("pause\n"),
            },
        )

        legacy_device.register(
            "button/control/Stop",
            {
                "label": _("Stop"),
                "icon": icons8_pause_50,
                "tip": _("Emergency stop the laser"),
                "action": lambda v: context("estop\n"),
            },
        )
        # ==========
        # CONFIGURATION PANEL
        # ==========

        # legacy_device.register(
        #     "button/config/DeviceManager",
        #     {
        #         "label": _("Devices"),
        #         "icon": icons8_manager_50,
        #         "tip": _("Opens DeviceManager Window"),
        #         "action": lambda v: context("window toggle DeviceManager\n"),
        #     },
        # )
        # legacy_device.register(
        #     "button/config/Configuration",
        #     {
        #         "label": _("Config"),
        #         "icon": icons8_computer_support_50,
        #         "tip": _("Opens device-specfic configuration window"),
        #         "action": lambda v: context("window toggle Configuration\n"),
        #     },
        # )
        # from sys import platform
        # if platform != "darwin":
        #     legacy_device.register(
        #         "button/config/Preferences",
        #         {
        #             "label": _("Preferences"),
        #             "icon": icons8_administrative_tools_50,
        #             "tip": _("Opens Preferences Window"),
        #             "action": lambda v: context("window toggle Preferences\n"),
        #         },
        #     )
        # legacy_device.register(
        #     "button/config/Keymap",
        #     {
        #         "label": _("Keymap"),
        #         "icon": icons8_keyboard_50,
        #         "tip": _("Opens Keymap Window"),
        #         "action": lambda v: context("window toggle Keymap\n"),
        #     },
        # )
        # legacy_device.register(
        #     "button/config/Rotary",
        #     {
        #         "label": _("Rotary"),
        #         "icon": icons8_roll_50,
        #         "tip": _("Opens Rotary Window"),
        #         "action": lambda v: context("window -p rotary/1 toggle Rotary\n"),
        #     },
        # )
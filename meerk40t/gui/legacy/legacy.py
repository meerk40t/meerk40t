from meerk40t.gui.legacy.configuration import Configuration
from meerk40t.gui.legacy.controller import Controller
from meerk40t.gui.legacy.file.fileoutput import FileOutput
from meerk40t.gui.legacy.lhystudios.lhystudiosaccel import LhystudiosAccelerationChart
from meerk40t.gui.legacy.lhystudios.lhystudioscontrollergui import LhystudiosControllerGui
from meerk40t.gui.legacy.lhystudios.lhystudiosdrivergui import LhystudiosDriverGui
from meerk40t.gui.legacy.moshi.moshicontrollergui import MoshiControllerGui
from meerk40t.gui.legacy.moshi.moshidrivergui import MoshiDriverGui
from meerk40t.gui.legacy.devicespanel import DeviceManager
from meerk40t.gui.legacy.tcp.tcpcontroller import TCPController
from meerk40t.gui.legacy.usbconnect import UsbConnect

from meerk40t.kernel import Modifier

try:
    import wx
except ImportError as e:
    from meerk40t.core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("modifier/LegacyGui", LegacyGui)
    elif lifecycle == "boot":
        kernel.get_context('legacy').activate("modifier/LegacyGui")


class LegacyGui(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)

    def attach(self, *a, **kwargs):
        self.context.listen("active", self.on_active_switch)
        self.context.listen("controller", self.on_controller)

    def detach(self, *args, **kwargs):
        self.context.unlisten("active", self.on_active_switch)
        self.context.unlisten("controller", self.on_controller)

    def on_controller(self, origin, original_origin, *args):
        split = original_origin.split("/")
        if split[0] == "lhystudios":
            self.context("window -p %s open %s/Controller\n" % (original_origin, split[0]))

    def on_active_switch(self, origin, *args):
        legacy_device = self.context
        output = legacy_device.default_output()
        if output is None:
            legacy_device.register("window/Controller", Controller)
            Controller.required_path = legacy_device.root.path
        elif output.type == "lhystudios":
            legacy_device.register("window/Controller", LhystudiosControllerGui)
            LhystudiosControllerGui.required_path = output.context.path
            legacy_device.register("window/AccelerationChart", LhystudiosAccelerationChart)
            LhystudiosAccelerationChart.required_path = output.context.path
        elif output.type == "moshi":
            legacy_device.register("window/Controller", MoshiControllerGui)
            MoshiControllerGui.required_path = output.context.path
        elif output.type == "tcp":
            legacy_device.register("window/Controller", TCPController)
            TCPController.required_path = output.context.path
        elif output.type == "file":
            legacy_device.register("window/Controller", FileOutput)
            FileOutput.required_path = output.context.path
        driver = legacy_device.default_driver()
        if driver is None:
            legacy_device.register("window/Configuration", Configuration)
            Configuration.required_path = legacy_device.root.path
        elif driver.type == "lhystudios":
            legacy_device.register("window/Configuration", LhystudiosDriverGui)
            LhystudiosDriverGui.required_path = output.context.path
        elif driver.type == "moshi":
            legacy_device.register("window/Configuration", MoshiDriverGui)
            MoshiDriverGui.required_path = output.context.path

    @staticmethod
    def sub_register(kernel):
        legacy_device = kernel.get_context('legacy')
        legacy_device.register("window/Controller", Controller)
        legacy_device.register("window/Configuration", Configuration)
        legacy_device.register("window/DeviceManager", DeviceManager)
        legacy_device.register("window/UsbConnect", UsbConnect)
        legacy_device.register("window/default/Controller", Controller)
        legacy_device.register("window/default/Configuration", Configuration)
        legacy_device.register("window/lhystudios/Controller", LhystudiosControllerGui)
        legacy_device.register("window/lhystudios/Configuration", LhystudiosDriverGui)
        legacy_device.register("window/lhystudios/AccelerationChart", LhystudiosAccelerationChart)
        legacy_device.register("window/moshi/Controller", MoshiControllerGui)
        legacy_device.register("window/moshi/Configuration", MoshiDriverGui)
        legacy_device.register("window/tcp/Controller", TCPController)
        legacy_device.register("window/file/Controller", FileOutput)

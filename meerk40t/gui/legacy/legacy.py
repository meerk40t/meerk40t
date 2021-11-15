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


try:
    import wx
except ImportError as e:
    from meerk40t.core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")


def plugin(kernel, lifecycle):
    def on_active_switch(origin, *args):
        output = legacy_device.default_output()
        if output is None:
            legacy_device.register("window/Controller", Controller)
            Controller.required_path = kernel.root
        elif output.type == "lhystudios":
            legacy_device.register("window/Controller", LhystudiosControllerGui)
            legacy_device.register("window/AccelerationChart", LhystudiosAccelerationChart)
            LhystudiosControllerGui.required_path = output.context.path
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
            Configuration.required_path = kernel.root
        elif driver.type == "lhystudios":
            legacy_device.register("window/Configuration", LhystudiosDriverGui)
            LhystudiosDriverGui.required_path = output.context.path
        elif driver.type == "moshi":
            legacy_device.register("window/Configuration", MoshiDriverGui)
            MoshiDriverGui.required_path = output.context.path

    legacy_device = kernel.get_context('legacy')
    if lifecycle == "register":
        legacy_device.register("window/DeviceManager", DeviceManager)
        legacy_device.register("window/UsbConnect", UsbConnect)
        legacy_device.listen("active", on_active_switch)

    if lifecycle == "shutdown":
        legacy_device.unlisten("active", on_active_switch)
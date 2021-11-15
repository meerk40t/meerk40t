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
    legacy_device = kernel.get_context('legacy')
    if lifecycle == "register":
        legacy_device.register("window/DeviceManager", DeviceManager)
        legacy_device.register("window/UsbConnect", UsbConnect)
        legacy_device.register("window/default/Controller", Controller)
        legacy_device.register("window/default/Configuration", Configuration)
        legacy_device.register("window/tcp/Controller", TCPController)
        legacy_device.register("window/file/Controller", FileOutput)
        legacy_device.register("window/lhystudios/Configuration", LhystudiosDriverGui)
        legacy_device.register("window/lhystudios/Controller", LhystudiosControllerGui)
        legacy_device.register(
            "window/lhystudios/AccelerationChart", LhystudiosAccelerationChart
        )
        legacy_device.register("window/moshi/Configuration", MoshiDriverGui)
        legacy_device.register("window/moshi/Controller", MoshiControllerGui)

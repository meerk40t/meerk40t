# -*- coding: utf-8 -*-

import os
import sys
import traceback

from meerk40t.gui.wxmscene import SceneWindow

try:
    import wx
except ImportError as e:
    from ..core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")

from ..kernel import Module
from ..main import APPLICATION_NAME, APPLICATION_VERSION
from .about import About
from .bufferview import BufferView
from .configuration import Configuration
from .controller import Controller
from .executejob import ExecuteJob
from .file.fileoutput import FileOutput
from .groupproperties import GroupProperty
from .imageproperty import ImageProperty
from .keymap import Keymap
from .laserrender import LaserRender
from .lhystudios.lhystudiosaccel import LhystudiosAccelerationChart
from .lhystudios.lhystudioscontrollergui import LhystudiosControllerGui
from .lhystudios.lhystudiosdrivergui import LhystudiosDriverGui
from .moshi.moshicontrollergui import MoshiControllerGui
from .moshi.moshidrivergui import MoshiDriverGui
from .notes import Notes
from .operationproperty import OperationProperty
from .panes.camerapanel import CameraInterface
from .panes.consolepanel import Console
from .panes.devicespanel import DeviceManager
from .panes.navigationpanels import Navigation
from .panes.spoolerpanel import JobSpooler
from .pathproperty import PathProperty
from .preferences import Preferences
from .rasterwizard import RasterWizard
from .rotarysettings import RotarySettings
from .simulation import Simulation
from .tcp.tcpcontroller import TCPController
from .textproperty import TextProperty
from .usbconnect import UsbConnect
from .wxmmain import MeerK40t

"""
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed
open-source laser cutting software. See https://github.com/meerk40t/meerk40t
for full details.

wxMeerK40t is the primary gui addon for MeerK40t. It requires wxPython for the interface.
The Transformations work in Windows/OSX/Linux for wxPython 4.0+ (and likely before)

"""

MILS_IN_MM = 39.3701

GUI_START = True

_ = wx.GetTranslation


def plugin(kernel, lifecycle):
    global GUI_START
    kernel_root = kernel.root
    if lifecycle == "console":
        GUI_START = False

        @kernel.console_command("gui", help=_("starts the gui"))
        def gui_start(**kwargs):
            del kernel._registered["command/None/gui"]
            meerk40tgui = kernel_root.open("module/wxMeerK40t")
            kernel.console("window open MeerK40t\n")
            meerk40tgui.MainLoop()

    elif lifecycle == "preregister":
        kernel.register("module/wxMeerK40t", wxMeerK40t)
        kernel_root.open("module/wxMeerK40t")

        # Registers the render-op make_raster. This is used to do cut planning.
        renderer = LaserRender(kernel_root)
        kernel_root.register("render-op/make_raster", renderer.make_raster)
    elif lifecycle == "postboot":
        choices = [
            {
                "attr": "show_negative_guide",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("Show Negative Guide"),
                "tip": _(
                    "Extend the Guide rulers with negative values to assist lining up objects partially outside the left/top of the bed"
                ),
            },
            {
                "attr": "windows_save",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("Save Window Positions"),
                "tip": _("Open Windows at the same place they were last closed"),
            },
            {
                "attr": "auto_spooler",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("Launch Spooler on Job Start"),
                "tip": _("Open the Spooler window automatically when you Execute a Job"),
            },
            {
                "attr": "mouse_wheel_pan",
                "object": kernel.root,
                "default": True,
                "type": bool,
                "label": _("MouseWheel Pan"),
                "tip": "\n".join(
                    (
                        _("Unset: MouseWheel=Zoom. Shift+MouseWheel=Horizontal pan."),
                        _(
                            "Set: MouseWheel=Vertical pan. Ctrl+MouseWheel=Zoom. Shift+MouseWheel=Horizontal pan."
                        ),
                    )
                ),
            },
            {
                "attr": "mouse_pan_invert",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Invert MouseWheel Pan"),
                "tip": _(
                    "Reverses the direction of the MouseWheel for horizontal & vertical pan"
                )
            },
            {
                "attr": "mouse_zoom_invert",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Invert MouseWheel Zoom"),
                "tip": _("Reverses the direction of the MouseWheel for zoom"),
            },
            {
                "attr": "disable_tool_tips",
                "object": kernel.root,
                "default": False,
                "type": bool,
                "label": _("Disable ToolTips"),
                "tip": "\n".join(
                    (
                        _(
                            "If you do not want to see tooltips like this one, check this box."
                        ),
                        _("Particularly useful if you have a touch screen."),
                        _(
                            "Note: You will need to restart MeerK40t for any change to take effect."
                        ),
                    )
                ),
            },
        ]
        kernel.register_choices("preferences", choices)

    elif lifecycle == "mainloop":
        def interrupt_popup():
            dlg = wx.MessageDialog(
                None,
                _("Spooling Interrupted. Press OK to Continue."),
                _("Interrupt"),
                wx.OK,
            )
            dlg.ShowModal()
            dlg.Destroy()

        kernel_root.register("function/interrupt", interrupt_popup)

        def interrupt():
            from ..device.lasercommandconstants import (
                COMMAND_FUNCTION,
                COMMAND_WAIT_FINISH,
            )

            yield COMMAND_WAIT_FINISH
            yield COMMAND_FUNCTION, kernel_root.lookup("function/interrupt")

        kernel_root.register("plan/interrupt", interrupt)

        if GUI_START:
            meerk40tgui = kernel_root.open("module/wxMeerK40t")
            kernel.console("window open MeerK40t\n")
            for obj, window, sname in kernel.find("window/.*"):
                if kernel.read_persistent(bool, "%s/open_on_start" % window, False):
                    kernel.console("window open %s\n" % sname)
            meerk40tgui.MainLoop()


supported_languages = (
    ("en", u"English", wx.LANGUAGE_ENGLISH),
    ("it", u"italiano", wx.LANGUAGE_ITALIAN),
    ("fr", u"français", wx.LANGUAGE_FRENCH),
    ("de", u"Deutsch", wx.LANGUAGE_GERMAN),
    ("es", u"español", wx.LANGUAGE_SPANISH),
    ("zh", u"中文", wx.LANGUAGE_CHINESE),
    ("hu", u"Magyar", wx.LANGUAGE_HUNGARIAN),
    ("pt", u"português", wx.LANGUAGE_PORTUGUESE),
    ("pt-br", u"português brasileiro", wx.LANGUAGE_PORTUGUESE_BRAZILIAN),
)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class wxMeerK40t(wx.App, Module):
    """
    wxMeerK40t is the wx.App main class and a qualified Module for the MeerK40t kernel.
    Running MeerK40t without the wxMeerK40t gui is both possible and reasonable. This should not change the way the
    underlying code runs. It should just be a series of frames held together with the kernel.
    """

    def __init__(self, context, path):
        wx.App.__init__(self, 0)
        self.supported_languages = supported_languages
        import meerk40t.gui.icons as icons

        def run_later(command, *args):
            if wx.IsMainThread():
                command(*args)
            else:
                wx.CallAfter(command, *args)

        context._kernel.run_later = run_later

        icons.DARKMODE = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        icons.icon_r = 230
        icons.icon_g = 230
        icons.icon_b = 230
        Module.__init__(self, context, path)
        self.locale = None
        self.Bind(wx.EVT_CLOSE, self.on_app_close)
        self.Bind(wx.EVT_QUERY_END_SESSION, self.on_app_close)  # MAC DOCK QUIT.
        self.Bind(wx.EVT_END_SESSION, self.on_app_close)
        self.Bind(wx.EVT_END_PROCESS, self.on_app_close)
        # This catches events when the app is asked to activate by some other process
        self.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

        # App started add the except hook
        sys.excepthook = handleGUIException

    def on_app_close(self, event=None):
        try:
            if self.context is not None:
                self.context("quit\n")
        except AttributeError:
            pass

    def OnInit(self):
        return True

    def BringWindowToFront(self):
        try:  # it's possible for this event to come when the frame is closed
            self.GetTopWindow().Raise()
        except Exception:
            pass

    def OnActivate(self, event):
        # if this is an activate event, rather than something else, like iconize.
        if event.GetActive():
            self.BringWindowToFront()
        event.Skip()

    def MacReopenApp(self):
        """Called when the doc icon is clicked, and ???"""
        self.BringWindowToFront()

    def MacNewFile(self):
        try:
            if self.context is not None:
                self.context.elements.clear_all()
        except AttributeError:
            pass

    def MacPrintFile(self, file_path):
        pass

    def MacOpenFile(self, filename):
        try:
            if self.context is not None:
                self.context.elements.load(os.path.realpath(filename))
        except AttributeError:
            pass

    def MacOpenFiles(self, filenames):
        try:
            if self.context is not None:
                for filename in filenames:
                    self.context.elements.load(os.path.realpath(filename))
        except AttributeError:
            pass

    @staticmethod
    def sub_register(kernel):
        kernel.register("window/MeerK40t", MeerK40t)
        kernel.register("window/PathProperty", PathProperty)
        kernel.register("window/TextProperty", TextProperty)
        kernel.register("window/ImageProperty", ImageProperty)
        kernel.register("window/OperationProperty", OperationProperty)
        kernel.register("window/GroupProperty", GroupProperty)
        kernel.register("window/CameraInterface", CameraInterface)
        kernel.register("window/Terminal", Console)
        kernel.register("window/Console", Console)
        kernel.register("window/Preferences", Preferences)
        kernel.register("window/Rotary", RotarySettings)
        kernel.register("window/About", About)
        kernel.register("window/DeviceManager", DeviceManager)
        kernel.register("window/Keymap", Keymap)
        kernel.register("window/UsbConnect", UsbConnect)
        kernel.register("window/Navigation", Navigation)
        kernel.register("window/Notes", Notes)
        kernel.register("window/JobSpooler", JobSpooler)
        kernel.register("window/ExecuteJob", ExecuteJob)
        kernel.register("window/BufferView", BufferView)
        kernel.register("window/RasterWizard", RasterWizard)
        kernel.register("window/Simulation", Simulation)
        kernel.register("window/Scene", SceneWindow)

        kernel.register("window/default/Controller", Controller)
        kernel.register("window/default/Configuration", Configuration)
        kernel.register("window/tcp/Controller", TCPController)
        kernel.register("window/file/Controller", FileOutput)
        kernel.register("window/lhystudios/Configuration", LhystudiosDriverGui)
        kernel.register("window/lhystudios/Controller", LhystudiosControllerGui)
        kernel.register(
            "window/lhystudios/AccelerationChart", LhystudiosAccelerationChart
        )
        kernel.register("window/moshi/Configuration", MoshiDriverGui)
        kernel.register("window/moshi/Controller", MoshiControllerGui)

        context = kernel.root

        @kernel.console_option(
            "path",
            "p",
            type=str,
            default="/",
            help=_("Context Path at which to open the window"),
        )
        @kernel.console_command(
            "window", output_type="window", help=_("Base window command")
        )
        def window_base(channel, _, path=None, remainder=None, **kwargs):
            """
            Opens a MeerK40t window or provides information. This command is restricted to use with the wxMeerK40t gui.
            This also allows use of a -p flag that sets the context path for this window to operate at. This should
            often be restricted to where the windows are typically opened since their function and settings usually
            depend on the context used. The default root path is "/". Eg. "window -p / open Settings"
            """
            context = kernel.root
            if path is None:
                path = context
            else:
                path = kernel.get_context(path)

            if remainder is None:
                channel(_("----------"))
                channel(_("Loaded Windows in Context %s:") % str(context.path))
                for i, name in enumerate(context.opened):
                    if not name.startswith("window"):
                        continue
                    module = context.opened[name]
                    channel(_("%d: %s as type of %s") % (i + 1, name, type(module)))

                channel(_("----------"))
                channel(_("Loaded Windows in Device %s:") % str(path.path))
                for i, name in enumerate(path.opened):
                    if not name.startswith("window"):
                        continue
                    module = path.opened[name]
                    channel(_("%d: %s as type of %s") % (i + 1, name, type(module)))
                channel(_("----------"))
            return "window", path

        @kernel.console_command(
            "list",
            input_type="window",
            output_type="window",
            help=_("List available windows."),
        )
        def window_list(channel, _, data, **kwargs):
            channel(_("----------"))
            channel(_("Windows Registered:"))
            for i, name in enumerate(context.match("window")):
                name = name[7:]
                if "/" in name:
                    channel("%d: Specific Window: %s" % (i + 1, name))
                else:
                    channel("%d: %s" % (i + 1, name))
            return "window", data

        @kernel.console_option(
            "driver",
            "d",
            type=bool,
            action="store_true",
            help=_("Load Driver Specific Window"),
        )
        @kernel.console_option(
            "output",
            "o",
            type=bool,
            action="store_true",
            help=_("Load Output Specific Window"),
        )
        @kernel.console_option(
            "source",
            "s",
            type=str,
            help=_("Specify source window type"),
        )
        @kernel.console_argument("window", type=str, help=_("window to be opened"))
        @kernel.console_command(
            ("open", "toggle"),
            input_type="window",
            help=_("open/toggle the supplied window"),
        )
        def window_open(
            command,
            channel,
            _,
            data,
            window=None,
            driver=False,
            output=False,
            source=None,
            args=(),
            **kwargs
        ):
            path = data
            try:
                parent = context.gui
            except AttributeError:
                parent = None
            window_uri = "window/%s" % window
            context.root.setting(str, "active", "0")
            active = context.root.active
            if source is not None:
                active = source
            if output or driver:
                # Specific class subwindow
                try:
                    _spooler, _input_driver, _output = context.lookup("device", active)
                except TypeError:
                    channel(_("Device not found."))
                    return
                if output:
                    q = _output
                elif driver:
                    q = _input_driver
                else:
                    q = _input_driver
                t = "default"
                m = "/"
                if q is not None:
                    obj = q
                    try:
                        t = obj.type
                        m = obj.context.path
                    except AttributeError:
                        pass
                path = context.get_context(m)
                window_uri = "window/%s/%s" % (t, window)
                v = context.lookup(window_uri)
                if v is None:
                    window_uri = "window/%s/%s" % ("default", window)

            def window_open(*a, **k):
                path.open(window_uri, parent, *args)

            def window_close(*a, **k):
                path.close(window_uri, *args)

            if command == "open":

                if context.lookup(window_uri) is not None:
                    kernel.run_later(window_open, None)
                    channel(_("Window Opened."))
                else:
                    channel(_("No such window as %s" % window))
                    raise SyntaxError
            else:
                if context.lookup(window_uri) is not None:
                    try:
                        w = path.opened[window_uri]
                        kernel.run_later(window_close, None)
                        channel(_("Window Closed."))
                    except KeyError:
                        kernel.run_later(window_open, None)
                        channel(_("Window Opened."))
                else:
                    channel(_("No such window as %s" % window))
                    raise SyntaxError

        @kernel.console_argument("window", type=str, help=_("window to be closed"))
        @kernel.console_command(
            "close",
            input_type="window",
            output_type="window",
            help=_("close the supplied window"),
        )
        def window_close(channel, _, data, window=None, args=(), **kwargs):
            path = data
            try:
                parent = context.gui if hasattr(context, "gui") else None
                kernel.run_later(
                    lambda e: path.close("window/%s" % window, parent, *args), None
                )
                channel(_("Window closed."))
            except (KeyError, ValueError):
                channel(_("No such window as %s" % window))
            except IndexError:
                raise SyntaxError

        @kernel.console_argument("window", type=str, help=_("window to be reset"))
        @kernel.console_command(
            "reset",
            input_type="window",
            output_type="window",
            help=_("reset the supplied window, or '*' for all windows"),
        )
        def window_reset(channel, _, data, window=None, **kwargs):
            if kernel._config is not None:
                for context in list(kernel.contexts):
                    if context.startswith("window"):
                        del kernel.contexts[context]
                kernel._config.DeleteGroup("window")

        @kernel.console_command("refresh", help=_("Refresh the main wxMeerK40 window"))
        def scene_refresh(command, channel, _, **kwargs):
            context.signal("refresh_scene", "Scene")
            context.signal("rebuild_tree")
            channel(_("Refreshed."))

        @kernel.console_command("tooltips_enable", hidden=True)
        def tooltip_enable(command, channel, _, **kwargs):
            context.setting(bool, "disable_tool_tips", False)
            context.disable_tool_tips = False
            wx.ToolTip.Enable(not context.disable_tool_tips)

        @kernel.console_command("tooltips_disable", hidden=True)
        def tooltip_disable(command, channel, _, **kwargs):
            context.setting(bool, "disable_tool_tips", False)
            context.disable_tool_tips = True
            wx.ToolTip.Enable(not context.disable_tool_tips)

    def initialize(self, *args, **kwargs):
        context = self.context
        kernel = context.kernel

        try:  # pyinstaller internal location
            _resource_path = os.path.join(sys._MEIPASS, "locale")
            wx.Locale.AddCatalogLookupPathPrefix(_resource_path)
        except Exception:
            pass

        try:  # Mac py2app resource
            _resource_path = os.path.join(os.environ["RESOURCEPATH"], "locale")
            wx.Locale.AddCatalogLookupPathPrefix(_resource_path)
        except Exception:
            pass

        wx.Locale.AddCatalogLookupPathPrefix("locale")

        # Default Locale, prepended. Check this first.
        basepath = os.path.abspath(os.path.dirname(sys.argv[0]))
        localedir = os.path.join(basepath, "locale")
        wx.Locale.AddCatalogLookupPathPrefix(localedir)

        kernel.translation = wx.GetTranslation
        kernel.set_config(wx.FileConfig(kernel.profile))
        context.app = self  # Registers self as kernel.app

        context.setting(int, "language", None)
        context.register("control/Delete Settings", self.clear_control)
        language = context.language
        if language is not None and language != 0:
            self.update_language(language)

    def clear_control(self):
        kernel = self.context.kernel
        if kernel._config is not None:
            kernel._config.DeleteAll()
            kernel._config = None
            kernel.shutdown()

    def update_language(self, lang):
        """
        Update language to the requested language.
        """
        context = self.context
        try:
            language_code, language_name, language_index = supported_languages[lang]
        except (IndexError, ValueError):
            return
        context.language = lang

        if self.locale:
            assert sys.getrefcount(self.locale) <= 2
            del self.locale
        self.locale = wx.Locale(language_index)
        # wxWidgets is broken. IsOk()==false and pops up error dialog, but it translates fine!
        if self.locale.IsOk() or "linux" in sys.platform:
            self.locale.AddCatalog("meerk40t")
        else:
            self.locale = None
        context.signal("language", (lang, language_code, language_name, language_index))


# end of class MeerK40tGui
def send_file_to_developers(filename):
    """
    Loads a file to send data to the developers.

    @param filename: file to send
    @return:
    """
    try:
        with open(filename, "r") as f:
            data = f.read()
    except:
        if data is None:
            return  # There is no file, there is no data.
    send_data_to_developers(filename, data)


def send_data_to_developers(filename, data):
    """
    Sends crash log to a server using rfc1341 7.2 The multipart Content-Type
    https://www.w3.org/Protocols/rfc1341/7_2_Multipart.html

    @param filename: filename to use when sending file
    @param data: data to send
    @return:
    """
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ipaddr = socket.gethostbyname("api.anonfiles.com")
    s.connect((ipaddr, 80))
    boundary = "----------------meerk40t-boundary"
    file_head = list()
    file_head.append("--" + boundary)
    file_head.append(
        'Content-Disposition: form-data; name="file"; filename="%s"' % filename
    )
    file_head.append("Content-Type: text/plain")
    file_head.append("")
    part = "\x0D\x0A".join(file_head)
    terminal = "--" + boundary + "--"
    payload = "\x0D\x0A".join((part, data, terminal, ""))
    http_req = list()
    http_req.append("POST /upload?token=630f908431136ef4 HTTP/1.1")
    http_req.append("Host: api.anonfiles.com")
    http_req.append("User-Agent: meerk40t/0.0.1")
    http_req.append("Accept: */*")
    http_req.append("Content-Length: %d" % (len(payload)))
    http_req.append("Content-Type: multipart/form-data; boundary=%s" % boundary)
    http_req.append("")
    header = "\x0D\x0A".join(http_req)
    request = "\x0D\x0A".join((header, payload))
    s.send(bytes(request, "utf-8"))
    response = s.recv(4096)
    response = response.decode("utf-8")
    print(response)
    s.close()
    if response is None or len(response) == 0:
        http_code = "No Response."
    else:
        http_code = response.split("\n")[0]

    if http_code.startswith("HTTP/1.1 200 OK"):
        http_code = response.split("\n")[0]
        dlg = wx.MessageDialog(
            None,
            _("We got your message. Thank you for helping\n\n") + str(http_code),
            _("Thanks"),
            wx.OK,
        )
        dlg.ShowModal()
        dlg.Destroy()
    else:
        MEERK40T_ISSUES = "https://github.com/meerk40t/meerk40t/issues"
        dlg = wx.MessageDialog(
            None,
            _(
                "We're sorry, that didn't work. Raise an issue on the github please.\n\n The log file will be in your working directory.\n"
            )
            + MEERK40T_ISSUES
            + "\n\n"
            + str(http_code),
            _("Thanks"),
            wx.OK,
        )
        dlg.ShowModal()
        dlg.Destroy()


def handleGUIException(exc_type, exc_value, exc_traceback):
    """
    Handler for errors. Save error to a file, and create dialog.

    :param exc_type:
    :param exc_value:
    :param exc_traceback:
    :return:
    """
    wxversion = "wx"
    try:
        wxversion = wx.version()
    except:
        pass

    error_log = "MeerK40t crash log. Version: %s on %s - %s\n" % (
        APPLICATION_VERSION,
        sys.platform,
        wxversion,
    )
    error_log += "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_log)
    try:
        import datetime

        filename = "MeerK40t-{date:%Y-%m-%d_%H_%M_%S}.txt".format(
            date=datetime.datetime.now()
        )
    except Exception:  # I already crashed once, if there's another here just ignore it.
        filename = "MeerK40t-Crash.txt"

    try:
        try:
            with open(filename, "w") as file:
                file.write(error_log)
                print(file)
        except PermissionError:
            from meerk40t.kernel import get_safe_path

            path = get_safe_path(APPLICATION_NAME)
            with open(path.joinpath(filename), "w") as file:
                file.write(error_log)
                print(file)
    except Exception:
        # I already crashed once, if there's another here just ignore it.
        pass

    # Ask to send file.
    message = _(
        """
    Good news MeerK40t User! MeerK40t encountered an crash!

    You now have the ability to help meerk40t's development by sending us the log.

    Send the following data to the MeerK40t team?
    ------
    """
    )
    message += error_log
    answer = wx.MessageBox(
        message, _("Crash Detected! Send Log?"), wx.YES_NO | wx.CANCEL, None
    )
    if answer == wx.YES:
        send_data_to_developers(filename, error_log)

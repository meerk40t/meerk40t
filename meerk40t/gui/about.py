import datetime

import wx

from ..main import APPLICATION_NAME, APPLICATION_VERSION
from .icons import icon_about, icon_meerk40t
from .mwindow import MWindow
from .wxutils import ScrolledPanel, StaticBoxSizer, wxButton

_ = wx.GetTranslation

HEADER_TEXT = (
    "MeerK40t is a free MIT Licensed open source project\n"
    + "for lasering on K40 Devices.\n\n"
    + "Participation in the project is highly encouraged.\n"
    + "Past participation, and continuing participation is graciously thanked.\n"
    + "This program is mostly the brainchild of Tatarize,\n"
    + "who sincerely hopes his contributions will be but\n"
    + "the barest trickle that becomes a raging river."
)


class AboutPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        self.bitmap_button_1 = wx.BitmapButton(
            self, wx.ID_ANY, icon_meerk40t.GetBitmap()
        )

        self.__set_properties()
        self.__do_layout()

        name = self.context.kernel.name
        version = self.context.kernel.version
        self.meerk40t_about_version_text.SetLabelText(f"{name}\nv{version}")

    def __set_properties(self):
        self.bitmap_button_1.SetSize(self.bitmap_button_1.GetBestSize())
        self.meerk40t_about_version_text = wx.StaticText(self, wx.ID_ANY, "MeerK40t")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: About.__do_layout
        vsizer_main = wx.BoxSizer(wx.VERTICAL)
        hsizer_pic_info = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_pic_iver = wx.BoxSizer(wx.VERTICAL)
        vsizer_pic_iver.Add(self.bitmap_button_1, 0, 0, 0)
        self.meerk40t_about_version_text.SetFont(
            wx.Font(
                10,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        vsizer_pic_iver.Add(self.meerk40t_about_version_text, 0, 0, 0)
        hsizer_pic_info.Add(vsizer_pic_iver, 0, wx.EXPAND, 0)
        hsizer_pic_info.AddSpacer(5)
        self.meerk40t_about_text_header = wx.StaticText(
            self,
            wx.ID_ANY,
            _(HEADER_TEXT),
        )
        self.meerk40t_about_text_header.SetFont(
            wx.Font(
                10,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        hsizer_pic_info.Add(self.meerk40t_about_text_header, 1, wx.EXPAND, 0)
        vsizer_main.Add(hsizer_pic_info, 1, wx.EXPAND, 0)
        # Simplify addition of future developers without need to translate every single time
        # Ordered by the amount of commits (as of Jan 2024)
        # tatarize ~ 11.800
        # jpirnay ~ 3.200
        # Sophist-UK ~ 500
        # tiger12506 ~ 90
        # joerlane ~ 50
        # jaredly ~ 15
        # frogmaster ~ 10
        hall_of_fame = [
            "jpirnay",
            "Sophist-UK",
            "tiger12506",
            "jaredly",
            "frogmaster",
            "inspectionsbybob",
        ]
        meerk40t_about_text = wx.StaticText(
            self,
            wx.ID_ANY,
            _("Thanks go out to...\n")
            + _("* Li Huiyu for their controller.\n")
            + _("* Scorch for lighting our path.\n")
            + _(
                "* Alois Zingl for his brilliant Bresenham curve plotting algorithms.\n"
            )
            + "\n"
            + _(
                "* @joerlane for his hardware investigation wizardry into how the M2-Nano works.\n"
            )
            + _("* All the MeerKittens, {developer}. \n").format(
                developer=", ".join(hall_of_fame)
            )
            + _(
                "* Beta testers and anyone who reported issues that helped us improve things.\n"
            )
            + _(
                "* Translators who helped internationalise MeerK40t for worldwide use.\n"
            )
            + _(
                "* Users who have added to or edited the Wiki documentation to help other users.\n"
            )
            + "\n"
            + _(
                "* Icons8 (https://icons8.com/) for their great icons used throughout the project.\n"
            )
            + _(
                "* The countless developers who created other software that we use internally.\n"
            )
            + _("* Regebro for his svg.path module which inspired svgelements.\n")
            + _("* The SVG Working Group.\n")
            + _("* Hackers and tinkerers."),
        )
        meerk40t_about_text.SetFont(
            wx.Font(
                10,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        vsizer_main.Add(meerk40t_about_text, 4, wx.EXPAND, 0)
        self.SetSizer(vsizer_main)
        self.Layout()
        # end wxGlade


class InformationPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.mk_version = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.config_path = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.os_version = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        self.os_version.SetMinSize(wx.Size(-1, 5 * 25))
        self.info_btn = wxButton(self, wx.ID_ANY, _("Copy to Clipboard"))
        self.Bind(wx.EVT_BUTTON, self.copy_debug_info, self.info_btn)
        self.update_btn = wxButton(self, wx.ID_ANY, _("Check for Updates"))
        self.Bind(wx.EVT_BUTTON, self.check_for_updates, self.update_btn)
        self.__set_properties()
        self.__do_layout()
        self.SetupScrolling()

    def __set_properties(self):
        # Fill the content...
        import os
        import platform
        import socket

        uname = platform.uname()
        info = ""
        info += f"System: {uname.system}" + "\n"
        info += f"Node Name: {uname.node}" + "\n"
        info += f"Release: {uname.release}" + "\n"
        info += f"Version: {uname.version}" + "\n"
        info += f"Machine: {uname.machine}" + "\n"
        info += f"Processor: {uname.processor}" + "\n"
        info += f"Theme: {self.context.themes.theme}, Darkmode: {self.context.themes.dark}\n"
        try:
            info += f"Ip-Address: {socket.gethostbyname(socket.gethostname())}"
        except socket.gaierror:
            info += "Ip-Address: localhost"
        self.os_version.SetValue(info)

        info = f"{APPLICATION_NAME} v{APPLICATION_VERSION}"
        self.mk_version.SetValue(info)
        info = os.path.dirname(self.context.elements.op_data._config_file)
        # info = self.context.kernel.current_directory
        self.config_path.SetValue(info)

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_mk = StaticBoxSizer(self, wx.ID_ANY, "MeerK40t", wx.HORIZONTAL)
        sizer_mk.Add(self.mk_version, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_mk, 0, wx.EXPAND, 0)

        sizer_cfg = StaticBoxSizer(
            self, wx.ID_ANY, _("Configuration-Path"), wx.HORIZONTAL
        )
        sizer_cfg.Add(self.config_path, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_cfg, 0, wx.EXPAND, 0)

        sizer_os = StaticBoxSizer(self, wx.ID_ANY, "OS", wx.HORIZONTAL)
        sizer_os.Add(self.os_version, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_os, 1, wx.EXPAND, 0)  # This one may grow

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.info_btn, 2, wx.EXPAND, 0)
        button_sizer.Add(self.update_btn, 1, wx.EXPAND, 0)
        sizer_main.Add(button_sizer, 0, wx.EXPAND, 0)

        sizer_main.Layout()
        self.SetSizer(sizer_main)

    def check_for_updates(self, event):
        self.context.setting(str, "last_update_check", None)
        now = datetime.date.today()
        if self.context.update_check == 2:
            command = "check_for_updates --beta --verbosity 3\n"
        else:
            command = "check_for_updates --verbosity 3\n"
        self.context(command)
        self.context.last_update_check = now.toordinal()

    def copy_debug_info(self, event):
        if wx.TheClipboard.Open():
            msg = ""
            msg += self.mk_version.GetValue() + "\n"
            msg += self.py_version.GetValue() + "\n"
            msg += self.wx_version.GetValue() + "\n"
            msg += self.config_path.GetValue() + "\n"
            msg += self.os_version.GetValue() + "\n"
            # print (msg)
            wx.TheClipboard.SetData(wx.TextDataObject(msg))
            wx.TheClipboard.Close()
        else:
            # print ("couldn't access clipboard")
            wx.Bell()


class ComponentPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.list_preview = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.info_btn = wxButton(self, wx.ID_ANY, _("Copy to Clipboard"))
        self.Bind(wx.EVT_BUTTON, self.copy_debug_info, self.info_btn)
        self.content = list()
        self.get_components()
        self.__set_properties()
        self.__do_layout()
        self.SetupScrolling()

    def __set_properties(self):
        self.list_preview.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=55)
        self.list_preview.AppendColumn(
            _("Component"), format=wx.LIST_FORMAT_LEFT, width=100
        )
        self.list_preview.AppendColumn(
            _("Version"), format=wx.LIST_FORMAT_LEFT, width=120
        )
        self.list_preview.AppendColumn(
            _("Status"), format=wx.LIST_FORMAT_LEFT, width=120
        )
        self.list_preview.AppendColumn(
            _("Source"), format=wx.LIST_FORMAT_LEFT, width=200
        )
        for idx, entry in enumerate(self.content):
            list_id = self.list_preview.InsertItem(
                self.list_preview.GetItemCount(), f"#{idx + 1}"
            )
            self.list_preview.SetItem(list_id, 1, entry[0])
            self.list_preview.SetItem(list_id, 2, entry[1])
            self.list_preview.SetItem(list_id, 3, entry[2])
            self.list_preview.SetItem(list_id, 4, entry[3])

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.list_preview, 1, wx.EXPAND, 0)
        sizer_main.Add(self.info_btn, 0, 0, 0)
        sizer_main.Layout()
        self.SetSizer(sizer_main)

    def get_components(self):
        def get_python():
            import platform

            entry = [
                "Python",
                platform.python_version(),
                _("Present"),
                "https://www.python.org",
            ]
            self.content.append(entry)

        def get_wxp():
            entry = ["wxPython", "", "", "https://www.wxpython.org"]
            info = "??"
            status = _("Old")
            try:
                info = wx.version()
                status = _("Present")
            except:
                pass
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_numpy():
            entry = ["numpy", "", "", "https://numpy.org/"]
            try:
                import numpy as np

                try:
                    info = np.version.short_version
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_pillow():
            entry = ["pillow", "", "", "https://pillow.readthedocs.io/en/stable/"]
            try:
                import PIL

                try:
                    info = PIL.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_potrace():
            entry = ["potracer", "", "", "https://pypi.org/project/potracer/"]
            try:
                import potrace

                if hasattr(potrace, "potracelib_version"):
                    status = _("Present (fast)")
                    entry[0] = "pypotrace"
                    entry[3] = "https://pypi.org/project/pypotrace/"
                    info = potrace.potracelib_version()
                else:
                    status = _("Present (slow)")
                    info = "??"
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_ezdxf():
            entry = ["ezdxf", "", "", "https://ezdxf.readthedocs.io/en/stable/"]
            try:
                import ezdxf

                try:
                    info = ezdxf.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_pyusb():
            entry = ["pyusb", "", "", "https://pypi.org/project/pyusb/"]
            try:
                import usb

                try:
                    info = usb.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_pyserial():
            entry = ["pyserial", "", "", "https://pypi.org/project/pyserial/"]
            try:
                import serial

                try:
                    info = serial.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_opencv():
            entry = ["opencv", "", "", "https://opencv.org/"]
            try:
                import cv2

                try:
                    info = cv2.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_barcode():
            entry = [
                "barcode-plugin",
                "",
                "",
                "https://pypi.org/project/meerk40t-barcodes/",
            ]
            has_barcodes = False
            try:
                import barcodes as mk

                has_barcodes = True
                if hasattr(mk, "version"):
                    info = mk.version
                elif hasattr(mk, "__version__"):
                    info = mk.__version__
                else:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)
            if has_barcodes:
                try:
                    import qrcode

                    info = "??"
                    try:
                        info = qrcode.__version__
                    except AttributeError:
                        pass
                    entry = (
                        "qrcode",
                        info,
                        _("Present"),
                        "https://github.com/lincolnloop/python-qrcode",
                    )
                    self.content.append(entry)
                except ImportError:
                    pass
                try:
                    import barcode

                    info = "??"
                    try:
                        info = barcode.version
                    except AttributeError:
                        pass
                    entry = (
                        "barcodes",
                        info,
                        _("Present"),
                        "https://github.com/WhyNotHugo/python-barcode",
                    )
                    self.content.append(entry)
                except ImportError:
                    pass

        def get_clipper():
            entry = ["clipper", "", "", "https://pypi.org/project/pyclipr/"]
            try:
                import pyclipr

                try:
                    info = pyclipr.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_numba():
            entry = ["numba", "", "", "https://numba.pydata.org/"]
            try:
                import numba

                try:
                    info = numba.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        self.content.clear()
        get_python()
        get_wxp()
        get_numpy()
        get_pillow()
        get_potrace()
        get_ezdxf()
        get_pyusb()
        get_pyserial()
        get_opencv()
        get_barcode()
        get_clipper()
        get_numba()

    def copy_debug_info(self, event):
        if wx.TheClipboard.Open():
            msg = ""
            for entry in self.content:
                msg += f"{entry[0]}: {entry[1]}, {entry[2]} \n"
            # print (msg)
            wx.TheClipboard.SetData(wx.TextDataObject(msg))
            wx.TheClipboard.Close()
        else:
            # print ("couldn't access clipboard")
            wx.Bell()


class About(MWindow):
    def __init__(self, *args, **kwds):
        from platform import system as _sys

        super().__init__(
            480,
            360,
            *args,
            style=wx.CAPTION
            | wx.CLOSE_BOX
            | wx.FRAME_FLOAT_ON_PARENT
            | wx.TAB_TRAVERSAL
            | (wx.RESIZE_BORDER if _sys() != "Darwin" else 0),
            **kwds,
        )
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)

        self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)
        self.panel_info = InformationPanel(self, wx.ID_ANY, context=self.context)
        self.panel_component = ComponentPanel(self, wx.ID_ANY, context=self.context)
        self.notebook_main.AddPage(self.panel_about, _("About"))
        self.notebook_main.AddPage(self.panel_info, _("System-Information"))
        self.notebook_main.AddPage(self.panel_component, _("MeerK40t-Components"))

        self.add_module_delegate(self.panel_about)
        self.add_module_delegate(self.panel_info)
        self.add_module_delegate(self.panel_component)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_about.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("About"))

        name = self.context.kernel.name
        version = self.context.kernel.version
        self.SetTitle(_("About {name} v{version}").format(name=name, version=version))
        self.restore_aspect()

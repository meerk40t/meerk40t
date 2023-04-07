import wx

from ..main import APPLICATION_NAME, APPLICATION_VERSION
from .icons import icon_meerk40t, icons8_about_50
from .mwindow import MWindow
from .wxutils import StaticBoxSizer

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
        hall_of_fame = [
            "Sophist-UK",
            "tiger12506",
            "jpirnay",
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


class InformationPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.mk_version = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.py_version = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.wx_version = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.config_path = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.os_version = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        self.info_btn = wx.Button(self, wx.ID_ANY, _("Copy to Clipboard"))
        self.Bind(wx.EVT_BUTTON, self.copy_debug_info, self.info_btn)
        self.update_btn = wx.Button(self, wx.ID_ANY, _("Check for Updates"))
        self.Bind(wx.EVT_BUTTON, self.check_for_updates, self.update_btn)
        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        # Fill the content...
        import os
        import platform
        import socket
        import sys

        info = "wx"
        try:
            info = wx.version()
        except:
            pass
        self.wx_version.SetValue(info)
        self.py_version.SetValue(platform.python_version())
        uname = platform.uname()
        info = ""
        info += f"System: {uname.system}" + "\n"
        info += f"Node Name: {uname.node}" + "\n"
        info += f"Release: {uname.release}" + "\n"
        info += f"Version: {uname.version}" + "\n"
        info += f"Machine: {uname.machine}" + "\n"
        info += f"Processor: {uname.processor}" + "\n"
        try:
            info += f"Ip-Address: {socket.gethostbyname(socket.gethostname())}"
        except socket.gaierror:
            info += "Ip-Address: localhost"
        self.os_version.SetValue(info)

        info = f"{APPLICATION_NAME} v{APPLICATION_VERSION}"
        # Development-Version ?
        git = branch = False
        if " " in APPLICATION_VERSION:
            ver, exec_type = APPLICATION_VERSION.rsplit(" ", 1)
            git = exec_type == "git"

        if git:
            head_file = os.path.join(sys.path[0], ".git", "HEAD")
            if os.path.isfile(head_file):
                ref_prefix = "ref: refs/heads/"
                ref = ""
                try:
                    with open(head_file) as f:
                        ref = f.readline()
                except Exception:
                    pass
                if ref.startswith(ref_prefix):
                    branch = ref[len(ref_prefix) :].strip("\n")

        if git and branch and branch not in ("main", "legacy6", "legacy7"):
            info = info + " - " + branch
        self.mk_version.SetValue(info)
        info = os.path.dirname(self.context.elements.op_data._config_file)
        # info = self.context.kernel.current_directory
        self.config_path.SetValue(info)

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_mk = StaticBoxSizer(self, wx.ID_ANY, "MeerK40t", wx.HORIZONTAL)
        sizer_mk.Add(self.mk_version, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_mk, 0, wx.EXPAND, 0)

        sizer_py = StaticBoxSizer(self, wx.ID_ANY, "Python", wx.HORIZONTAL)
        sizer_py.Add(self.py_version, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_py, 0, wx.EXPAND, 0)

        sizer_wx = StaticBoxSizer(self, wx.ID_ANY, "wxPython", wx.HORIZONTAL)
        sizer_wx.Add(self.wx_version, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_wx, 0, wx.EXPAND, 0)

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
        self.context("check_for_updates -popup\n")

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

        self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)
        self.panel_info = InformationPanel(self, wx.ID_ANY, context=self.context)
        self.notebook_main.AddPage(self.panel_about, _("About"))
        self.notebook_main.AddPage(self.panel_info, _("System-Information"))

        self.add_module_delegate(self.panel_about)
        self.add_module_delegate(self.panel_info)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_about_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("About"))

        name = self.context.kernel.name
        version = self.context.kernel.version
        self.SetTitle(_("About {name} v{version}").format(name=name, version=version))

"""
    A simple module to display some startup tips.
    You can add more tips, every tip has two elements:
        a) the info-text to display in the panel
        b) an (optional) command to be executed in the 'Try it out' button
"""
import datetime
import os
import wx
from wx import aui

from ..kernel import get_safe_path
from .icons import (
    icons8_circled_left,
    icons8_circled_right,
    icons8_detective,
)
from .wxutils import dip_size

_ = wx.GetTranslation


def register_panel_tips(window, context):
    panel = TipPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Float()
        .MinSize(80, 125)
        .FloatingSize(120, 145)
        .Hide()
        .Caption(_("Tips"))
        .CaptionVisible(not context.pane_lock)
        .Name("tips")
    )
    pane.dock_proportion = 150
    pane.control = panel
    pane.submenu = "~" + _("Help")

    window.on_pane_create(pane)
    context.register("pane/tips", pane)


class TipPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.tip_command = ""
        self.tips = list()
        self.setup_tips()
        self.context.setting(bool, "show_tips", True)
        self.SetHelpText("tips")
        icon_size = dip_size(self, 25, 25)
        # Main Sizer
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.text_tip = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY|wx.TE_MULTILINE)
        sizer_main.Add(self.text_tip, 1, wx.EXPAND, 0)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_prev = wx.Button(self, wx.ID_ANY, _("Previous tip"))
        self.button_prev.SetBitmap(
            icons8_circled_left.GetBitmap(resize=icon_size[0])
        )
        self.button_next = wx.Button(self, wx.ID_ANY, _("Next tip"))
        self.button_next.SetBitmap(
            icons8_circled_right.GetBitmap(resize=icon_size[0])
        )
        button_sizer.Add(self.button_prev, 0, wx.ALIGN_CENTER_VERTICAL)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(self.button_next, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_main.Add(button_sizer, 0, wx.EXPAND, 0)

        self.check_startup = wx.CheckBox(self, wx.ID_ANY, _("Show tips at startup"))
        self.check_startup.SetToolTip(_("Show tips at program start"))
        self.check_startup.SetValue(self.context.show_tips)

        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_try = wx.Button(self, wx.ID_ANY, _("Try it out"))
        self.button_try.SetBitmap(
            icons8_detective.GetBitmap(resize=icon_size[0])
        )
        option_sizer.Add(self.button_try, 0, wx.ALIGN_CENTER_VERTICAL)
        option_sizer.AddStretchSpacer()
        option_sizer.Add(self.check_startup, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(option_sizer, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.check_startup.Bind(wx.EVT_CHECKBOX, self.on_check_startup)
        self.button_prev.Bind(wx.EVT_BUTTON, self.on_tip_prev)
        self.button_next.Bind(wx.EVT_BUTTON, self.on_tip_next)
        self.button_try.Bind(wx.EVT_BUTTON, self.on_button_try)

        self.context.setting(int, "next_tip", 0)
        self.current_tip = self.context.next_tip

    @property
    def current_tip(self):
        return self._current_tip

    @current_tip.setter
    def current_tip(self, newvalue):
        if newvalue < 0:
            newvalue = len(self.tips) - 1
        if newvalue >= len(self.tips):
            newvalue = 0
        self._current_tip = newvalue
        # Store it for the next session
        self.context.next_tip = newvalue + 1
        my_tip = self.tips[self._current_tip]
        self.text_tip.SetValue(my_tip[0])
        if my_tip[1]:
            self.button_try.Show(True)
            self.tip_command = my_tip[1]
        else:
            self.button_try.Show(False)
            self.tip_command = ""
        self.Layout()

    def on_button_try(self, event):
        if self.tip_command:
            self.context(f"{self.tip_command}\n")

    def on_check_startup(self, event):
        state = self.check_startup.GetValue()
        self.context.show_tips = state

    def on_tip_prev(self, event):
        self.current_tip -= 1

    def on_tip_next(self, event):
        self.current_tip += 1

    def setup_tips(self):
        self.tips.append(
            (
                _(
                    "Do you want to get extended information about a feature in MeerK40t?\n"
                    + "Just place your mouse over a window or a an UI-element and press F11."
                ),
                "",
            )
        )
        self.tips.append(
            (
                _(
                    "MeerK40t supports more than 'just' a K40 laser.\n"
                    + "You can add more devices in the Device-Manager.\n"
                    + "And you can even add multiple instances for the same physical device,\n"
                    + "where you can different configuration settings (eg regular and rotary)."
                ),
                "window open DeviceManager",
            ),
        )
        self.tips.append(
            (
                _(
                    "MeerK40ts standard to load / save data is the svg-Format (supported by many tools like inkscape).\n"
                    + "While it is supporting most of SVG functionalities, there are still some unsupported features (most notably advanced text effect, clips and gradients).\n"
                    + "To overcome that limitation MeerK40t can automatically convert these features with the help of inkscape:\n"
                    + "just set the 'Unsupported feature' option in the preference section to 'Ask at load time'"
                ),
                "window open Preferences\n",
            ),
        )
        lastdate = None
        lastcall = self.context.setting(int, "last_tip_check", None)
        doit = True
        if lastcall is not None:
            try:
                lastdate = datetime.date.fromordinal(lastcall)
            except ValueError:
                pass

        safe_dir = os.path.realpath(get_safe_path(self.context.kernel.name))
        self.local_file = os.path.join(safe_dir, "tips.txt")
        if os.path.exists(self.local_file):
            now = datetime.date.today()
            if lastdate is not None:
                delta = now - lastdate
                if delta.days < 6:
                    # Once per week is enough
                    doit = False
        if doit:
            self.load_tips_from_github()
        self.load_tips_from_local_cache()

    def load_tips_from_github(self):
        successful = False
        import requests
        content = ""
        url = 'https://raw.githubusercontent.com/repo/meerk40t/meerk40t/assets/tip.txt'
        try:
            page = requests.get(url)
            if page.status_code == 200: # okay
                content = page.text
                successful = True
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            pass


        if successful:
            now = datetime.date.today()
            self.context.last_tip_check = now.toordinal()
            # Store the result to the local cache file
            if len(content):
                try:
                    with open(self.local_file, mode="w") as f:
                        f.write(content)
                except (OSError, RuntimeError, PermissionError, FileNotFoundError):
                    pass

    def load_tips_from_local_cache(self):

        def comparable_version(version):
            """
            Return a comparable sequence from a version string
            """
            ending = ""
            result = list()
            if version is not None:
                if version.startswith("v"):
                    version = version[1:]
                if " " in version:
                    version, ending = version.split(" ", 1)
                result = list(map(int, version.split(".")))
                if len(result) > 3:
                    result = result[0:2]
            while len(result) < 3:
                result.append(0)
            # print (f"Looking at {orgversion}: {result}")
            return result


        def add_tip(tip, cmd, version, current_version):
            if version:
                minimal_version = comparable_version(version)
                # print (f"comparing {current_version} to {minimal_version}")
                if current_version < minimal_version:
                    tip = ""
            if tip:
                # Replace '\n' with real line breaks
                tip = tip.replace( r"\n", "\n")
                if cmd:
                    cmd = cmd.replace( r"\n", "\n")
                self.tips.append(
                    (tip, cmd)
                )

        myversion = comparable_version(self.context.kernel.version)

        try:
            with open(self.local_file, mode="r") as f:
                ver = ""
                tip = ""
                cmd = ""
                for line in f:
                    cline = line.strip()
                    if cline.startswith("#") or len(cline) == 0:
                        continue
                    if cline.startswith("["):
                        add_tip(tip, cmd, ver, myversion)
                        ver = ""
                        tip = ""
                        cmd = ""
                    elif cline.startswith("tip="):
                        tip = cline[len("tip="):]
                    elif cline.startswith("version="):
                        ver = cline[len("version="):]
                    elif cline.startswith("cmd="):
                        cmd = cline[len("cmd="):]
                # Something pending?
                add_tip(tip, cmd, ver, myversion)


        except (OSError, RuntimeError, PermissionError, FileNotFoundError):
            return


    def pane_show(self, *args):
        pass

    def pane_hide(self, *args):
        pass

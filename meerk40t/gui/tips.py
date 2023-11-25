"""
    A simple module to display some startup tips.
    You can add more tips, every tip has three elements:
        a) the info-text to display in the panel
        b) an (optional) command to be executed in the 'Try it out' button
        c) an (optional) image (url) to be shown
"""
import os
import urllib
import webbrowser

import wx

from ..kernel import get_safe_path
from .icons import (
    icon_outline,
    icon_youtube,
    icons8_circled_left,
    icons8_circled_right,
    icons8_console,
    icons8_detective,
    icons8_light_on,
)
from .mwindow import MWindow
from .wxutils import dip_size

_ = wx.GetTranslation


class TipPanel(wx.Panel):
    """
    Display MeerK40t usage tips
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PositionPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.tip_command = ""
        self.tip_image = ""
        self.tips = list()

        safe_dir = os.path.realpath(get_safe_path(self.context.kernel.name))
        self.local_file = os.path.join(safe_dir, "tips.txt")

        self.setup_tips()
        self.context.setting(bool, "show_tips", True)
        # Has the user already agreed to download an image automatically
        # if it can't be found? Defaults to False - please note that the
        # consent will be set to False by default
        self.context.setting(bool, "tip_access_consent", False)
        # Reset for debug purposes
        # self.context.tip_access_consent = False
        self.SetHelpText("tips")
        icon_size = dip_size(self, 25, 25)
        # Main Sizer
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.image_tip = wx.StaticBitmap(self, wx.ID_ANY, style=wx.SB_FLAT)
        self.image_tip.SetMinSize(wx.Size(250, -1))
        self.check_consent = wx.CheckBox(
            self, wx.ID_ANY, _("Image missing!\nRetrieve automatically?")
        )
        self.check_consent.SetToolTip(
            _(
                "Couldn't find the cached image for this tip!\nShall MeerK40t try to download such missing images from the internet?"
            )
        )
        self.check_consent.SetValue(self.context.tip_access_consent)
        self.check_consent.Show(False)
        # self.image_tip.SetMaxSize(wx.Size(250, -1))
        # self.image_tip.SetSize(wx.Size(250, -1))
        self.text_tip = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        tip_area = wx.BoxSizer(wx.HORIZONTAL)
        tip_area.Add(self.check_consent, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        tip_area.Add(self.image_tip, 1, wx.EXPAND, 0)
        tip_area.Add(self.text_tip, 3, wx.EXPAND, 0)

        sizer_main.Add(tip_area, 1, wx.EXPAND, 0)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_prev = wx.Button(self, wx.ID_ANY, _("Previous tip"))
        self.button_prev.SetBitmap(icons8_circled_left.GetBitmap(resize=icon_size[0]))
        self.button_prev.SetToolTip(_("Jump back to the previously displayed tip"))

        self.button_next = wx.Button(self, wx.ID_ANY, _("Next tip"))
        self.button_next.SetBitmap(icons8_circled_right.GetBitmap(resize=icon_size[0]))
        self.button_next.SetToolTip(_("Jump to the previously displayed tip"))

        button_sizer.Add(self.button_prev, 0, wx.ALIGN_CENTER_VERTICAL)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(self.button_next, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_main.Add(button_sizer, 0, wx.EXPAND, 0)

        self.check_startup = wx.CheckBox(self, wx.ID_ANY, _("Show tips at startup"))
        self.check_startup.SetToolTip(
            _(
                "Show tips at program start.\n"
                + "Even if disabled, 'Tips & Tricks' are always available in the Help-menu."
            )
        )
        self.check_startup.SetValue(self.context.show_tips)

        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_try = wx.Button(self, wx.ID_ANY, _("Try it out"))
        self.button_try.SetToolTip(
            _(
                "Launch an example, please be aware that this might change your design,\n"
                + "as new elements could be created to show the functionality"
            )
        )
        self.button_try.SetBitmap(icons8_detective.GetBitmap(resize=icon_size[0]))
        self.button_update = wx.Button(self, wx.ID_ANY, _("Update"))
        self.button_update.SetFont(
            wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        self.button_update.SetToolTip(
            _(
                "Look for new tips on MeerK40ts website.\n"
                + "The list of tips is constantly expanded, so please update it\n"
                + "every now and then to learn about new or hidden features."
            )
        )
        option_sizer.Add(self.button_try, 0, wx.ALIGN_CENTER_VERTICAL)
        option_sizer.AddStretchSpacer()
        option_sizer.Add(self.button_update, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        option_sizer.Add(self.check_startup, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(option_sizer, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.check_consent.Bind(wx.EVT_CHECKBOX, self.on_check_consent)
        self.check_startup.Bind(wx.EVT_CHECKBOX, self.on_check_startup)
        self.button_prev.Bind(wx.EVT_BUTTON, self.on_tip_prev)
        self.button_next.Bind(wx.EVT_BUTTON, self.on_tip_next)
        self.button_try.Bind(wx.EVT_BUTTON, self.on_button_try)
        self.button_update.Bind(wx.EVT_BUTTON, self.on_button_update)

        self.cache_dir = self.establish_picture_cache()
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
        if my_tip[2]:
            self.set_tip_image(my_tip[2], newvalue, self.context.tip_access_consent)
        else:
            self.set_tip_image("", newvalue, self.context.tip_access_consent)
        self.Layout()

    def set_tip_image(self, path, counter, automatic_download, display=True):
        """
        path: URL of the image to be loaded
        counter: an additional naming element to
        avoid ending up with the same name for equally called images
        display: apply and display the image
        """
        self.tip_image = path
        if isinstance(path, wx.Bitmap):
            if display:
                self.image_tip.SetBitmap(path)
                self.image_tip.Show(True)
        else:
            found = False
            if path and self.cache_dir:
                # Hex-string of path-hash
                basename = f"{hash(path):#x}"
                local_path = os.path.join(self.cache_dir, basename)
                # Is this file already on the disk? If not load it...
                if not os.path.exists(local_path):
                    if automatic_download:
                        loaded = False
                        opened = False
                        try:
                            with urllib.request.urlopen(path) as file:
                                content = file.read()
                                opened = True
                        except (urllib.error.URLError, urllib.error.HTTPError) as e:
                            # print (f"Error: {e}")
                            pass
                        # If the file object is successfully opened, read its content as a string
                        if opened:
                            try:
                                with open(local_path, "wb") as f:
                                    f.write(content)
                                    loaded = True
                            except (OSError, PermissionError, RuntimeError) as e:
                                # print (f"Error @ image write to {local_path}: {e}")
                                pass

                        found = loaded
                    else:
                        self.check_consent.Show(True)

                if display and local_path and os.path.exists(local_path):
                    bmp = wx.Bitmap()
                    res = bmp.LoadFile(local_path)
                    if res:
                        new_x, new_y = bmp.Size
                        img_size = self.image_tip.GetSize()
                        if new_x > img_size[0] or new_y > img_size[1]:
                            if new_x > img_size[0]:
                                fact = img_size[0] / new_x
                                new_y *= fact
                                new_x *= fact
                            if new_y > img_size[1]:
                                fact = img_size[1] / new_y
                                new_y *= fact
                                new_x *= fact
                            image = bmp.ConvertToImage()
                            image.Rescale(int(new_x), int(new_y))
                            bmp = wx.Bitmap(image)

                        try:
                            self.image_tip.SetScaleMode(wx.StaticBitmap.Scale_None)
                        except AttributeError:
                            # Old version of wxpython
                            pass
                        self.image_tip.SetBitmap(bmp)
                        found = True
            if display:
                if found:
                    self.image_tip.Show(True)
                else:
                    self.image_tip.Show(False)

    def on_button_try(self, event):
        if self.tip_command:
            if self.tip_command.startswith("http"):
                webbrowser.open(self.tip_command, new=0, autoraise=True)
            else:
                self.context(f"{self.tip_command}\n")

    def on_check_consent(self, event):
        state = self.check_consent.GetValue()
        self.context.tip_access_consent = state
        # Hide me again...
        self.check_consent.Show(False)
        # Force refresh
        self.current_tip = self.current_tip

    def on_check_startup(self, event):
        state = self.check_startup.GetValue()
        self.context.show_tips = state

    def on_tip_prev(self, event):
        self.current_tip -= 1

    def on_tip_next(self, event):
        self.current_tip += 1

    def setup_tips(self):
        self.tips.clear()
        # This initial list of tips does contain only very basic and very limited tips
        # and very intentional does not have any image resources from the web.
        # The user has the opportunity to download more and more sophisticated tips
        # by clicking the update button.
        self.tips.append(
            (
                _(
                    "Do you want to get extended information about a feature in MeerK40t?\n"
                    + "Just place your mouse over a window or an UI-element and press F11."
                ),
                "",
                "",
            )
        )
        self.tips.append(
            (
                _(
                    "MeerK40t supports more than 'just' a K40 laser.\n"
                    + "You can add more devices in the Device-Manager.\n"
                    + "And you can even add multiple instances for the same physical device,\n"
                    + "where you can have different configuration settings (eg regular and rotary)."
                ),
                "window open DeviceManager",
                "",
            ),
        )
        self.tips.append(
            (
                _(
                    "There are a couple of YouTube-videos that deal with some specific functionalities and explain their usage:\n"
                    + "https://www.youtube.com/channel/UCsAUV23O2FyKxC0HN7nkAQQ"
                ),
                "https://www.youtube.com/channel/UCsAUV23O2FyKxC0HN7nkAQQ",
                icon_youtube.GetBitmap(resize=200),
            )
        )
        self.tips.append(
            (
                _(
                    "More instructional videos? Sure, here is another channel:\n\n"
                    + "https://www.youtube.com/channel/UCMN9gGvpacxZINPZCSOecaQ"
                ),
                "https://www.youtube.com/channel/UCMN9gGvpacxZINPZCSOecaQ",
                icon_youtube.GetBitmap(resize=200),
            )
        )
        self.tips.append(
            (
                _(
                    "MeerK40t can create a so called outline around an element.\nJust select the element, right click on top of it to get the context menu and choose from the 'Outline elements' menu..."
                ),
                "rect 2cm 2cm 4cm 4cm fill black outline 2mm --steps 4 --outer stroke red",
                icon_outline.GetBitmap(resize=200),
            ),
        )
        self.tips.append(
            (
                _(
                    "MeerK40t has an extensive set of commands that allow a lot of scriptable actions.\nJust open the console window and type 'help'"
                ),
                "pane show console\nhelp",
                icons8_console.GetBitmap(resize=200),
            ),
        )
        self.tips.append(
            (
                _(
                    "Do you want to see more Tips & Tricks?\n"
                    + "Just click on the 'Update'-button to load additional hints from MeerK40ts website.\n"
                    + "The list of tips is constantly expanded, so please update it every now and then to learn about new or hidden features."
                ),
                "",
                icons8_light_on.GetBitmap(resize=200),
            ),
        )

        self.load_tips_from_local_cache()

    def on_button_update(self, event):
        prev_count = len(self.tips)
        self.load_tips_from_github()
        self.setup_tips()
        # Load all images...
        for idx, tip in enumerate(self.tips):
            if tip[2]:
                # As we are accessing the internet deliberately, we will download the pictures too
                self.set_tip_image(tip[2], idx, True, display=False)
        new_count = len(self.tips)
        res = wx.MessageBox(
            message=_("Tips have been updated, {info} new entries found.").format(
                info=str(new_count - prev_count)
            ),
            caption=_("Tips"),
        )
        # Force update...
        self.current_tip = self.current_tip

    def load_tips_from_github(self):
        successful = False

        content = ""
        url = "https://github.com/meerk40t/meerk40t/raw/main/locale/"
        # Do we have a localized version?
        locale = "en"
        languages = list(self.context.app.supported_languages)
        try:
            locale = languages[self.context.language][0]
        except IndexError:
            pass
        # print(self.context.language, locale, languages)
        if locale and locale != "en":
            try:
                with urllib.request.urlopen(url + locale + "/tips.txt") as file:
                    content = file.read().decode("utf-8")
                    successful = True
            except (urllib.error.URLError, urllib.error.HTTPError):
                pass

        # if we don't have anything localized then let's use the english master
        if not successful:
            try:
                with urllib.request.urlopen(url + "tips.txt") as file:
                    content = file.read().decode("utf-8")
                    successful = True
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                # print (f"Error: {e}")
                pass

        if successful:
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
            return result

        def add_tip(tip, cmd, img, version, current_version):
            if version:
                minimal_version = comparable_version(version)
                # print (f"comparing {current_version} to {minimal_version}")
                if current_version < minimal_version:
                    tip = ""
            if tip:
                # Replace '\n' with real line breaks
                tip = tip.replace(r"\n", "\n")
                if cmd:
                    cmd = cmd.replace(r"\n", "\n")
                self.tips.append((tip, cmd, img))

        myversion = comparable_version(self.context.kernel.version)

        try:
            with open(self.local_file, mode="r") as f:
                ver = ""
                tip = ""
                cmd = ""
                img = ""
                lastline_was_tip = False
                for line in f:
                    cline = line.strip()
                    if cline.startswith("#") or len(cline) == 0:
                        continue
                    if cline.startswith("tip="):
                        lastline_was_tip = True
                        # Store previous
                        add_tip(tip, cmd, img, ver, myversion)
                        ver = ""
                        tip = ""
                        cmd = ""
                        img = ""
                        tip = cline[len("tip=") :]
                    elif cline.startswith("version="):
                        lastline_was_tip = False
                        ver = cline[len("version=") :]
                    elif cline.startswith("cmd="):
                        lastline_was_tip = False
                        cmd = cline[len("cmd=") :]
                    elif cline.startswith("image="):
                        lastline_was_tip = False
                        img = cline[len("image=") :]
                    elif cline.startswith("img="):
                        lastline_was_tip = False
                        img = cline[len("img=") :]
                    else:
                        if lastline_was_tip:
                            tip += "\n" + cline

                # Something pending?
                add_tip(tip, cmd, img, ver, myversion)

        except (OSError, RuntimeError, PermissionError, FileNotFoundError):
            return

    def establish_picture_cache(self):
        """
        Check for existence of a subdirectory to store images
        and create it if not found
        """
        safe_dir = os.path.realpath(get_safe_path(self.context.kernel.name))
        cache_dir = os.path.join(safe_dir, "tip_images")
        if not os.path.exists(cache_dir):
            try:
                os.mkdir(cache_dir)
            except (OSError, PermissionError, RuntimeError):
                cache_dir = ""
        return cache_dir

    def pane_show(self, *args):
        pass

    def pane_hide(self, *args):
        pass


class Tips(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(400, 350, *args, **kwds)
        self.panel = TipPanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_detective.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Tips"))

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    def delegates(self):
        yield self.panel

    @staticmethod
    def submenu():
        # Suppress...
        return "Tips", "Tips", True

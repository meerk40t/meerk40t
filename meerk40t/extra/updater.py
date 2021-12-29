from typing import Optional, Any, Union
from typing import Callable, Dict, List, Tuple

import datetime
from functools import partial
import json
from ..kernel import Modifier, Context, Channel, Kernel
import os
import platform
from random import choice
import sys
from textwrap import wrap
from urllib.request import Request, urlopen, urlretrieve
from urllib.error import
try:
    import wx
    GUI_ENABLED = True
except ImportError:
    GUI_ENABLED = False

UPDATER_CONTEXT = "updater"
UPDATER_PATH = "modifier/Updater"
ENUM_DOWNLOAD_NO = 1
ENUM_DOWNLOAD_BROWSER = 2
ENUM_DOWNLOAD_MK = 3


def plugin(kernel: Kernel, lifecycle: Optional[str]=None) -> None:
    if lifecycle == "console":
        GUI_ENABLED = False
    elif lifecycle == "register":
        kernel.register(UPDATER_PATH, Updater)
    elif lifecycle == "boot":
        context = kernel.get_context(UPDATER_CONTEXT)
        context.activate(UPDATER_PATH)
    elif lifecycle == "finished":
        context = kernel.get_context(UPDATER_CONTEXT)
        instance = context.attached[UPDATER_PATH]
        instance.startup()

def UpdateMessageDialog(msg: str, caption: str='', style: int=wx.OK | wx.CENTRE) -> wx.Dialog:
    """
    Improves the wx message dialog box by separating out the first paragraph
    as main message (shown in bold) and the rest as an extended message
    """
    if "\n\n" in msg:
        msg, ext_msg = msg.split("\n\n", 1)
        ext_msg = ext_msg.strip("\n")
    else:
        ext_msg = ""
    dlg = wx.UpdateMessageDialog(
        None,
        msg,
        caption=caption,
        style=style
    )
    if ext_msg:
        dlg.SetExtendedMessage(ext_msg)
    return dlg


class UpdaterWebError(Exception):
    """
    Plugin specific exception used to flag some sort of WebError
    """
    pass


class GHRelease:
    """
    Used to hold details of a release
    * Currently executing release
    * Full or beta update releases plus Github API Response plus calculated values
    """
    def __init__(self, _: Callable[[str], str], tag: str="", response: Union[Dict, List[Dict]]=None) -> None:
        self._ = _
        self.tag = tag.strip()
        if " " in self.tag:
            self.tag, src = self.tag.split(" ", 1)
        if self.tag == "" and response is not None and "tag_name" in response:
            self.tag = response["tag_name"]
        self.version = self.comparable_version(self.tag)
        self.response = response
        self.asset = None
        self.update_path = None11

    @staticmethod
    def comparable_version(tag: str) -> List[int]:
        """
        Return a comparable sequence from a version string
        """
        if not tag:
            return [0, 0, 0, 0]
        tag = tag.strip()
        src = beta = ""
        if tag.startswith("v"):
            tag = tag[1:]
        if "-" in tag:
            tag, beta = tag.split("-", 1)
        if beta.startswith("beta"):
            beta = beta[4:]
        if not beta:
            beta = 9999  # indicates a full version
        else:
            beta = int(beta)
        version = tag.split(".")
        version.extend([0, 0, 0])
        version = version[:3]
        version = list(map(int,version))
        version.append(beta)
        return version

    @property
    def beta(self) -> bool:
        if self.response and "prerelease" in self.response:
            return self.response["prerelease"]
        if len(self.version) <= 3:
            return False
        return self.version[3] < 9999

    @property
    def release_type(self) -> str:
        _ = self._
        return _("beta release") if self.beta else _("full release")


class Updater(Modifier, dict):
    """
    This class provides three types of update functionality, all of which use a common set of routines:
    1.  Console command check_for_updates which simply provides
        the details and release URL for new full (or beta) updates.
        This check is also run on every start of Meerk40t in console mode.
    2.  A GUI version available from the Help menu which makes the same checks and
        (when appropriate) also offers a download button.
    3.  A periodic GUI startup update check which runs every 1 days on program start-up,
        and alerts the user of new versions since the last check and / or
        a periodic reminder every 7 days if they ignored the previous alert.

        User is considered alerted if any of the above options advises the user that an update is available.

    If a new release is identified in GUI or statup checks, the user is given the option to download,
    either using internal functionality or by launching a browser window.

    Preferences are provided for:
    a.  Turning the automated check off/on (default On)
    b.  Always checking for beta versions as well as full versions (default Off).
        User is always alerted to updated beta versions of the same minor release
        if they are already running a beta version.
    c.  Disabling the internal download and always using a browser download.

    The internal download option is used if:
    i.  Option to force browser dowload is off; and
    ii. User is running an executable; and
    iii.Directory containing the current executable is writeable.

    All web access is done in a worker thread so that main thread is not hung whilst
    waiting for web transfer to complete.

    All GUI access is done on main thread as this is a restriction of wxPython.
    """

    def __init__(self, context: Context, name: str=None, channel: Channel=None, *args, **kwargs) -> None:
        Modifier.__init__(self, context, name, channel)
        self.kernel = self.context._kernel
        self.root = self.kernel.root
        self._ = _ = self.kernel.translation

        self.release_current = GHRelease(_, self.kernel.version)

        self.debug = self.kernel.channel(UPDATER_CONTEXT, timestamp=True)
        self.executable_path = sys.path[0]
        if getattr(sys, "frozen", False):
            self.executable_type = "exe"
            self.executable_path = sys.executable
        elif os.path.isdir(sys.path[0] + "/.git"):
            self.executable_type = "git"
        elif os.path.isdir(sys.path[0] + "/.github"):
            self.executable_type = "src"
        else:
            self.executable_type = "pkg"
        self.system_type = "{os}:{arch}".format(os=platform.system(), arch=platform.machine())
        self.is_windows = platform.system() == "Windows"

        self.define_settings()
        self.define_constants()

        if self.root.updater_test:
            self.set_test_mode()

    def define_settings(self) -> None:
        root = self.root
        context = self.context

        root.setting(bool, "updater_check_automated", True)
        root.setting(bool, "updater_check_betas", False)
        root.setting(bool, "updater_download_browser", False)
        root.setting(bool, "updater_test", False)  # Set updater_test to True to run in test mode

        context.setting(str, "updater_check_timestamp", "")
        context.setting(str, "updater_check_tag_full", "")
        context.setting(str, "updater_check_tag_beta", "")
        context.setting(str, "updater_check_tag_current", "")
        context.setting(str, "updater_check_last_reminder", "")

    def define_constants(self) -> None:
        # Override the translation function to format paragraphs to a fixed length
        # so that the wx.UpdateMessageDialog doesn't size the dialog as wide as it might like.

        # Note: This might also be a useful general translation function for meerk40t
        # e.g. to format the about box and tooltips, particularly where translation strings include
        # fixed line splits that complicate the translation, however generalising this is beyond
        # the scope of the PR that introduces this function, particularly since we may also need to
        # introduce a means of specifying the reflow width for each type of translation
        # (in a way which does not prevent gettext collection of translation strings for the catalog).
        def _(text: str) -> str:
            MSGBOX_TEXT_WIDTH = 80
            # Split the translated text into separate lines, reflow each line as several lines of maximum width
            # and then combine back into a single string
            lines = self._(text).split("\n")
            for i, line in enumerate(lines):
                lines[i] = "\n".join(wrap(
                    line,
                    width=MSGBOX_TEXT_WIDTH,
                    subsequent_indent="   " if line.startswith("* ") else "",
                ))
            return "\n".join(lines)

        self["DELAY_BETWEEN_AUTOCHECKS"] = datetime.timedelta(days=2)
        self["DELAY_BETWEEN_REMINDERS"] = datetime.timedelta(days=7)
        # For autochecks, in order to have a ramp up of users in case of release issues,
        # we don't report a new release until a certain number of days have passed
        self["DAYS_AUTO_AFTER_RELEASE_FULL"] = datetime.timedelta(days=7)
        self["DAYS_AUTO_AFTER_RELEASE_BETA"] = datetime.timedelta(days=2)

        # https://docs.github.com/en/rest/reference/repos#list-releases
        # We assume that there will have been less than 20 releases to legacy branches since
        # last full and beta releases to main branch
        self["GITHUB_RELEASES"] = "https://api.github.com/repos/meerk40t/meerk40t/releases?perpage=20"
        self["HEADER_ACCEPT"] = "application/vnd.github.v3+json"
        self["HEADER_USERAGENT"] = "Meerk40t/{version}".format(version=self.release_current.tag)
        self["GITHUB_TIMESTAMP_FORMAT"] = "%Y-%m-%dT%H:%M:%SZ"

        self["WEB_ERROR_MESSAGE"] = (
            _("Check for updates: Github request for release details failed!")
            + "\n\nException: {exception}"
        )
        self["CURRENT_MESSAGE"] = _("You are already running the current {release_type} of {name}.")
        self["PRERELEASE_MESSAGE"] = _("You appear to be running a pre-release version of {name}.")
        self["UPDATE_MESSAGE"] = _(
            "A new {release_type} of {name} v{tag} is available from:"
            + "\n{url}"
        )
        self["GUI_CAPTION"] = _("Check for Update")
        self["GUI_HELP"] = _("FAQs")
        self["DEFER"] = _("Defer for {days} days")
        self["NO"] = _("&No")
        self["OK"] = _("&OK")
        self["UPDATE"] = _("&Update")
        self["DOWNLOAD_EXECUTABLE"] = _("&Download executable")
        self["DOWNLOAD_BROWSER"] = _("Download with &browser")
        download_message = _("Do you want to download this new release?")
        download_exe_yourself = _(
            "* Download the executable file using a browser, to a directory and executable name of your own choice."
        )
        self["EXE_DOWNLOAD_MESSAGE"] = (
            self["UPDATE_MESSAGE"]
            + "\n\n"
            + _(
                "You are running from an executable under windows and windows will not allow "
                + "us to replace the executable file whilst you are running {name}. "
                + "To update you can either:"
            )
            + "\n"
            + _(
                "* Download the new executable to the same directory with a unique filename containing the version number. "
                + "You will need to run this different executable next time to get the new version; or"
            )
            + "\n"
            + download_exe_yourself
            + "\n\n"
            + download_message
        )
        self["EXE_BROWSER_MESSAGE"] = (
            self["UPDATE_MESSAGE"]
            + "\n\n"
            + _(
                "You are running from an executable but the directory the executable is located in is not writeable by {name}. "
                + "This means that you will need to:"
            )
            + "\n"
            + download_exe_yourself
            + "\n\n"
            + download_message
        )
        self["EXE_UPDATE_MESSAGE"] = (
            self["UPDATE_MESSAGE"]
            + "\n\n"
            + _(
                'You are running from an executable file "{file}". To update you can either:'
            )
            + "\n"
            + _(
                '* Have {name} download and replace the executable file; or'
            )
            + "\n"
            + download_exe_yourself
            + "\n\n"
            + download_message
        )
        src_update = (
            _(
                "* Download the compressed source file using a browser, and unpack it yourself to:"
            )
            + "\n {path}\n\n".format(path=os.path.dirname(self.executable_path))
            + download_message
        )
        self["SRC_UPDATE_MESSAGE"] = (
            self["UPDATE_MESSAGE"]
            + "\n\n"
            + _(
                "You are running from downloaded source. To update you can either:"
            )
            + "\n"
            + _(
                "* Have {name} download and replace the source files; or"
            )
            + "\n"
            + src_update
        )
        self["SRC_BROWSER_MESSAGE"] = (
            self["UPDATE_MESSAGE"]
            + "\n\n"
            + _(
                "You are running from downloaded source. To update you can either:"
            )
            + _(
                "You are running from downloaded source but unfortunaely one or more directories or files "
                + "for this source copy are not writeable by {name}. This means that you will need to:"
            )
            + src_update
        )
        self["GIT_MESSAGE"] = (
            _(
                "You appear to be running from Git managed source code."
            )
            + "\n\n"
            + _(
                "If this is the case, you will need to use Git to update your source code."
            )
        )
        self["PACKAGE_MESSAGE"] = (
            _(
                "You are running from a packaged version of the {name} source, "
                + "and you will need to use your package manager to update your installed version."
            )
            + "\n\n"
            + _("If your package manager is Python's PIP3 then command should be something like:")
            + "\n"
            + "PIP3 install -u {name}"
        )
        self["UPDATER_HELP_URL"] = "https://github.com/meerk40t/meerk40t/wiki/Updater-FAQs"
        self["PROGRESS_TITLE"] = _("Downloading newer version...")
        self["PROGRESS_MESSAGE"] = _("Downloading {file}...")
        self["DOWNLOADED"] = _("Download complete: {file}")


        # List of possible file specs for each platform
        # For uniqueness, first specification (with {tag}) will be download filename
        # key: platform.system() + ":" + platform.machine()
        # The following has been derived from https://en.wikipedia.org/wiki/Uname
        windows32_spec = ["MeerK40t {tag}.exe", "MeerK40t.exe"]
        linux32_spec   = ["MeerK40t-Linux-{tag}", "Meerk40t-Linux"]
        rpi_spec       = ["MeerK40t_Pi_{tag}.tar", "Meerk40t_Pi.tar"]
        darwin_unsigned_spec = [
            "MeerK40t_unsigned_{tag}.dmg",
            "MeerK40t_{tag}.dmg",
            "Meerk40t_unsigned.dmg",
            "Meerk40t.dmg",
        ]
        darwin_m1_spec = ["MeerK40t_M1_{tag}.dmg", "MeerK40t_M1.dmg"]
        self["ASSET_MAP"] = {
            "Windows:i386"  : windows32_spec,
            "Windows:AMD64" : windows32_spec,
            "Linux:i686"    : linux32_spec,
            "Linux:x86_64"  : linux32_spec,
            "Linux:armv6l"  : rpi_spec,
            "Linux:armv7l"  : rpi_spec,
            "Linux:aarch64" : rpi_spec,
            "Darwin:i386"   : darwin_unsigned_spec, # MacOS 10.6
            "Darwin:i586"   : darwin_unsigned_spec, # Unknown versions
            "Darwin:i686"   : darwin_unsigned_spec, # Unknown versions
            "Darwin:x86_64" : darwin_unsigned_spec, # MacOS 10.7-10.15
            "Darwin:arm64"  : darwin_m1_spec, # MacOS 11 on M1
        }


        self["FILESPEC_TAG_OPTIONS"] = [
            "-{tag}",  # First will be appended to file name if all else fails
            "_{tag}",
            " {tag}",
            "{tag}",   # Shortest must come last
        ]

        # if self.root.updater_test:
            # print("updater messages:")
            # for id, msg in self.items():
                # print("{id}: {msg}".format(id=id, msg=msg))

    def set_test_mode(self) -> None:
        context = self.context
        _ = self._

        # Set current release to 0 so that all releases are new
        self.release_current = GHRelease(_)

        # In case you are testing when running from source, pretend to be running from exe
        self.executable_type = "exe"

        # Delete all previous update data
        context.updater_check_timestamp = ""
        context.updater_check_tag_full = ""
        context.updater_check_tag_beta = ""
        context.updater_check_tag_current = ""
        context.updater_check_last_reminder = ""

        # Run and report more frequently (minutes rather than days)
        self["DELAY_BETWEEN_AUTOCHECKS"] = datetime.timedelta(minutes=1)
        self["DELAY_BETWEEN_REMINDERS"] = datetime.timedelta(minutes=5)

        # Don't limit to releases x days old
        self["DAYS_AUTO_AFTER_RELEASE_FULL"] = datetime.timedelta(days=0)
        self["DAYS_AUTO_AFTER_RELEASE_BETA"] = datetime.timedelta(days=0)

        # Set random O/S & hardware
        self.system_type = choice(list(self["ASSET_MAP"].keys()))
        self.executable_type = choice(["exe", "git", "pkg", "src"])
        self.is_windows = self.system_type.startswith("Windows:")
        if self.executable_type == "exe":
            self.executable_path = os.path.join(
                os.path.dirname(self.executable_path),
                self["ASSET_MAP"][self.system_type][-1],
            )
        # Send debug channel to print / console
        self.debug.watch(print)
        if "console" in self.kernel.channels:
            self.debug.watch(self.kernel.channels["console"])
        self.debug(
            "updater_test: running in test mode as:\n\tsystype: {systype}\n\trun from: {ex_type}\n\tpath: {path}".format(
                systype=self.system_type,
                ex_type=self.executable_type,
                path=self.executable_path,
            )
        )
        # All options should now be testable using Preferences
        # GUI check will actually run autocheck GUI.

    def attach(self, *args, **kwargs) -> None:
        # Console check_for_updates
        # Runs entirely in a worker thread becuase console output works

        kernel = self.kernel
        _ = self._

        @kernel.console_command(
            "check_for_updates",
            help=_("Check whether a newer version is available"),
        )
        def console_check_for_updates(channel: Channel, _: Callable[[str], str], **kwargs) -> None:
            """
            This command checks for updates and outputs the results to the console.
            """
            kernel.threaded(
                self.updater_console, channel,
                thread_name="Updater"
            )

        # GUI Help/Check for updates
        # Lookup/analysis and download functions run in a worker thread
        # GUI dialogs to report release status and download success run on main thread
        if GUI_ENABLED:
            kernel.register("updater/gui", self.updater_gui)
            self.context.listen("updater;download_progress", self.gui_download_progress)

    def startup(self):
        # Startup
        if self.root.updater_check_automated:
            self.updater_startup()

    # ==========
    # Console/Gui/Startup update control flows
    # ==========

    def updater_console(self, channel: Channel, autocheck: Optional[bool]=False) -> None:
        # Whole execution runs on worker thread
        self.debug(
            "updater_console: called on worker - autocheck={autocheck}".format(
                autocheck=autocheck
            )
        )
        try:
            release_full, release_beta = self.updater_check()
        except UpdaterWebError as e:
            self.debug("updater_console: web error")
            if not autocheck:
                self.console_weberror(channel, e)
            return

        self.store_last_check(release_full, release_beta)
        release_current = self.release_current
        if (
            (
              release_current.version == release_full.version
              and release_beta.tag == ""
            )
            or (
              release_current.version == release_beta.version
              and release_beta.tag
            )
        ):
            self.debug("updater_console: up to date")
            self.console_up_to_date(channel, release_current)
            return

        if(
            release_current.version > release_full.version
            and release_current.version > release_beta.version
        ):
            self.debug("updater_console: running pre-release version")
            self.console_prerelease(channel, release_current)
            return

        # Advise user of new release
        self.store_last_reminder()
        if release_current.version < release_full.version:
            self.debug("updater_console: newer full")
            self.console_new_release(channel, release_full)

        if release_current.version < release_beta.version:
            self.debug("updater_console: newer beta")
            self.console_new_release(channel, release_beta)

    def updater_gui(self, autocheck: Optional[bool]=False) -> None:
        # Runs on main thread
        """
        Called from the help menu, this function checks for updates and pops
        up a window if appropriate.
        """
        self.debug(
            "updater_gui: called on main - autocheck={autocheck}".format(
                autocheck=autocheck
            )
        )

        # If we are in test mode, then GUI run is treated as an autocheck
        if not autocheck and self.root.updater_test:
            self.debug("updater_gui: running in test mode as autocheck")
            autocheck = True

        self.kernel.threaded(
            self.updater_gui_check, autocheck,
            thread_name="Updater"
        )

    def updater_gui_check(self, autocheck: Optional[bool]=False) -> None:
        # Runs on worker thread
        self.debug(
            "updater_gui: check called on worker - autocheck={autocheck}".format(
                autocheck=autocheck
            )
        )
        try:
            release_full, release_beta = self.updater_check(autocheck)
            if release_full is None:
                return
        except UpdaterWebError as e:
            self.debug("updater_gui: github web error")
            # If autocheck we do not report web errors to the user
            if not autocheck:
                # self.context.signal("updater;to_main", self.gui_weberror, e)
                self.kernel.run_later(self.gui_weberror, e)
            return

        # If autocheck, then we may suppress repeat results if user has deferred an update.
        if autocheck:
            # If results have not changed; and
            # Elapsed time since results last advised is insufficient
            # Then save current results and don't do any more processing
            if (
                self.is_same_as_last_check(release_full, release_beta)
                and self.is_alert_deferred()
            ):
                self.debug("updater_gui: autocheck user alert deferred")
                self.store_last_check(release_full, release_beta)
                return

        self.store_last_check(release_full, release_beta)

        # Unlike console, only now interested in single new version
        if release_beta.tag:
            new_release = release_beta
        else:
            new_release = release_full

        # Find correct download, check whether MK download/update is possible etc.
        self.analyse_update(new_release)

        self.kernel.run_later(
            self.updater_gui_results,
            new_release,
            autocheck,
        )

    def analyse_update(self, release: GHRelease) -> bool:
        """
        Determine all the data needed for a later download etc.
        1. Asset to download, filename for new download file
        2. Whether download by MK should be enabled, and if so whether replace or download
        3. Download by MK disabled if insufficient diskspace required, etc.
        """
        # This method decides whether MK download of the new release is possible:
        #   1.  We cannot risk overwriting the existing files directly in case overwrite is interrupted by
        #       e.g. a crash or power failure, and so need to download (and unpack) a separate copy and then rename.
        #   2.  To update We therefore need to have access rights sufficient to create a new executable / source directory
        #       alongside the existing one, and to rename existing to old and new to existing.
        #   3.  There needs to be sufficient disk space to allow this to happen.
        # If all the above are true, then Meerk40t can manage the download and update.

        # If user has disabled updater
        if self.root.updater_download_browser:
            return False

        # If we are a Pypi or Git run from source:
        if self.executable_type in ["pkg", "git"]:
            return False

        # If exe, then we need sufficient space for the download of the new executable
        if self.executable_type == "exe":
            s

    def updater_gui_results(self,
        release: GHRelease,
        autocheck: Optional[bool]=False
    ) -> None:
        # Runs on main thread
        self.debug(
            "updater_gui: results called on main - autocheck={autocheck}".format(autocheck=autocheck)
        )
        release_current = self.release_current
        if release_current.version == release.version:
            self.debug("updater_gui: up to date")
            if autocheck:
                self.debug("updater_gui: autocheck: up to date - user advise skipped")
            else:
                self.gui_up_to_date(release_current)
            return

        if release_current.version > release.version:
            self.debug("updater_gui: running pre-release version")
            if autocheck:
                self.debug("updater_gui: autocheck: running pre-release - user advise skipped")
            else:
                self.gui_prerelease(release_current)
            return

        # Advise user of new release
        self.store_last_reminder()
        self.debug("updater_gui: advise newer version")
        download = self.gui_new_release(release, autocheck)
        if download is ENUM_DOWNLOAD_NO:
            self.debug("updater_gui: button no/defer")
        elif download is ENUM_DOWNLOAD_MK:
            self.debug("updater_gui: button download")
            if self.executable_type == "exe":
                self.updater_download_exe(release)
                return
            if self.executable_type == "src":
                self.updater_download_src(release)
                return
        elif download is ENUM_DOWNLOAD_BROWSER:
            self.debug("updater_gui: button browser")
        else:
            self.debug("updater_gui: button unknown")

    def updater_download_browser(self, release: GHRelease) -> None:
        url = release.download_url
        self.debug('updater_download_exe: opening {url} in browser'.format(url=url))
        import webbrowser
        webbrowser.open(url)

    def updater_download_exe(self, release: GHRelease) -> None:
        """
        Based on the o/s type, derive the executable link from the response asset list and,
        depending on whether the executable path is writeable,
        either download the file directly or open a browser to download the file .
        """
        # Runs in main thread
        self.debug("updater_gui: download exe on main")

        # If Windows then we
        if self.system_type in self["ASSET_MAP"]:
            file_specs = self["ASSET_MAP"][system_type]
        else:
            # Attempt to derive file_specs from current filename
            current_tag = self.release_current.tag
            file_specs = []
            executable_name = os.path.basename(sys.executable)
            if current_tag in executable_name:
                for param in self["FILESPEC_TAG_OPTIONS"]:
                    tag = param.format(tag=current_tag)
                    if tag in executable_name:
                        # Option 1 - equivalent filename with current tag replaced with {tag}
                        file_specs.append[executable_name.replace(spec_tag, spec)]
                        # Option 2 - no tag in filename
                        file_specs.append[executable_name.replace(spec_tag, "")]
                        break
            if not file_specs:
                name, ext = os.path.splitext(executable_name)
                for spec in self["FILESPEC_TAG_OPTIONS"]:
                    file_specs.append(name + spec + ext)
                file_specs.append(executable_name)
        self.debug("updater_download_exe: specs " + str(file_specs))

        # Find file spec (possibly with tag applied) that matches an asset name
        release_tag = release.tag
        response = release.response
        links = []
        for spec in file_specs:
            name = spec.format(tag=release_tag).lower()
            for asset in response["assets"]:
                if asset["name"].lower() == name:
                    links.append((spec, asset))
        self.debug("updater_download_exe: links " + str(links))

        download_name = file_specs[0].format(tag=release_tag)
        download_path = self.executable_path
        download_full = os.path.join(os.path.dirname(download_path), download_name)
        if len(links) == 1:
            # Only one possible asset
            spec, asset = links[0]
            if not self.root.updater_download_browser and os.access(download_path, os.W_OK):
                # Download directly
                self.kernel.threaded(
                    self.updater_gui_download, asset, download_full,
                    thread_name="Updater"
                )
                return
            # Download executable in browser
            url = asset["browser_download_url"]
        else:
            # Open release page in browser
            url = response["html_url"]

        self.debug('updater_download_exe: opening {url} in browser'.format(url=url))
        import webbrowser
        webbrowser.open(url)

    def updater_download_src(self, release: GHRelease) -> None:
        """
        Derive the src type (zip or tar) from o/s type,
        derive the file link from the response,
        and open a browser to download the appropriate asset.
        """
        # Runs in main thread
        self.debug("updater_gui: download src on main")
        if self.is_windows:
            self.debug("updater_gui: windows - download zip")
            url = release.response["zipball_url"]
        else:
            self.debug("updater_gui: non-windows - download tar")
            url = release.response["tarball_url"]

        self.debug('updater_download_exe: opening {url} in browser'.format(url=url))
        import webbrowser
        webbrowser.open(url)


    def updater_gui_download(self, asset: Dict, file_path: str) -> None:
        # Runs on worker thread
        # progress is used to pass values to the progress bar but also
        # to store the reference to the wx ProgressDialog object
        progress = {
            "file_path": file_path,
            "file_size": asset["size"],
        }
        url = asset["browser_download_url"]
        self.debug('updater_gui: download on worker {url} to "{file}"'.format(url=url, file=file_path))
        try:
            filename, headers = urlretrieve(
                url,
                file_path,
                reporthook=partial(
                    self.gui_download_reporthook,
                    progress,
                ),
            )
        except URLError as e:
            self.debug("updater_gui: download web error")
            self.kernel.run_later(
                self.gui_weberror,
                UpdaterWebError("Direct download failed: " + str(e))
            )
            return

        # Check that downloaded filename as expected
        if filename != file_path:
            self.debug("updater_gui: download file not correct path")
            self.kernel.run_later(
                self.gui_weberror,
                UpdaterWebError("Direct download failed: incorrect filename")
            )
            return
        # Check that downloaded filesize matches Github
        size = asset["size"]
        if os.path.getsize(file_path) != size:
            self.debug("updater_gui: download file not correct size")
            self.kernel.run_later(
                self.gui_weberror,
                UpdaterWebError("Direct download failed: file size incorrect")
            )
            return

        self.kernel.run_later(self.gui_download_successful, file_path)

    def gui_download_reporthook(self,
        progress: Dict,
        blks: int,
        blk_size: int,
        size: int
    ) -> None:
        progress["blks"] = blks
        progress["blk_size"] = blk_size
        percent = min(int(blks * blk_size * 100 / progress["file_size"]), 100)
        if (
            "percent" not in progress
            or percent > progress["percent"]
        ):
            progress["percent"] = percent
            self.context.signal(
                "updater;download_progress",
                progress,
            )
        else:
            progress["percent"] = percent

    def updater_startup(self) -> None:
        # Runs on main thread

        # If disabled, do nothing
        if not self.root.updater_check_automated:
            self.debug("updater_autocheck: disabled")
            return

        self.debug("updater_autocheck: called at startup")
        # If we are running in console mode, we will always run the console command
        if not GUI_ENABLED:
            self.debug("updater_autocheck: running as console")
            self.kernel.threaded(
                self.updater_console, self.kernel.channel("console"), True,
                thread_name="Updater"
            )
            return

        # Check whether sufficient elapsed time has happened since we last ran the check
        if self.is_autocheck_due():
            self.updater_gui(autocheck=True)


    # ==========
    # Display routines - Console / Gui versions
    # ==========

    def console_weberror(self, channel: Channel, e: Exception) -> None:
        channel(self["WEB_ERROR_MESSAGE"].format(exception=e))

    def console_up_to_date(self, channel: Channel, release: GHRelease) -> None:
        channel(
            self["CURRENT_MESSAGE"].format(
                release_type=release.release_type,
                name=self.kernel.name,
            )
        )

    def console_prerelease(self, channel: Channel, release: GHRelease) -> None:
        channel(
            self["PRERELEASE_MESSAGE"].format(
                release_type=release.release_type,
                name=self.kernel.name,
            )
        )

    def console_new_release(self, channel: Channel, release: GHRelease) -> None:
        channel(
            self["UPDATE_MESSAGE"].format(
                release_type=release.release_type,
                tag=release.tag,
                url=release.response["html_url"],
                name=self.kernel.name,
            )
        )

    def gui_weberror(self, e: Exception) -> None:
        dlg = UpdateMessageDialog(
            self["WEB_ERROR_MESSAGE"].format(exception=e),
            caption=self["GUI_CAPTION"],
            style=wx.OK | wx.ICON_WARNING | wx.CENTRE,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def gui_up_to_date(self, release: GHRelease) -> None:
        dlg = UpdateMessageDialog(
            self["CURRENT_MESSAGE"].format(
                release_type=release.release_type,
                name=self.kernel.name,
            ),
            caption=self["GUI_CAPTION"],
            style=wx.OK | wx.ICON_WARNING | wx.CENTRE,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def gui_prerelease(self, release: GHRelease) -> None:
        dlg = UpdateMessageDialog(
            self["PRERELEASE_MESSAGE"].format(
                release_type=release.release_type,
                name=self.kernel.name,
            ),
            caption=self["GUI_CAPTION"],
            style=wx.OK | wx.ICON_WARNING | wx.CENTRE,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def gui_new_release(self, release: GHRelease, autocheck: Optional[bool]=False) -> Optional[int]:
        # Runs on main

        # Button mappings
        # Ok/Cancel - do not download now - shown as "Ok" or "No" or "Defer..." depending on execution_type
        # Yes - Internal download - shown as "Update" or "Download"
        # No - Browser download - shown as "Download with browser" or "Open Release page"

        executable_type = self.executable_type
        if autocheck:
            okmsg = cancelmsg = self["DEFER"].format(days=self["DELAY_BETWEEN_REMINDERS"].days)
        else:
            cancelmsg = self["NO"]
            okmsg = self["OK"]

        if executable_type in ["exe", "src"]:
            yesmsg = self["UPDATE"]
            if executable_type == "exe":
                if self.is_windows:
                    msg = self["EXE_DOWNLOAD_MESSAGE"]
                    yesmsg = self["DOWNLOAD_EXECUTABLE"]
                else:
                    msg = self["EXE_UPDATE_MESSAGE"]
            else:
                msg = self["SRC_UPDATE_MESSAGE"]
            msg = msg.format(
                release_type=release.release_type,
                tag=release.tag,
                path=self.executable_path,
                url=release.response["html_url"],
                name=self.kernel.name,
            )
            dlg = UpdateMessageDialog(
                msg,
                caption=self["GUI_CAPTION"],
                style=wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION | wx.CENTRE | wx.HELP,
            )
            dlg.SetYesNoCancelLabels(yesmsg, self["DOWNLOAD_BROWSER"], cancelmsg)

        elif executable_type in ["git", "pkg"]:
            msg = self["GIT_MESSAGE"] if executable_type == "git" else self["PKG_MESSAGE"]
            msg = msg.format(
                release_type=release.release_type,
                tag=release.tag,
                path=self.executable_path,
                url=release.response["html_url"],
                name=self.kernel.name,
            )
            dlg = UpdateMessageDialog(
                msg,
                caption=self["GUI_CAPTION"],
                style=wx.OK | wx.ICON_INFORMATION | wx.CENTRE | wx.HELP,
            )
            dlg.SetCancelLabel(okmsg)

        dlg.SetHelpLabel(self["GUI_HELP"])
        while True:
            download = dlg.ShowModal()
            if download == wx.ID_HELP:
                import webbrowser
                webbrowser.open(self["UPDATER_HELP_URL"])
            else:
                break
        download = (
            ENUM_DOWNLOAD_NO if download in [wx.ID_OK, wx.ID_CANCEL]
            else ENUM_DOWNLOAD_MK if download in [wx.ID_YES]
            else ENUM_DOWNLOAD_BROWSER if download in [wx.ID_NO]
            else None
        )
       dlg.Destroy()

        return download

    def gui_download_progress(self, path: str, progress: Dict[str, Any]) -> None:
        blks = progress["blks"]
        blk_size = progress["blk_size"]
        file_size = progress["file_size"]
        percent = progress["percent"]
        self.debug(
            "gui_download_progress: {percent}%: {blks} blocks of {blk_size} bytes out of {file_size}".format(
                blks=blks,
                blk_size=blk_size,
                file_size=file_size,
                percent=percent,
            )
        )
        if not "dlg" in progress:
            # Open progress bar
            # We store a reference to the dialog in the progress dict so it is persistent
            progress["dlg"] = wx.GenericProgressDialog(
                self["PROGRESS_TITLE"],
                self["PROGRESS_MESSAGE"].format(file=os.path.dirname(progress["file_path"])),
                style=
                    wx.PD_SMOOTH
                    | wx.PD_AUTO_HIDE
                    | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME,
            )
        if "dlg" in progress and blks * blk_size >= file_size:
            # Close progress bar
            progress["dlg"].Destroy()
            del progress["dlg"]
        else:
            # Update progress bar
            progress["dlg"].Update(percent)

    def gui_download_successful(self, file_path: str) -> None:
        dlg = UpdateMessageDialog(
            self["DOWNLOADED"].format(
                file=file_path,
            ),
            caption=self["GUI_CAPTION"],
            style=wx.OK | wx.ICON_WARNING | wx.CENTRE,
        )
        dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def gui_split_message(msg: str) -> tuple:
        ext = None
        if "\n" in msg:
            msg, ext = msg.split("\n", 1)
            ext = ext.strip("\n")
        return msg, ext


    # ==========
    # Background processing
    # ==========

    def updater_check(self, autocheck: Optional[bool]=False) -> Tuple[Optional[GHRelease], Optional[GHRelease]]:
        # Runs on worker
        req = Request(self["GITHUB_RELEASES"])
        req.add_header("Accept", self["HEADER_ACCEPT"])
        req.add_header("User-Agent", self["HEADER_USERAGENT"])

        try:
            req = urlopen(req)
        except URLError as e:
            self.debug("updater_check: UrlError: " + str(e))
            if not autocheck:
                # self.context.signal("updater;to_main", self.gui_weberror, e)
                self.kernel.run_later(self.gui_weberror, e)
            return None, None

        responses = json.loads(req.read())
        # responses = json.loads("[{}]")  # Uncomment to test invalid response
        if len(responses) == 0:
            self.debug("updater_check: Github JSON response empty")
            if not autocheck:
                # self.context.signal(
                    # "updater;to_main",
                    # self.gui_weberror,
                    # UpdaterWebError("Empty GitHub JSON response")
                # )
                self.kernel.run_later(
                    self.gui_weberror,
                    UpdaterWebError("Empty GitHub JSON response")
                )
            return None, None

        return self.updater_process(responses, autocheck)

    def updater_process(self,
        responses: List[Dict],
        autocheck: Optional[bool]=False
    ) -> Tuple[GHRelease, GHRelease]:
        # Runs on worker
        kernel = self.kernel
        _ = kernel.translation

        updater_check_betas = kernel.root.updater_check_betas
        release_current = self.release_current

        self.debug(
            "updater_process: current {tag} {version}".format(
                tag=release_current.tag,
                version=release_current.version
            )
        )

        release_full = release_beta = GHRelease(_)
        for response in responses:
            if (
                "tag_name" not in response
                or "draft" not in response
                or "prerelease" not in response
                or "published_at" not in response
            ):
                self.debug("updater_process: Github JSON response missing key data")
                if not autocheck:
                    self.kernel.run_later(
                        self.gui_weberror,
                        UpdaterWebError("Invalid GitHub JSON response - missing attribute(s)")
                    )
                return None, None

            if response["draft"]:
                continue

            release = GHRelease(_, response=response)
            if release.version < release_current.version:
                continue

            # If autocheck then only use releases that are sufficiently old
            if autocheck:
                try:
                    published = datetime.datetime.strptime(
                        response["published_at"],
                        self["GITHUB_TIMESTAMP_FORMAT"],
                    ).date()
                except ValueError as e:
                    self.debug("updater_process: Github 'published_at' time format invalid")
                    if not autocheck:
                        self.kernel.run_later(
                            self.gui_weberror,
                            UpdaterWebError("Github 'published_at' time format invalid"),
                        )
                    return None, None

                defer_time = self.defer_time(release)
                if (datetime.date.today() - published) < defer_time:
                    self.debug(
                        "updater_autocheck: skipping release published within {days} days".format(
                            days=defer_time.days,
                        )
                    )
                    release_beta = release
                    continue

            if release.beta:
                if release.version > release_beta.version:
                    # Check all betas
                    if updater_check_betas:
                        self.debug(
                            "updater_autocheck: check betas selected: beta found {tag}".format(
                                tag=release.tag,
                            )
                        )
                        release_beta = release
                    # Temp running beta and later one of the same release
                    elif (
                        release_current.beta
                        and release.version[0:3] == release_current.version[0:3]
                        and release.version[3] > release_current.version[3]
                    ):
                        self.debug(
                            "updater_autocheck: running a beta: later beta found {tag}".format(
                                tag=release.tag,
                            )
                        )
                        release_beta = release
            elif release.version > release_full.version:
                release_full = release

        # If full version is latest, disregard betas
        if release_full.version > release_beta.version:
            release_beta = GHRelease(_)

        self.debug(
            "updater_process: full {tag} {version}".format(
                tag=release_full.tag,
                version=release_full.version,
            )
        )
        self.debug(
            "updater_process: beta {tag} {version}".format(
                tag=release_beta.tag,
                version=release_beta.version,
            )
        )

        return release_full, release_beta

    # ==========
    # Automated check decision functions
    # ==========

    @staticmethod
    def now() -> str:
        return datetime.datetime.now().astimezone().isoformat()

    def defer_time(self, release: GHRelease) -> datetime.timedelta:
        if release.beta:
            return self["DAYS_AUTO_AFTER_RELEASE_BETA"]
        return self["DAYS_AUTO_AFTER_RELEASE_FULL"]

    @staticmethod
    def is_timeout(timestamp: str, wait: datetime.timedelta) -> bool:
        now = datetime.datetime.now().astimezone()
        then = datetime.datetime.fromisoformat(timestamp).astimezone()
        return (now - then) >= wait

    def is_autocheck_due(self) -> bool:
        root = self.root
        context = self.context
        if not root.updater_check_automated:
            return False
        if context.updater_check_timestamp == "":
            self.debug("updater_autocheck: last check time blank")
            return True
        if context.updater_check_tag_current != self.release_current.tag:
            self.debug("updater_autocheck: executing version has changed")
            return True
        timestamp = context.updater_check_timestamp
        delay = self["DELAY_BETWEEN_AUTOCHECKS"]
        due = self.is_timeout(
            timestamp,
            delay,
        )
        self.debug(
            "updater_autocheck: autocheck due: {due} - Previous check: {timestamp}, delay: {delay}".format(
                due=due,
                timestamp=timestamp,
                delay=delay,
            )
        )
        return due

    def is_same_as_last_check(self, release_full: GHRelease, release_beta: GHRelease) -> bool:
        context = self.context
        updater_check_tag_current = context.updater_check_tag_current
        updater_check_tag_full = context.updater_check_tag_full
        updater_check_tag_beta = context.updater_check_tag_beta
        self.debug("updater: updater_check_tag_current={value}".format(value=updater_check_tag_current))
        self.debug("updater: updater_check_tag_full={value}".format(value=updater_check_tag_full))
        self.debug("updater: updater_check_tag_beta={value}".format(value=updater_check_tag_beta))
        if updater_check_tag_current != self.release_current.tag:
            self.debug("updater_autocheck: results different - running different version")
            return False
        if updater_check_tag_full != release_full.tag:
            self.debug("updater_autocheck: results different - full release different")
            return False
        if updater_check_tag_beta != release_beta.tag:
            self.debug("updater_autocheck: results different - beta release different")
            return False
        self.debug("updater_autocheck: results same as last check")
        return True

    def is_alert_deferred(self) -> bool:
        context = self.context
        if context.updater_check_last_reminder == "":
            self.debug("updater_autocheck: alert not deferred - last reminder blank")
            return false
        alert = self.is_timeout(
            context.updater_check_last_reminder,
            self["DELAY_BETWEEN_REMINDERS"],
        )
        self.debug("updater_autocheck: alert: {alert}".format(alert=alert))
        return not alert

    # ==========
    # Context updates
    # ==========

    def store_last_check(self, release_full: GHRelease, release_beta: GHRelease) -> None:
        context = self.context
        now = self.now()

        context.updater_check_tag_full = release_full.tag
        self.debug("updater: set context.updater_check_tag_full = " + release_full.tag)
        context.updater_check_tag_beta = release_beta.tag
        self.debug("updater: set context.updater_check_tag_beta = " + release_beta.tag)
        context.updater_check_tag_current = self.release_current.tag
        self.debug("updater: set context.updater_check_tag_current = " + self.release_current.tag)
        context.updater_check_timestamp = now
        self.debug("updater: set context.updater_check_timestamp = " + now)

    def store_last_reminder(self) -> None:
        context = self.context
        now = self.now()

        context.updater_check_last_reminder = now
        self.debug("updater: set context.updater_check_last_reminder = " + now)


"""
show publication date of versions
unittests
<<<<<<< Updated upstream
=======
fix executable download file unwriteable (because it is in use)
check writeability for update and only shown browser download if not available
handle Update vs Browser as return code
do src unpack
>>>>>>> Stashed changes
"""
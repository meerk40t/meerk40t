"""
The code inside this module provides routines to look for newer versions of meerk40t on GitHub
"""
import http.client
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        choices = [
            {
                "attr": "update_check",
                "object": kernel.root,
                "default": 1,
                "type": int,
                "label": _("Action"),
                "style": "option",
                "display": (
                    _("No, thank you"),
                    _("Look for major releases"),
                    _("Look for major+beta releases"),
                ),
                "choices": (0, 1, 2),
                "tip": _("Check for available updates on startup."),
                "page": "Options",
                "section": "Check for updates on startup",
            },
            {
                "attr": "update_frequency",
                "object": kernel.root,
                "default": 1,
                "type": int,
                "label": _("Frequency"),
                "style": "option",
                "display": (
                    _("At every startup"),
                    _("Once per day"),
                    _("Once per week"),
                ),
                "choices": (0, 1, 2),
                "tip": _("How often should MeerK40t look for new versions"),
                "page": "Options",
                "section": "Check for updates on startup",
                "conditional": (kernel.root, "update_check", 1, 2),
            },
        ]
        kernel.register_choices("preferences", choices)

        # https://docs.github.com/en/rest/reference/repos#get-the-latest-release
        GITHUB_LATEST = "https://api.github.com/repos/meerk40t/meerk40t/releases/latest"
        # https://docs.github.com/en/rest/reference/repos#list-releases
        GITHUB_RELEASES = (
            "https://api.github.com/repos/meerk40t/meerk40t/releases?perpage=100"
        )
        GITHUB_HEADER = ("Accept", "application/vnd.github.v3+json")

        UPDATE_MESSAGE_HEADER = _("A new {type} release is available:")
        UPDATE_MESSAGE_BODY = _(
            "Version: {name} v{version} ({label})\n" + "Url: {url}\n" + "Info: {info}"
        )
        NO_UPDATE_MESSAGE_HEADER = _("You seem to have the latest version.")
        NO_UPDATE_MESSAGE_BODY = _(
            "Latest version on github: {name} v{version} ({label})\n"
            + "Url: {url}\n"
            + "Info: {info}"
        )
        ERROR_MESSAGE = _("Could not find any release information on github")

        context = kernel.root
        context.setting(bool, "check_for_betas", False)

        @context.console_option(
            "beta", "b", type=bool, action="store_true", help=_("Check for betas")
        )
        @context.console_option(
            "verbosity",
            "v",
            type=int,
            help="Show Info: 0 never, 1 console only, 2 if version found, 3 always",
        )
        @context.console_option(
            "force", "f", type=bool, action="store_true", help=_("Force a found message")
        )
        @kernel.console_command(
            "check_for_updates",
            help=_("Check whether a newer version of Meerk40t is available"),
        )
        def check_for_updates(channel, _, beta=None, verbosity=None, force=None, **kwargs):
            """
            This command checks for updates and outputs the results to the console.

            If we run a beta
            then we get the release list and iterate through
            to find the latest full and beta releases that are > currently running

            If we are not currently running a beta
            then we check only for a full release > currently running
            """

            def comparable_version(version):
                """
                Return a comparable sequence from a version string
                "Major", "Minor", "Release", "Beta"
                Beta is derived from Release by default if release > 100 and last two digits != 0
                """
                src = beta = False
                orgversion = version
                ending = ""
                result = list()
                if version is not None:
                    if version.startswith("v"):
                        version = version[1:]
                    if " " in version:
                        version, ending = version.split(" ", 1)
                    if ending == "git":
                        src = True
                    elif ending == "src":
                        src = True

                    result = list(map(int, version.split(".")))
                    if len(result) > 3:
                        result = result[0:2]
                while len(result) < 3:
                    result.append(0)
                if result[2] > 100:
                    subrelease = result[2] % 100
                    beta = bool(subrelease != 0)
                result.append(beta)
                result.append(src)
                # print (f"Looking at {orgversion}: {result}")
                return result

            def extract_from_json(response):
                # print (response)
                tag = response["tag_name"]
                version = comparable_version(tag)
                if response["prerelease"]:
                    version[3] = True
                url = response["html_url"]
                assets = response["assets"]
                label = response["name"]
                rel_info = ""
                if response["body"]:
                    infomessages = response["body"].split("\n")
                    for idx, line in enumerate(infomessages):
                        if (
                            "what's changed" in line.lower()
                            or "full changelog:" in line.lower()
                            or idx > 6
                        ):
                            # Too much information... stop
                            break
                        if rel_info != "":
                            rel_info += "\n"
                        rel_info += line
                rel_info = rel_info.strip()
                return tag, version, label, url, assets, rel_info

            def newer_version(candidate_version, reference_version):
                """
                Checks whether the given candidate_version is newer than
                the provided reference_version
                Args:
                    candidate_version: tuple (major, minor, release, is_a_beta, is_source)
                    reference_version: tuple (major, minor, release, is_a_beta, is_source)
                """
                is_newer = False
                sub_ref = [0, 0, 0]
                sub_cand = [0, 0, 0]
                # python can compare lists
                if candidate_version is not None and isinstance(
                    candidate_version, (list, tuple)
                ):
                    sub_cand = list(candidate_version[0:3])
                if reference_version is not None and isinstance(
                    reference_version, (list, tuple)
                ):
                    sub_ref = list(reference_version[0:3])
                # print (sub_cand, sub_ref, bool(sub_cand > sub_ref))
                try:
                    if sub_cand > sub_ref:
                        is_newer = True
                except TypeError:
                    # Invalid data
                    is_newer = False
                # print (f"Comparing {candidate_version} vs {reference_version}: {is_newer}")
                return is_newer

            def update_check(verbosity=None, beta=None, force=None):
                def update_test(*args):
                    version_current = comparable_version(kernel.version)
                    # print (f"Current version: {version_current}")
                    if force:
                        version_current = (0, 0, 0, 0)
                    is_a_beta = version_current[3]
                    if beta:
                        url = GITHUB_RELEASES
                    else:
                        url = GITHUB_LATEST
                    if verbosity > 0:
                        channel(
                            f"Testing against current {'beta' if is_a_beta else 'full'} version: {kernel.version} (include betas: {'yes' if beta else 'no'})"
                        )
                    req = Request(url)
                    req.add_header(*GITHUB_HEADER)
                    try:
                        req = urlopen(req)
                        response = json.loads(req.read())
                    except (HTTPError, URLError, http.client.IncompleteRead):
                        if verbosity > 0:
                            channel(ERROR_MESSAGE)
                        return

                    tag_full = tag_beta = None
                    label_full = label_beta = None
                    version_full = version_beta = version_newest = None
                    url_full = url_beta = None
                    assets_full = assets_beta = None
                    info_full = info_beta = ""
                    something = False
                    if beta:
                        for resp in response:
                            if resp["draft"]:
                                continue
                            (
                                tag,
                                version,
                                label,
                                url,
                                assets,
                                rel_info,
                            ) = extract_from_json(resp)
                            # What is the newest beta
                            if resp["prerelease"]:
                                if newer_version(version, version_beta):
                                    (
                                        tag_beta,
                                        version_beta,
                                        label_beta,
                                        url_beta,
                                        assets_beta,
                                        info_beta,
                                    ) = (
                                        tag,
                                        version,
                                        label,
                                        url,
                                        assets,
                                        rel_info,
                                    )
                            # What is the newest release
                            elif newer_version(version, version_full):
                                (
                                    tag_full,
                                    version_full,
                                    label_full,
                                    url_full,
                                    assets_full,
                                    info_full,
                                ) = (
                                    tag,
                                    version,
                                    label,
                                    url,
                                    assets,
                                    rel_info,
                                )
                        # If full version is latest, disregard betas
                        if newer_version(version_full, version_beta):
                            (
                                tag_beta,
                                version_beta,
                                label_beta,
                                url_beta,
                                assets_beta,
                                info_beta,
                            ) = (
                                None,
                                None,
                                None,
                                None,
                                None,
                                "",
                            )
                    else:
                        resp = response
                        (
                            tag_full,
                            version_full,
                            label_full,
                            url_full,
                            assets_full,
                            info_full,
                        ) = extract_from_json(resp)
                    # print (f"Newest release: {version_full}, newest beta: {version_beta}, current: {version_current}")
                    version_newest = version_full
                    tag_newest = tag_full
                    url_newest = url_full
                    label_newest = label_full
                    type_newest = ""
                    info_newest = info_full
                    if newer_version(version_beta, version_full):
                        version_newest = version_beta
                        tag_newest = tag_beta
                        label_newest = label_beta
                        url_newest = url_beta
                        type_newest = " (beta)"
                        info_newest = info_beta
                        # print ("Beta is newer than full")
                    newest_message_header = ""
                    newest_message_body = ""
                    if newer_version(version_full, version_current):
                        something = True
                        message_header = UPDATE_MESSAGE_HEADER.format(
                            type="full",
                        )
                        message_body = UPDATE_MESSAGE_BODY.format(
                            name=kernel.name,
                            version=tag_full,
                            label=label_full,
                            url=url_full,
                            info=info_full,
                        )
                        if verbosity > 0:
                            channel(message_header + "\n" + message_body)
                        newest_message_header = message_header
                        newest_message_body = message_body

                    if newer_version(version_beta, version_current):
                        something = True
                        message_header = UPDATE_MESSAGE_HEADER.format(type="beta")
                        message_body = UPDATE_MESSAGE_BODY.format(
                            name=kernel.name,
                            version=tag_beta,
                            label=label_beta,
                            url=url_beta,
                            info=info_beta,
                        )
                        if verbosity > 0:
                            channel(message_header + "\n" + message_body)
                        newest_message_header = message_header
                        newest_message_body = message_body
                    # print (f"Something: {something}, verbosity={verbosity}")
                    has_wx = False
                    try:
                        import wx

                        from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
                        from meerk40t.gui.wxutils import dip_size

                        has_wx = True
                    except ImportError:
                        pass
                    action = False

                    def get_response(header, content, footer):
                        if has_wx:
                            # Very simple panel
                            dlg = wx.Dialog(
                                None,
                                wx.ID_ANY,
                                title=_("Update-Info"),
                                size=wx.DefaultSize,
                                pos=wx.DefaultPosition,
                                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                            )
                            # contents
                            sizer = wx.BoxSizer(wx.VERTICAL)

                            label = wx.StaticText(dlg, wx.ID_ANY, header)
                            sizer.Add(label, 0, wx.EXPAND, 0)
                            info = wx.TextCtrl(
                                dlg, wx.ID_ANY, style=wx.TE_READONLY | wx.TE_MULTILINE
                            )
                            info.SetValue(content)
                            sizer.Add(info, 1, wx.EXPAND, 0)
                            label = wx.StaticText(dlg, wx.ID_ANY, footer)
                            sizer.Add(label, 0, wx.EXPAND, 0)
                            btnsizer = wx.StdDialogButtonSizer()
                            btn = wx.Button(dlg, wx.ID_OK)
                            btn.SetDefault()
                            btnsizer.AddButton(btn)
                            btn = wx.Button(dlg, wx.ID_CANCEL)
                            btnsizer.AddButton(btn)
                            btnsizer.Realize()
                            sizer.Add(btnsizer, 0, wx.EXPAND, 0)
                            panel = ChoicePropertyPanel(
                                dlg, wx.ID_ANY, context=context, choices=choices
                            )
                            sizer.Add(panel, 1, wx.EXPAND, 0)
                            dlg.SetSizer(sizer)
                            sizer.Fit(dlg)
                            dlg.SetSize(dip_size(dlg, 620, 400))
                            dlg.CenterOnScreen()
                            answer = dlg.ShowModal()
                            dlg.Destroy()
                            response = bool(answer in (wx.YES, wx.ID_YES, wx.ID_OK))
                        else:
                            question = header + "\n" + content + "\n" + footer
                            response = kernel.yesno(question)
                        return response

                    if something:
                        # if we have a hit then we brag about it
                        #
                        if verbosity > 1:
                            action = get_response(
                                newest_message_header,
                                newest_message_body,
                                _("Do you want to go the download page?"),
                            )
                    else:
                        if version_newest is not None:
                            message_header = NO_UPDATE_MESSAGE_HEADER
                            message_body = NO_UPDATE_MESSAGE_BODY.format(
                                name=kernel.name,
                                version=tag_newest,
                                type=type_newest,
                                label=label_newest,
                                url=url_newest,
                                info=info_newest,
                            )
                            if verbosity > 2:
                                channel(message_header + "\n" + message_body)
                                action = get_response(
                                    message_header,
                                    message_body,
                                    _("Do you want to look for yourself?"),
                                )
                            elif verbosity > 0:
                                channel(message_header + "\n" + message_body)
                        else:
                            if verbosity > 0:
                                channel(ERROR_MESSAGE)
                    # Yes, please open a webpage
                    if action:
                        import webbrowser

                        webbrowser.open(url_newest, new=0, autoraise=True)

                if beta is None:
                    beta = False
                if verbosity is None:
                    verbosity = 1
                if force is None:
                    force = False
                return update_test

            from meerk40t.kernel.kernel import Job

            _job = Job(
                process=update_check(verbosity, beta, force),
                job_name="update_check_job",
                interval=0.01,
                times=1,
                run_main=True,
            )
            context.schedule(_job)

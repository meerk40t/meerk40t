"""
The code inside this module provides routines to look for newer versions of meerk40t on github
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

        # https://docs.github.com/en/rest/reference/repos#get-the-latest-release
        GITHUB_LATEST = "https://api.github.com/repos/meerk40t/meerk40t/releases/latest"
        # https://docs.github.com/en/rest/reference/repos#list-releases
        GITHUB_RELEASES = (
            "https://api.github.com/repos/meerk40t/meerk40t/releases?perpage=100"
        )
        GITHUB_HEADER = ("Accept", "application/vnd.github.v3+json")

        UPDATE_MESSAGE = _(
            "A new {type} release is available:\n"
            + "Version: {name} v{version} ({label})\n"
            + "Url: {url}\n"
            + "Info: {info}"
        )
        NO_UPDATE_MESSAGE = _(
            "You seem to have the latest version.\n"
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
        @context.console_option("verbosity", "p", type=int, help=("Show Info: 0 never, 1 console only, 2 if version found, 3 always"))
        @kernel.console_command(
            "check_for_updates",
            help=_("Check whether a newer version of Meerk40t is available"),
        )
        def check_for_updates(channel, _, beta=None, verbosity=None, **kwargs):
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
                Major, Minor, Release, Beta
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
                        if "what's changed" in line.lower() or "full changelog:" in line.lower() or idx > 6:
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
                if candidate_version is not None:
                    sub_cand = candidate_version[0:3]
                if reference_version is not None:
                    sub_ref = reference_version[0:3]
                # print (sub_cand, sub_ref, bool(sub_cand > sub_ref))
                if sub_cand > sub_ref:
                    is_newer = True
                # print (f"Comparing {candidate_version} vs {reference_version}: {is_newer}")
                return is_newer

            def update_check(verbosity=None, beta=None):
                def update_test(*args):
                    version_current = comparable_version(kernel.version)
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
                    except (HTTPError, URLError):
                        if verbosity > 0:
                            channel(ERROR_MESSAGE)
                        return

                    tag_full = tag_beta = None
                    label_full = label_beta = None
                    version_full = version_beta = version_newest = None
                    url_full = url_beta = None
                    assets_full = assets_beta = None
                    info_full = info_beta = ""

                    response = json.loads(req.read())
                    # print ("Response:")
                    # print (response)
                    something = False
                    if beta:
                        for resp in response:
                            if resp["draft"]:
                                continue
                            tag, version, label, url, assets, rel_info = extract_from_json(resp)
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
                            tag_beta, version_beta, label_beta, url_beta, assets_beta, info_beta = (
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
                    newest_message = ""
                    if newer_version(version_full, version_current):
                        something = True
                        message = UPDATE_MESSAGE.format(
                            type="full",
                            name=kernel.name,
                            version=tag_full,
                            label=label_full,
                            url=url_full,
                            info=info_full,
                        )
                        if verbosity > 0:
                            channel(message)
                        newest_message = message

                    if newer_version(version_beta, version_current):
                        something = True
                        message = UPDATE_MESSAGE.format(
                            type="beta",
                            name=kernel.name,
                            version=tag_beta,
                            label=label_beta,
                            url=url_beta,
                            info=info_beta,
                        )
                        if verbosity > 0:
                            channel(message)
                        newest_message = message
                    if something:
                        # if we have a hit then we brag about it
                        if verbosity > 1:
                            if kernel.yesno(
                                newest_message
                                + "\n"
                                + _("Do you want to go the download page?")
                            ):
                                import webbrowser

                                webbrowser.open(url_newest, new=0, autoraise=True)
                    else:
                        if version_newest is not None:
                            message = NO_UPDATE_MESSAGE.format(
                                name=kernel.name,
                                version=tag_newest,
                                type=type_newest,
                                label=label_newest,
                                url=url_newest,
                                info=info_newest,
                            )
                            if verbosity > 0:
                                channel(message)
                            if verbosity > 2:
                                channel(message)
                                if kernel.yesno(
                                    message + "\n" + _("Do you want to look for yourself?")
                                ):
                                    import webbrowser

                                    webbrowser.open(url_newest, new=0, autoraise=True)
                        else:
                            if verbosity > 0:
                                channel(ERROR_MESSAGE)

                if beta is None:
                    beta = False
                if verbosity is None:
                    verbosity = 1
                return update_test

            kernel.threaded(update_check(verbosity, beta), "update_check")

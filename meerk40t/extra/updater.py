import json
import sys
from urllib.request import urlopen, Request

def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

        # https://docs.github.com/en/rest/reference/repos#get-the-latest-release
        GITHUB_LATEST = "https://api.github.com/repos/meerk40t/meerk40t/releases/latest"
        # https://docs.github.com/en/rest/reference/repos#list-releases
        GITHUB_RELEASES = "https://api.github.com/repos/meerk40t/meerk40t/releases?perpage=100"
        GITHUB_HEADER = ("Accept", "application/vnd.github.v3+json")

        RESET_VERSION = [0, 0, 0, 0]

        UPDATE_MESSAGE = _(
            "A new {type} release of {name} v{version} is available from\n"
            + "{url}"
        )

        context = kernel.root
        context.setting(bool, "check_for_betas", False)

        @kernel.console_command("check_for_updates", help=_("Check whether a newer version is available"))
        def check_for_updates(channel, _, **kwargs):
            """
            This command checks for updates and outputs the results to the console.

            If check_for_betas setting is true
            then we get the release list and iterate through
            to find the latest full and beta releases that are > currently running

            If check_for_betas is false
            but we are currently running a beta
            then we check for a full release > currently running
            and if not then the latest beta > currently running

            If check_for_betas is false
            and we are not currently running a beta
            then we check only for a full release > currently running
            """

            # To-Do: Identify whether we are running from an executable or source
            #        If an executable, then:
            #            Check whether the current executable directory is writeable,
            #            then identify the executable type to download
            #            and if it exists and not already downloaded or if size is different
            #            then download it to the executable directory
            #        Otherwise give the user the Release page url.

            def comparable_version(version):
                """
                Return a comparable sequence from a version string
                """
                src = beta = ""
                if version.startswith("v"):
                    version = version[1:]
                if " " in version:
                    version, src = version.split(" ", 1)
                if "-" in version:
                    version, beta = version.split("-", 1)
                if beta.startswith("beta"):
                    beta = beta[4:]
                if not beta:
                    beta = 9999  # indicates a full version
                else:
                    beta = int(beta)
                version = list(map(int,version.split(".")))
                version.append(beta)
                return version

            def extract_from_json(response):
                tag = response["tag_name"]
                version = comparable_version(tag)
                url = response["html_url"]
                assets = response["assets"]
                return tag, version, url, assets

            def update_check():
                version_current = comparable_version(kernel.version)

                check_for_betas = context.check_for_betas or version_current[3] < 9999
                if check_for_betas:
                    url = GITHUB_RELEASES
                else:
                    url = GITHUB_LATEST

                req = Request(url)
                req.add_header(*GITHUB_HEADER)
                req = urlopen(req)

                running_executable = getattr(sys, "frozen", False)

                tag_full = tag_beta = None
                version_full = version_beta = RESET_VERSION
                url_full = url_beta = None
                assets_full = assets_beta = None

                response = json.loads(req.read())

                if check_for_betas:
                    for resp in response:
                        if resp["draft"]:
                            continue
                        tag, version, url, assets = extract_from_json(resp)
                        if resp["prerelease"]:  # beta
                            if (version > version_beta
                                and (
                                    context.check_for_betas
                                    or (
                                        # If on a temp beta, then only interested in minor beta updates
                                        version[0:2] == version_current[0:2]
                                        and version[3] > version_current[3]
                                    )
                                )
                            ):
                                tag_beta, version_beta, url_beta, assets_beta = tag, version, url, assets
                        elif version > version_full:
                            tag_full, version_full, url_full, assets_full = tag, version, url, assets
                    # If full version is latest, disregard betas
                    if version_full > version_beta:
                        tag_beta, version_beta, url_beta, assets_beta = (None, RESET_VERSION, None, None)
                else:
                    tag_full, version_full, url_full, assets_full = extract_from_json(response)

                if version_full > version_current:
                    channel(
                        UPDATE_MESSAGE.format(
                            type="full",
                            name=kernel.name,
                            version=tag_full,
                            url=url_full
                        )
                    )

                if version_beta > version_current:
                    channel(
                        UPDATE_MESSAGE.format(
                            type="beta",
                            name=kernel.name,
                            version=tag_beta,
                            url=url_beta
                        )
                    )

            kernel.threaded(update_check,"update_check")

"""
Webhelp is a list of websites relevant to the program. This registers a `webhelp` command that will launch a browser
point to the relvant sites.
"""

MEERK40T_ISSUES = "https://github.com/meerk40t/meerk40t/issues"
MEERK40T_HELP = "https://github.com/meerk40t/meerk40t/wiki"
MEERK40T_BEGINNERS = "https://github.com/meerk40t/meerk40t/wiki/Beginners:-0.-Index"
MEERK40T_WEBSITE = "https://github.com/meerk40t/meerk40t"
MEERK40T_RELEASES = "https://github.com/meerk40t/meerk40t/releases"
FACEBOOK_MEERK40T = "https://www.facebook.com/groups/716000085655097"
DISCORD_MEERK40T = "https://discord.gg/vkDD3HdQq6"
MAKERS_FORUM_MEERK40T = "https://forum.makerforums.info/c/k40/meerk40t/120"
IRC_CLIENT = "http://kiwiirc.com/client/irc.libera.chat/meerk40t"
MEERK40T_FEATURE = "https://github.com/meerk40t/meerk40t/discussions/1318"


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

        @kernel.console_argument("page", help=_("Webhelp page"), type=str)
        @kernel.console_command("webhelp", help=_("Launch a registered webhelp page"))
        def webhelp(channel, _, page=None, **kwargs):
            if page is None:
                channel(_("----------"))
                channel(_("Webhelp Registered:"))
                for i, find in enumerate(kernel.find("webhelp")):
                    value, name, suffix = find
                    channel(f"{i + 1}: {str(suffix).ljust(15)} {value}")
                channel(_("----------"))
                return
            try:
                page_num = int(page)
                for i, find in enumerate(kernel.find("webhelp")):
                    if i == page_num:
                        value, name, suffix = find
                        page = value
            except ValueError:
                pass
            value = kernel.lookup("webhelp", page)
            if value is None:
                channel(_("Webhelp not found."))
                return
            value = str(value)
            if not value.startswith("http"):
                channel("bad webhelp")
                return
            import webbrowser

            webbrowser.open(value, new=0, autoraise=True)

        kernel.register("webhelp/help", MEERK40T_HELP)
        kernel.register("webhelp/beginners", MEERK40T_BEGINNERS)
        kernel.register("webhelp/main", MEERK40T_WEBSITE)
        kernel.register("webhelp/issues", MEERK40T_ISSUES)
        kernel.register("webhelp/releases", MEERK40T_RELEASES)
        kernel.register("webhelp/facebook", FACEBOOK_MEERK40T)
        kernel.register("webhelp/discord", DISCORD_MEERK40T)
        kernel.register("webhelp/makers", MAKERS_FORUM_MEERK40T)
        kernel.register("webhelp/irc", IRC_CLIENT)
        kernel.register("webhelp/featurerequest", MEERK40T_FEATURE)

MEERK40T_ISSUES = "https://github.com/meerk40t/meerk40t/issues"
MEERK40T_HELP = "https://github.com/meerk40t/meerk40t/wiki"
MEERK40T_BEGINNERS = "https://github.com/meerk40t/meerk40t/wiki/Beginners:-0.-Index"
MEERK40T_WEBSITE = "https://github.com/meerk40t/meerk40t"
MEERK40T_RELEASES = "https://github.com/meerk40t/meerk40t/releases"
FACEBOOK_MEERK40T = "https://www.facebook.com/groups/716000085655097"
DISCORD_MEERK40T = "https://discord.gg/vkDD3HdQq6"
MAKERS_FORUM_MEERK40T = "https://forum.makerforums.info/c/k40/meerk40t/120"
IRC_CLIENT = "http://kiwiirc.com/client/irc.libera.chat/meerk40t"


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation

        @kernel.console_argument("page", help=_("Webhelp page"), type=str)
        @kernel.console_command("webhelp", help=_("Launch a registered webhelp page"))
        def webhelp(channel, _, page=None, **kwargs):
            if page is None:
                channel(_("----------"))
                channel(_("Webhelp Registered:"))
                for i, name in enumerate(kernel.match("webhelp")):
                    value = kernel.registered[name]
                    name = name.split("/")[-1]
                    channel("%d: %s %s" % (i + 1, str(name).ljust(15), value))
                channel(_("----------"))
                return
            try:
                page_num = int(page)
                for i, name in enumerate(kernel.match("webhelp")):
                    if i == page_num:
                        value = kernel.registered[name]
                        page = value
            except ValueError:
                pass
            key = "webhelp/%s" % page
            if key in kernel.registered:
                value = str(kernel.registered[key])
                if not value.startswith("http"):
                    channel("bad webhelp")
                    return
                import webbrowser

                webbrowser.open(value, new=0, autoraise=True)
            else:
                channel(_("Webhelp not found."))

        kernel.register("webhelp/help", MEERK40T_HELP)
        kernel.register("webhelp/beginners", MEERK40T_BEGINNERS)
        kernel.register("webhelp/main", MEERK40T_WEBSITE)
        kernel.register("webhelp/issues", MEERK40T_ISSUES)
        kernel.register("webhelp/releases", MEERK40T_RELEASES)
        kernel.register("webhelp/facebook", FACEBOOK_MEERK40T)
        kernel.register("webhelp/discord", DISCORD_MEERK40T)
        kernel.register("webhelp/makers", MAKERS_FORUM_MEERK40T)
        kernel.register("webhelp/irc", IRC_CLIENT)

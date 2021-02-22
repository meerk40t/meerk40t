MEERK40T_ISSUES = "https://github.com/meerk40t/meerk40t/issues"
MEERK40T_HELP = "https://github.com/meerk40t/meerk40t/wiki"
MEERK40T_WEBSITE = "https://github.com/meerk40t/meerk40t"


def plugin(kernel, lifecycle):
    if lifecycle == "register":

        @kernel.console_argument("page", help="Webhelp page", type=str)
        @kernel.console_command("webhelp", help="Launch a registered webhelp page")
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
        kernel.register("webhelp/main", MEERK40T_WEBSITE)
        kernel.register("webhelp/issues", MEERK40T_ISSUES)

"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # NOTES COMMANDS
    # ==========
    @self.console_argument("filename", type=str)
    @self.console_command("load", help=_("load <file>"), all_arguments_required=True)
    def file_open(command, channel, _, filename, **kwargs):
        try:
            if self.load(filename):
                channel(_("File loaded {filename}").format(filename=filename))
            else:
                channel(
                    _("Load handler not found: {filename}").format(filename=filename)
                )
        except OSError as e:
            channel(str(e))

    @self.console_command("load_types", help=_("load_types"))
    def file_open_types(command, channel, _, **kwargs):
        for loader, loader_name, sname in kernel.find("load"):
            for description, extensions, mimetype in loader.load_types():
                for ext in extensions:
                    channel(f"{description} ({ext})")

    @self.console_argument("filename", type=str)
    @self.console_option("version", "v", type=str, default="default")
    @self.console_command("save", help=_("save <file>"), all_arguments_required=True)
    def file_save(command, channel, _, filename, version, **kwargs):
        try:
            if self.save(filename, version=version):
                channel(
                    _("File saved {version} {filename}").format(
                        filename=filename, version=version
                    )
                )
            else:
                channel(
                    _("Save handler not found: {version} {filename}").format(
                        filename=filename, version=version
                    )
                )
        except OSError as e:
            channel(str(e))

    @self.console_command("save_types", help=_("save_types"))
    def file_save_types(command, channel, _, **kwargs):
        for saver, save_name, sname in kernel.find("save"):
            for description, extension, mimetype, version in saver.save_types():
                channel(f"{description} ({version}: {extension})")

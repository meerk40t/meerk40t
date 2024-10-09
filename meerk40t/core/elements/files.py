"""
This module provides a set of console commands for managing file operations within the application.
Users can load and save files, as well as retrieve information about supported file types.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up file commands.
- init_commands(kernel): Initializes the file commands and defines the associated operations.
- file_open(command, channel, _, filename, **kwargs): Loads a specified file and reports the result to the user.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    filename: The name of the file to load.
  Returns:
    None
- file_open_types(command, channel, _, **kwargs): Lists the types of files that can be loaded by the application.
  Args:
    command: The command context.
    channel: The communication channel for messages.
  Returns:
    None
- file_save(command, channel, _, filename, version, **kwargs): Saves the current data to a specified file with an optional version.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    filename: The name of the file to save.
    version: The version of the file to save.
  Returns:
    None
- file_save_types(command, channel, _, **kwargs): Lists the types of files that can be saved by the application.
  Args:
    command: The command context.
    channel: The communication channel for messages.
  Returns:
    None
- file_autoexec(command, channel, _, **kwargs): Executes a list of startup commands defined in the last loaded file.
  Args:
    command: The command context.
    channel: The communication channel for messages.
  Returns:
    None
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

    @self.console_command("file_startup", help=_("Execute file startup command list"))
    def file_autoexec(command, channel, _, **kwargs):
        if self.last_file_autoexec:
            commands = self.last_file_autoexec.split("\n")
            for command in commands:
                command = command.strip()
                if len(command) == 0:
                    continue
                if command.startswith("#"):
                    channel(command)
                else:
                    self(command + "\n")
        else:
            channel("No commands defined")

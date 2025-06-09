"""
This module provides console commands for managing notes within the application. Users can set, retrieve, and append notes, allowing for easy tracking of information.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up note commands.
- init_commands(kernel): Initializes the note commands and defines the associated operations.
- note(command, channel, _, append=False, remainder=None, **kwargs): Sets or retrieves the current note. If a note is provided, it can either replace the existing note or be appended to it.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    append: A flag indicating whether to append to the existing note.
    remainder: The note text to set or append.
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
    @self.console_option("append", "a", type=bool, action="store_true", default=False)
    @self.console_command("note", help=_("note <note>"))
    def note(command, channel, _, append=False, remainder=None, **kwargs):
        _note = remainder
        if _note is None:
            if self.note is None:
                channel(_("No Note."))
            else:
                channel(str(self.note))
        else:
            if append:
                self.note += "\n" + _note
            else:
                self.note = _note
            self.signal("note", self.note)
            channel(_("Note Set."))
            channel(str(self.note))

    # --------------------------- END COMMANDS ------------------------------

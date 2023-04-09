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

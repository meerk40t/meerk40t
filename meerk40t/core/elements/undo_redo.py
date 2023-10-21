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
    # UNDO/REDO COMMANDS
    # ==========
    @self.console_command(
        "save_restore_point",
    )
    def undo_mark(data=None, **kwgs):
        self.undo.mark()

    @self.console_command(
        "undo",
    )
    def undo_undo(command, channel, _, **kwgs):
        if not self.undo.undo():
            # At bottom of stack.
            channel("No undo available.")
            return
        self.validate_selected_area()
        channel(f"Undo: {self.undo}")
        self.signal("refresh_scene", "Scene")
        self.signal("rebuild_tree")

    @self.console_command(
        "redo",
    )
    def undo_redo(command, channel, _, data=None, **kwgs):
        if not self.undo.redo():
            channel("No redo available.")
            return
        channel(f"Redo: {self.undo}")
        self.validate_selected_area()
        self.signal("refresh_scene", "Scene")
        self.signal("rebuild_tree")

    @self.console_command(
        "undolist",
    )
    def undo_list(command, channel, _, **kwgs):
        for entry in self.undo.undolist():
            channel(entry)

    # --------------------------- END COMMANDS ------------------------------

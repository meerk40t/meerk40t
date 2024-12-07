"""
This module provides a set of console commands for managing undo and redo operations within the application.
These commands allow users to mark restore points, undo actions, redo actions, and list the available undo operations.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up undo/redo commands.
- init_commands(kernel): Initializes the undo/redo commands and defines the associated operations.
- undo_mark(data=None, message=None, **kwgs): Marks a restore point in the undo stack with an optional message.
  Args:
    data: Additional data for the command (not used).
    message: A message to associate with the restore point.
- undo_undo(command, channel, _, **kwgs): Performs the undo operation, reverting the last action.
  Args:
    command: The command context.
    channel: The communication channel for messages.
- undo_redo(command, channel, _, data=None, **kwgs): Performs the redo operation, reapplying the last undone action.
  Args:
    command: The command context.
    channel: The communication channel for messages.
    data: Additional data for the command (not used).
- undo_list(command, channel, _, **kwgs): Lists all available undo operations in the stack.
  Args:
    command: The command context.
    channel: The communication channel for messages.
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
    @self.console_argument("message", type=str, default=None)
    @self.console_command(
        "save_restore_point",
    )
    def undo_mark(data=None, message=None, **kwgs):
        self.undo.mark(message)

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

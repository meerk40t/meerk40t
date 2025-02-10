"""
This module clipboard operations provides a set of console commands for managing clipboard operations
within the elements system of the application. application.
It allows the user to copy, cut, paste, and clear elements, as well to as manage clipboard contents and settings.

Functions:
- plugin(kernel, lifecycle=None): Initializes the plugin and sets up copy, clipboard commands.
- init_commands(kernel): cut, paste, and clear Initializes the clipboard commands and defines elements, as well as manage clipboard contents.
"""

from copy import copy

from meerk40t.core.units import Length
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    # ==========
    # CLIPBOARD COMMANDS
    # ==========
    @self.console_option("name", "n", type=str)
    @self.console_command(
        "clipboard",
        help=_("clipboard"),
        input_type=(None, "elements"),
        output_type="clipboard",
    )
    def clipboard_base(data=None, name=None, **kwargs):
        """
        Clipboard commands. Applies to current selected elements to
        make a copy of those elements. Paste a copy of those elements
        or cut those elements. Clear clears the clipboard.

        The list command will list them but this is only for debug.
        """
        if name is not None:
            self._clipboard_default = name
        if data is None:
            return "clipboard", list(self.elems(emphasized=True))
        else:
            return "clipboard", data

    @self.console_command(
        "copy",
        help=_("clipboard copy"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_copy(data=None, **kwargs):
        destination = self._clipboard_default
        self._clipboard[destination] = []
        for e in data:
            copy_node = copy(e)
            # Need to add stroke and fill, as copy will take the
            # default values for these attributes
            options = ["fill", "stroke", "wxfont"]
            for prop in dir(e):
                if prop.startswith("mk"):
                    options.append(prop)
            for optional in options:
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))
            self._clipboard[destination].append(copy_node)
        # Let the world know we have filled the clipboard
        self.signal("icons")
        return "elements", self._clipboard[destination]

    @self.console_option("dx", "x", help=_("paste offset x"), type=Length, default=0)
    @self.console_option("dy", "y", help=_("paste offset y"), type=Length, default=0)
    @self.console_command(
        "paste",
        help=_("clipboard paste"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_paste(
        command, channel, _, data=None, post=None, dx=None, dy=None, **kwargs
    ):
        destination = self._clipboard_default
        pasted = []
        try:
            for e in self._clipboard[destination]:
                copy_node = copy(e)
                if copy_node is None:
                    channel(_("Error: clipboard empty node"))
                    continue
                # Need to add stroke and fill, as copy will take the
                # default values for these attributes
                options = ["fill", "stroke", "wxfont"]
                for optional in options:
                    if hasattr(e, optional):
                        setattr(copy_node, optional, getattr(e, optional))
                hadoptional = False
                options = []
                for prop in dir(e):
                    if prop.startswith("mk"):
                        options.append(prop)
                for optional in options:
                    if hasattr(e, optional):
                        setattr(copy_node, optional, getattr(e, optional))
                        hadoptional = True

                if hadoptional:
                    for property_op in self.kernel.lookup_all("path_updater/.*"):
                        property_op(self.kernel.root, copy_node)

                pasted.append(copy_node)
        except (TypeError, KeyError):
            channel(_("Error: Clipboard Empty"))
            return
        if len(pasted) == 0:
            channel(_("Error: Clipboard Empty"))
            return

        if dx is not None:
            dx = float(dx)
        else:
            dx = 0
        if dy is not None:
            dy = float(dy)
        else:
            dy = 0
        if dx != 0 or dy != 0:
            matrix = Matrix.translate(dx, dy)
            for node in pasted:
                node.matrix *= matrix
        # _("Clipboard paste")
        with self.undoscope("Clipboard paste"):
            if len(pasted) > 1:
                group = self.elem_branch.add(type="group", label="Group", id="Copy", expanded=True)
            else:
                group = self.elem_branch
            target = []
            for p in pasted:
                if hasattr(p, "label"):
                    s = "Copy" if p.label is None else f"{p.display_label()} (copy)"
                    p.label = s
                group.add_node(p)
                target.append(p)
        # Make sure we are selecting the right thing...
        if len(pasted) > 1:
            self.set_emphasis([group])
        else:
            self.set_emphasis(target)

        self.signal("refresh_tree", group)
        # Newly created! Classification needed?
        post.append(classify_new(pasted))
        return "elements", pasted

    @self.console_command(
        "cut",
        help=_("clipboard cut"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_cut(data=None, **kwargs):
        destination = self._clipboard_default
        self._clipboard[destination] = []
        for e in data:
            copy_node = copy(e)
            options = ["fill", "stroke", "wxfont"]
            for prop in dir(e):
                if prop.startswith("mk"):
                    options.append(prop)
            for optional in options:
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))
            self._clipboard[destination].append(copy_node)
        # _("Clipboard cut")
        with self.undoscope("Clipboard cut"):
            self.remove_elements(data)
        # Let the world know we have filled the clipboard
        self.signal("icons")
        return "elements", self._clipboard[destination]

    @self.console_command(
        "clear",
        help=_("clipboard clear"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_clear(data=None, **kwargs):
        destination = self._clipboard_default
        try:
            old = self._clipboard[destination]
        except KeyError:
            old = None
        self._clipboard[destination] = None
        return "elements", old

    @self.console_command(
        "contents",
        help=_("clipboard contents"),
        input_type="clipboard",
        output_type="elements",
    )
    def clipboard_contents(**kwargs):
        destination = self._clipboard_default
        return "elements", self._clipboard[destination]

    @self.console_command(
        "list",
        help=_("clipboard list"),
        input_type="clipboard",
    )
    def clipboard_list(command, channel, _, **kwargs):
        for v in self._clipboard:
            k = self._clipboard[v]
            channel(f"{str(v).ljust(5)}: {str(k)}")
        try:
            num = len(self._clipboard[self._clipboard_default])
        except (TypeError, KeyError):
            num = 0
        channel(_("Clipboard-Entries: {index}").format(index=num))

    # --------------------------- END COMMANDS ------------------------------

"""
Group management functionality for MeerK40t.

This module provides console commands and functions for grouping, ungrouping,
and simplifying groups of elements in the MeerK40t laser processing system.
"""


def plugin(kernel, lifecycle=None):
    """
    Plugin initialization for group management functionality.

    Args:
        kernel: The MeerK40t kernel instance
        lifecycle: The lifecycle stage for plugin initialization
    """
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def filter_redundant_ancestors(nodes):
    """
    Filter out nodes whose ancestors are also in the list.

    If the selection contains both an ancestor and one (or more) of its descendants,
    only keep the ancestor.

    This check serves two purposes:
    1. Logical Consistency: It prevents "flattening" the structure. If we grouped both
       GroupA and its ChildB, ChildB would be moved out of GroupA into the new group,
       becoming a sibling of GroupA. We want to preserve the hierarchy.
    2. Redundancy: While node.append_child() now has built-in cycle prevention,
       this filter avoids attempting operations that are structurally redundant.

    Args:
        nodes: List of nodes to filter

    Returns:
        List of nodes with redundant descendants removed
    """
    if not nodes:
        return []

    treat_set = set(nodes)
    filtered = []
    for node in nodes:
        ancestor = node.parent
        redundant = False
        while ancestor is not None:
            if ancestor in treat_set:
                redundant = True
                break
            ancestor = ancestor.parent
        if not redundant:
            filtered.append(node)
    return filtered


def init_commands(kernel):
    """
    Initialize console commands for group operations.

    Args:
        kernel: The MeerK40t kernel instance
    """
    self = kernel.elements

    _ = kernel.translation

    classify_new = self.post_classify

    def get_group_data(data) -> list:
        """
        Extract group and file nodes from the provided data, filtering out
        nodes whose ancestors are already in the data to avoid double processing.

        Args:
            data: List of nodes to process, or None to use emphasized elements

        Returns:
            List of group and file nodes that should be processed
        """
        if data is None:
            data = list(self.elems_nodes(emphasized=True))
        if len(data) == 0:
            return []
        # Establish the parent group/file nodes to ungroup.
        to_treat = []
        for node in data:
            if node.type in ("group", "file"):
                # Let's establish whether the group/files (grand)parent
                # is also in the data.
                # If that's the case, we don't need to treat this group/file now.
                present = False
                ancestor = node.parent
                while ancestor is not None:
                    if ancestor in data:
                        present = True
                        break
                    ancestor = ancestor.parent
                if not present and node not in to_treat:
                    to_treat.append(node)
        return to_treat

    @self.console_option(
        "reparent",
        "r",
        type=bool,
        help=_("Reparent grouped elements to the root"),
        action="store_true",
    )
    @self.console_argument("label", type=str, help=_("Label of the group"))
    @self.console_command(
        "group",
        help=_("group selected elements"),
        input_type=(None, "elements"),
        output_type=None,
    )
    def group_elements(
        command,
        channel,
        _,
        label=None,
        data=None,
        reparent=False,
        post=None,
        **kwargs,
    ):
        """
        Group selected elements into a new group node.

        Args:
            command: The console command that triggered this function
            channel: The output channel for messages
            _: Translation function (unused)
            label: Optional label for the new group
            data: Elements to group, or None to use emphasized elements
            reparent: If True, reparent grouped elements to root instead of condensing
            post: Post-processing function (unused)
            **kwargs: Additional keyword arguments
        """

        def condensed_set(data):
            """
            Condense the data by replacing groups where all children are selected
            with the parent group node to avoid redundant nesting.

            Args:
                data: List of nodes to condense

            Returns:
                List of condensed nodes with redundant group children
                removed
            """
            # Condense the data in the sense, that if for a given node, we see that it belongs
            # to a group and all other children of that group are part of the set too,
            # then we will replace those nodes by the parent group node.
            data_set = set(data)
            parent_map = {}
            # collect selected children per group‐parent
            for node in data:
                p = node.parent
                if p and p.type == "group":
                    parent_map.setdefault(p, []).append(node)

            new_data = []
            for node in data:
                p = node.parent
                # if we selected all children, replace them with the parent
                if p in parent_map and len(parent_map[p]) == len(p.children):
                    if p not in new_data:
                        new_data.append(p)
                else:
                    new_data.append(node)

            if set(new_data) != data_set:
                return condensed_set(new_data)
            return new_data

        if data is None:
            data = list(self.elems_nodes(emphasized=True))
        if reparent:
            to_treat = [n for n in data if n.type not in ("file", "group")]
        else:
            to_treat = condensed_set(data)

        to_treat = filter_redundant_ancestors(to_treat)
        if not to_treat:
            channel(_("Nothing to group."))
            return

        def minimal_parent(data):
            """
            Find the minimal common parent for a set of nodes to determine
            where to place the new group.

            Args:
                data: List of nodes to find common parent for

            Returns:
                The node that should be the parent of the new group
            """
            result = None
            root = self.elem_branch
            curr_level = None
            for node in data:
                plevel = 0
                candidate = node.parent
                while candidate is not None and candidate.parent is not root:
                    candidate = candidate.parent
                    plevel += 1
                if curr_level is None or plevel < curr_level:
                    curr_level = plevel
                    result = node.parent
                if plevel == 0:
                    # No need to continue
                    break
            if result is None:
                result = root
            return result

        # _("Group elements")
        with self.undoscope("Group elements"):
            with self.node_lock:
                parent_node = minimal_parent(to_treat)
                label = label if label is not None else "Group"
                group_node = parent_node.add(type="group", label=label, expanded=True)
                group_node.append_children(to_treat, fast=True)
                channel(_("Grouped {count} elements.").format(count=len(data)))
                classify_new(group_node)
        self.signal("rebuild_tree", "elements")

    @self.console_command(
        "ungroup",
        help=_("ungroup selected elements"),
        input_type=(None, "elements"),
        output_type=None,
    )
    def group_release(
        command,
        channel,
        _,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Ungroup selected elements by moving children of groups/files to their parent level.

        Args:
            command: The console command that triggered this function
            channel: The output channel for messages
            _: Translation function (unused)
            data: Elements to ungroup, or None to use emphasized elements
            post: Post-processing function (unused)
            **kwargs: Additional keyword arguments
        """
        to_treat = get_group_data(data)
        if len(to_treat) == 0:
            channel(_("No group or file selected."))
            return
        # Translation hint ("Ungroup elements")
        with self.undoscope("Ungroup elements"):
            with self.node_lock:
                for gnode in to_treat:
                    gnode.insert_siblings(list(gnode.children), below=False, fast=True)
                    gnode.remove_node()  # Removing group/file node.
        self.signal("rebuild_tree", "elements")

    @self.console_command(
        "simplify-group",
        help=_("Unlevel groups if they just contain another group"),
        input_type=(None, "elements"),
        output_type=None,
    )
    def group_simplify(
        command,
        channel,
        _,
        data=None,
        post=None,
        **kwargs,
    ):
        """
        Simplify group structure by removing unnecessary nesting levels.
        Groups that contain only one child group are flattened.

        Args:
            command: The console command that triggered this function
            channel: The output channel for messages
            _: Translation function (unused)
            data: Elements to simplify, or None to use emphasized elements
            post: Post-processing function (unused)
            **kwargs: Additional keyword arguments
        """
        to_treat = get_group_data(data)
        if len(to_treat) == 0:
            channel(_("No group or file selected."))
            return

        def straighten(snode):
            """
            Recursively flatten unnecessary group nesting in a node.

            Args:
                snode: The node to straighten

            Returns:
                Number of nodes that were removed during straightening
            """
            amount = 0
            needs_repetition = True
            while needs_repetition:
                needs_repetition = False
                cl = list(snode.children)
                if not cl:
                    # No Children? Remove
                    amount = 1
                    snode.remove_node()
                elif len(cl) == 1:
                    gnode = cl[0]
                    if gnode is not None and gnode.type == "group":
                        gnode.insert_siblings(list(gnode.children), fast=True)
                        gnode.remove_node()  # Removing group/file node.
                        needs_repetition = True
                else:
                    for n in cl:
                        if n is not None and n.type == "group":
                            fnd = straighten(n)
                            amount += fnd
            return amount

        # _("Simplify group")
        with self.undoscope("Simplify group"):
            res = 0
            for node in to_treat:
                with self.node_lock:
                    res += straighten(node)
        channel(
            _(
                "Simplified {count} groups. Removed {removed} unnecessary group levels."
            ).format(count=len(to_treat), removed=res)
        )
        if res > 0:
            self.signal("rebuild_tree", "elements")

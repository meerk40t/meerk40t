"""
This is a giant list of console commands that deal with and often implement the elements system in the program.
"""


from meerk40t.kernel import CommandSyntaxError

from .element_types import *


def plugin(kernel, lifecycle=None):
    _ = kernel.translation
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    self = kernel.elements

    _ = kernel.translation

    # ==========
    # TREE BASE
    # ==========
    @self.console_command(
        "tree", help=_("access and alter tree elements"), output_type="tree"
    )
    def tree(**kwargs):
        return "tree", [self._tree]

    @self.console_command(
        "bounds", help=_("view tree bounds"), input_type="tree", output_type="tree"
    )
    def tree_bounds(command, channel, _, data=None, **kwargs):
        if data is None:
            data = [self._tree]

        def b_list(path, node):
            for i, n in enumerate(node.children):
                p = list(path)
                p.append(str(i))
                channel(
                    f"{'.'.join(p).ljust(10)}: {str(n._bounds)} - {str(n._bounds_dirty)} {str(n.type)} - {str(str(n)[:16])}"
                )
                b_list(p, n)

        for d in data:
            channel("----------")
            if d.type == "root":
                channel(_("Tree:"))
            else:
                channel(f"{str(d)}:")
            b_list([], d)
            channel("----------")

        return "tree", data

    @self.console_command(
        "list", help=_("view tree"), input_type="tree", output_type="tree"
    )
    def tree_list(command, channel, _, data=None, **kwargs):
        if data is None:
            data = [self._tree]

        def t_list(path, node):
            for i, n in enumerate(node.children):
                p = list(path)
                p.append(str(i))
                if n.targeted:
                    j = "+"
                elif n.emphasized:
                    j = "~"
                elif n.highlighted:
                    j = "-"
                else:
                    j = ":"
                channel(f"{'.'.join(p).ljust(10)}{j} {str(n.type)} - {str(n.label)}")
                t_list(p, n)

        for d in data:
            channel("----------")
            if d.type == "root":
                channel(_("Tree:"))
            else:
                channel(f"{d.label}:")
            t_list([], d)
            channel("----------")

        return "tree", data

    @self.console_argument("drag", help="Drag node address")
    @self.console_argument("drop", help="Drop node address")
    @self.console_command(
        "dnd", help=_("Drag and Drop Node"), input_type="tree", output_type="tree"
    )
    def tree_dnd(command, channel, _, data=None, drag=None, drop=None, **kwargs):
        """
        Drag and Drop command performs a console based drag and drop operation
        E.g. "tree dnd 0.1 0.2" will drag node 0.1 into node 0.2
        """
        if data is None:
            data = [self._tree]
        if drop is None:
            raise CommandSyntaxError
        with self.static("tree_dnd"):
            try:
                drag_node = self._tree
                for n in drag.split("."):
                    drag_node = drag_node.children[int(n)]
                drop_node = self._tree
                for n in drop.split("."):
                    drop_node = drop_node.children[int(n)]
                drop_node.drop(drag_node)
            except (IndexError, AttributeError, ValueError):
                raise CommandSyntaxError
        return "tree", data

    @self.console_argument("node", help="Node address for menu")
    @self.console_argument("execute", help="Command to execute")
    @self.console_command(
        "menu",
        help=_("Load menu for given node"),
        input_type="tree",
        output_type="tree",
    )
    def tree_menu(command, channel, _, data=None, node=None, execute=None, **kwargs):
        """
        Create menu for a particular node.
        Processes submenus, references, radio_state and check_state as needed.
        """
        try:
            menu_node = self._tree
            for n in node.split("."):
                menu_node = menu_node.children[int(n)]
        except (IndexError, AttributeError, ValueError):
            raise CommandSyntaxError

        menu = []
        submenus = {}

        def menu_functions(f, cmd_node):
            func_dict = dict(f.func_dict)

            def specific(event=None):
                f(cmd_node, **func_dict)

            return specific

        from meerk40t.core.treeop import get_tree_operation_for_node

        tree_operations_for_node = get_tree_operation_for_node(self)
        for func in tree_operations_for_node(menu_node):
            submenu_name = func.submenu
            submenu = None
            if submenu_name in submenus:
                submenu = submenus[submenu_name]
            elif submenu_name is not None:
                submenu = list()
                menu.append((submenu_name, submenu))
                submenus[submenu_name] = submenu

            menu_context = submenu if submenu is not None else menu
            if func.reference is not None:
                pass
            if func.radio_state is not None:
                if func.separate_before:
                    menu_context.append(("------", None))
                n = func.real_name
                if func.radio_state:
                    n = "✓" + n
                menu_context.append((n, menu_functions(func, menu_node)))
            else:
                if func.separate_before:
                    menu_context.append(("------", None))
                n = func.real_name
                if hasattr(func, "check_state") and func.check_state:
                    n = "✓" + n
                menu_context.append((n, menu_functions(func, menu_node)))
            if func.separate_after:
                menu_context.append(("------", None))
        if execute is not None:
            try:
                execute_command = ("menu", menu)
                for n in execute.split("."):
                    name, cmd = execute_command
                    execute_command = cmd[int(n)]
                name, cmd = execute_command
                channel(f"Executing {name}: {str(cmd)}")
                cmd()
            except (IndexError, AttributeError, ValueError, TypeError):
                raise CommandSyntaxError
        else:

            def m_list(path, _menu):
                for i, _n in enumerate(_menu):
                    p = list(path)
                    p.append(str(i))
                    _name, _submenu = _n
                    channel(f"{'.'.join(p).ljust(10)}: {str(_name)}")
                    if isinstance(_submenu, list):
                        m_list(p, _submenu)

            m_list([], menu)

        return "tree", data

    @self.console_command(
        "selected",
        help=_("delegate commands to focused value"),
        input_type="tree",
        output_type="tree",
    )
    def selected(channel, _, **kwargs):
        """
        Set tree list to selected node
        """
        # print ("selected")
        # for n in self.flat():
        #     print ("Node: %s, selected=%s, emphasized=%s" % (n.type, n.selected, n.emphasized))
        return "tree", list(self.flat(selected=True))

    @self.console_command(
        "emphasized",
        help=_("delegate commands to focused value"),
        input_type="tree",
        output_type="tree",
    )
    def emphasized(channel, _, **kwargs):
        """
        Set tree list to emphasized node
        """
        return "tree", list(self.flat(emphasized=True))

    @self.console_command(
        "highlighted",
        help=_("delegate commands to sub-focused value"),
        input_type="tree",
        output_type="tree",
    )
    def highlighted(channel, _, **kwargs):
        """
        Set tree list to highlighted nodes
        """
        return "tree", list(self.flat(highlighted=True))

    @self.console_command(
        "targeted",
        help=_("delegate commands to sub-focused value"),
        input_type="tree",
        output_type="tree",
    )
    def targeted(channel, _, **kwargs):
        """
        Set tree list to highlighted nodes
        """
        return "tree", list(self.flat(targeted=True))

    @self.console_command(
        "delete",
        help=_("delete the given nodes"),
        input_type="tree",
        output_type="tree",
    )
    def delete(channel, _, data=None, **kwargs):
        """
        Delete nodes.
        Structural nodes such as root, elements branch, and operations branch are not able to be deleted
        """
        # This is an unusually dangerous operation, so if we have multiple node types, like ops + elements
        # then we would 'only' delete those where we have the least danger, so that regmarks < operations < elements
        if len(data) == 0:
            channel(_("Nothing to delete"))
            return
        # print ("Delete called with data:")
        # for n in data:
        #     print ("Node: %s, sel=%s, emp=%s" % (n.type, n.selected, n.emphasized))
        typecount = [0, 0, 0, 0, 0]
        todelete = [[], [], [], [], []]
        nodetypes = ("Operations", "References", "Elements", "Regmarks", "Branches")
        regmk = list(self.regmarks())
        for node in data:
            if node.type in op_nodes:
                typecount[0] += 1
                todelete[0].append(node)
            elif node.type == "reference":
                typecount[1] += 1
                todelete[1].append(node)
            elif node.type in elem_group_nodes:
                if node in regmk:
                    typecount[3] += 1
                    todelete[3].append(node)
                else:
                    if hasattr(node, "lock") and node.lock:
                        # Don't delete locked nodes
                        continue
                    typecount[2] += 1
                    todelete[2].append(node)
            else:  # branches etc...
                typecount[4] += 1
        # print ("Types: ops=%d, refs=%d, elems=%d, regmarks=%d, branches=%d" %
        #     (typecount[0], typecount[1], typecount[2], typecount[3], typecount[4]))
        single = False
        if (
            typecount[0] > 0
            and typecount[1] == 0
            and typecount[2] == 0
            and typecount[3] == 0
        ):
            single = True
            entry = 0
        elif (
            typecount[1] > 0
            and typecount[0] == 0
            and typecount[2] == 0
            and typecount[3] == 0
        ):
            single = True
            entry = 1
        elif (
            typecount[2] > 0
            and typecount[0] == 0
            and typecount[1] == 0
            and typecount[3] == 0
        ):
            single = True
            entry = 2
        elif (
            typecount[3] > 0
            and typecount[0] == 0
            and typecount[1] == 0
            and typecount[2] == 0
        ):
            single = True
            entry = 3
        if not single:
            if typecount[3] > 0:
                # regmarks take precedence, the least dangereous delete
                entry = 3
            elif typecount[1] > 0:
                # refs next
                entry = 1
            elif typecount[0] > 0:
                # ops next
                entry = 0
            else:
                # Not sure why and when this supposed to happen?
                entry = 2
            channel(
                _(
                    "There were nodes across operations ({c1}), assignments ({c2}), elements ({c3}) and regmarks ({c4})."
                ).format(
                    c1=typecount[0],
                    c2=typecount[1],
                    c3=typecount[2],
                    c4=typecount[3],
                )
                + "\n"
                + _("Only nodes of type {nodetype} were deleted.").format(
                    nodetype=nodetypes[entry]
                )
                + "\n"
                + _(
                    "If you want to remove all nodes regardless of their type, consider: 'tree selected remove'"
                )
            )
        # print ("Want to delete %d" % entry)
        # for n in todelete[entry]:
        #     print ("Node to delete: %s" % n.type)
        with self.static("delete"):
            self.remove_nodes(todelete[entry])
            self.validate_selected_area()
        self.signal("refresh_scene", "Scene")
        return "tree", [self._tree]

    @self.console_command(
        "remove",
        help=_("forcefully deletes all given nodes"),
        input_type="tree",
        output_type="tree",
    )
    def remove(channel, _, data=None, **kwargs):
        """
        Delete nodes.
        Structural nodes such as root, elements branch, and operations branch are not able to be deleted
        """
        # This is an unusually dangerous operation, so if we have multiple node types, like ops + elements
        # then we would 'only' delete those where we have the least danger, so that regmarks < operations < elements
        with self.static("remove"):
            self.remove_nodes(data)
        self.signal("refresh_scene", "Scene")
        return "tree", [self._tree]

    @self.console_command(
        "delegate",
        help=_("delegate commands to focused value"),
        input_type="tree",
        output_type=("op", "elements"),
    )
    def delegate(channel, _, **kwargs):
        """
        Delegate to either ops or elements depending on the current node emphasis
        """
        for item in self.flat(emphasized=True):
            if item.type.startswith("op"):
                return "ops", list(self.ops(emphasized=True))
            if item.type in elem_nodes or item.type in ("group", "file"):
                return "elements", list(self.elems(emphasized=True))

    # --------------------------- END COMMANDS ------------------------------

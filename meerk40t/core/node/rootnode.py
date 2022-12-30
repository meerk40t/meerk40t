from meerk40t.core.node.node import Node


class RootNode(Node):
    """
    RootNode is one of the few directly declarable node-types and serves as the base type for all Node classes.

    The notifications are shallow. They refer *only* to the node in question, not to any children or parents.
    """

    def __init__(self, context, **kwargs):
        _ = context._
        super(RootNode, self).__init__(type="root", **kwargs)
        self._root = self
        self.context = context
        self.listeners = []
        self.add(type="branch ops", label=_("Operations"))
        self.add(type="branch elems", label=_("Elements"))
        self.add(type="branch reg", label=_("Regmarks"))

    def __repr__(self):
        return f"RootNode({str(self.context)})"

    def __copy__(self):
        return RootNode(self.context)

    def is_draggable(self):
        return False

    def listen(self, listener):
        self.listeners.append(listener)

    def unlisten(self, listener):
        self.listeners.remove(listener)

    def notify_created(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_created"):
                listen.node_created(node, **kwargs)

    def notify_destroyed(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_destroyed"):
                listen.node_destroyed(node, **kwargs)

    def notify_attached(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_attached"):
                listen.node_attached(node, **kwargs)

    def notify_detached(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_detached"):
                listen.node_detached(node, **kwargs)

    def notify_changed(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "node_changed"):
                listen.node_changed(node, **kwargs)

    def notify_selected(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "selected"):
                listen.selected(node, **kwargs)

    def notify_emphasized(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "emphasized"):
                listen.emphasized(node, **kwargs)

    def notify_targeted(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "targeted"):
                listen.targeted(node, **kwargs)

    def notify_highlighted(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "highlighted"):
                listen.highlighted(node, **kwargs)

    def notify_modified(self, node=None, **kwargs):
        """
        Notifies any listeners that a value in the tree has been changed such that the matrix or other property
        values have changed. But that the underlying data object itself remains intact.
        @param node: node that was modified.
        @param kwargs:
        @return:
        """
        if node is None:
            node = self
        self._bounds = None
        for listen in self.listeners:
            if hasattr(listen, "modified"):
                listen.modified(node, **kwargs)

    def notify_altered(self, node=None, **kwargs):
        """
        Notifies any listeners that a value in the tree has had its underlying data fundamentally changed and while
        this may not be reflected by the properties any assumptions about the content of this node are no longer
        valid.

        @param node:
        @param kwargs:
        @return:
        """
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "altered"):
                listen.altered(node, **kwargs)

    def notify_expand(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "expand"):
                listen.expand(node, **kwargs)

    def notify_collapse(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "collapse"):
                listen.collapse(node, **kwargs)

    def notify_reorder(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "reorder"):
                listen.reorder(node, **kwargs)

    def notify_update(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "update"):
                listen.update(node, **kwargs)

    def notify_focus(self, node=None, **kwargs):
        if node is None:
            node = self
        for listen in self.listeners:
            if hasattr(listen, "focus"):
                listen.focus(node, **kwargs)

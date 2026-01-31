from meerk40t.core.node.node import Node


class DummyLock:
    """Dummy lock that does nothing - for compatibility when no real locking is needed."""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class RootNode(Node):
    """
    RootNode is one of the few directly declarable node-types and serves as the base type for all Node classes.

    The notifications are shallow. They refer *only* to the node in question, not to any children or parents.

    RootNode enforces a strict structure: it only accepts children with types starting with "branch".
    """

    def __init__(self, context, **kwargs):
        _ = context._
        super().__init__(type="root", **kwargs)
        self._root = self
        self.listeners = []
        self.context = context
        self.pause_notify = False
        # Dummy lock that can be overridden by Elements with a real threading.RLock
        self.node_lock = DummyLock()
        # Flag indicating the tree structure changed; listeners may set this
        # and services can invalidate caches lazily.
        self._structure_dirty = False
        self.add(type="branch ops", label=_("Operations"))
        self.add(type="branch elems", label=_("Elements"))
        self.add(type="branch reg", label=_("Regmarks"))

    def __repr__(self):
        return f"RootNode({str(self.context)})"

    def __copy__(self):
        return RootNode(self.context)

    def is_draggable(self):
        return False

    def validate_child(self, child):
        """
        Enforces that only branch nodes can be added directly to the root.
        """
        if not child.type.startswith("branch"):
            return False
        return True

    def listen(self, listener):
        self.listeners.append(listener)

    def unlisten(self, listener):
        self.listeners.remove(listener)

    def notify_frozen(self, status):
        # Tells the listener that an update of its visual apperance is not necessary
        for listen in self.listeners:
            if hasattr(listen, "frozen"):
                listen.frozen(status)

    def notify_created(self, node=None, **kwargs):
        if node is None:
            node = self
        # Mark structure dirty for lazy cache invalidation
        with self.node_lock:
            try:
                self._structure_dirty = True
            except Exception:
                pass
        # If notification delivery is paused, do not dispatch per-node events.
        if getattr(self, "pause_notify", False):
            return
        for listen in self.listeners:
            if hasattr(listen, "node_created"):
                listen.node_created(node, **kwargs)

    def notify_destroyed(self, node=None, **kwargs):
        if node is None:
            node = self
        # Mark structure dirty for lazy cache invalidation
        with self.node_lock:
            try:
                self._structure_dirty = True
            except Exception:
                pass
        if getattr(self, "pause_notify", False):
            return
        for listen in self.listeners:
            if hasattr(listen, "node_destroyed"):
                listen.node_destroyed(node, **kwargs)

    def notify_attached(self, node=None, **kwargs):
        if node is None:
            node = self
        # Mark structure dirty for lazy cache invalidation
        with self.node_lock:
            try:
                self._structure_dirty = True
            except Exception:
                pass
        if getattr(self, "pause_notify", False):
            return
        for listen in self.listeners:
            if hasattr(listen, "node_attached"):
                listen.node_attached(node, **kwargs)

    def notify_detached(self, node=None, **kwargs):
        if node is None:
            node = self
        # Mark structure dirty for lazy cache invalidation
        with self.node_lock:
            try:
                self._structure_dirty = True
            except Exception:
                pass
        if getattr(self, "pause_notify", False):
            return
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

    def notify_translated(self, node=None, dx=0, dy=0, interim=False, **kwargs):
        """
        Notifies any listeners that a value in the tree has been changed such that the matrix or other property
        values have changed. But that the underlying data object itself remains intact.
        @param node: node that was modified.
        @param dx: translation change for node
        @param dy: translation change for node
        @param kwargs:
        @return:
        """
        if node is None:
            node = self
        if self._bounds is not None:
            self._bounds = [
                self._bounds[0] + dx,
                self._bounds[1] + dy,
                self._bounds[2] + dx,
                self._bounds[3] + dy,
            ]
        for listen in self.listeners:
            if hasattr(listen, "translated"):
                listen.translated(node, dx=dx, dy=dy, interim=interim)  # , **kwargs)

    def notify_scaled(self, node=None, sx=1, sy=1, ox=0, oy=0, interim=False, **kwargs):
        """
        Notifies any listeners that a value in the tree has been changed such that the matrix or other property
        values have changed. But that the underlying data object itself remains intact.

        @param node: node that was modified.
        @param sx: scale_x value
        @param sy: scale_y value
        @param ox: offset_x value
        @param oy: offset_y value
        @param kwargs:
        @return:
        """
        if node is None:
            node = self
        if self._bounds is not None:
            x0, y0, x1, y1 = self._bounds
            if sx != 1.0:
                d1 = x0 - ox
                d2 = x1 - ox
                x0 = ox + sx * d1
                x1 = ox + sx * d2
            if sy != 1.0:
                d1 = y0 - oy
                d2 = y1 - oy
                y0 = oy + sy * d1
                y1 = oy + sy * d2
            self._bounds = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]

        for listen in self.listeners:
            if hasattr(listen, "scaled"):
                listen.scaled(
                    node, sx=sx, sy=sy, ox=ox, oy=oy, interim=interim
                )  # , **kwargs)

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

    def notify_tree_structure_changed(self, **kwargs):
        """Notify listeners that the tree structure changed in bulk (e.g., bulk add/remove operations).

        This deliberately passes node=None to allow listeners to distinguish a coarse-grained structural
        change from a per-node attached/detached event.
        """
        # Mark dirty for lazy cache invalidation. Elements will flush caches lazily
        # by inspecting the RootNode's `_structure_dirty` flag.
        with self.node_lock:
            try:
                self._structure_dirty = True
            except Exception:
                pass
        # Immediately invalidate caches on listeners that expose invalidate hooks
        for listen in self.listeners:
            try:
                if hasattr(listen, "_invalidate_elems_cache"):
                    listen._invalidate_elems_cache()
            except Exception:
                pass
            try:
                if hasattr(listen, "_invalidate_ops_cache"):
                    listen._invalidate_ops_cache()
            except Exception:
                pass
        # If notifications are paused, skip dispatch of per-listener updates.
        if getattr(self, "pause_notify", False):
            return
        for listen in self.listeners:
            if hasattr(listen, "structure_changed"):
                try:
                    listen.structure_changed(node=None, **kwargs)
                except Exception:
                    pass

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

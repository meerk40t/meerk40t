"""
Undo States

The undo class centralizes the undo stack and related commands. It's passed the
rootnode of the tree and can perform marks to save the current tree states and will
execute undo and redo operations for the tree.
"""
import threading


class UndoState:
    def __init__(self, state, message=None):
        self.state = state
        self.message = message
        if self.message is None:
            self.message = str(id(state))

    @property
    def tree_representation(self):
        def node_representation(node):
            t = node.type 
            if node.children:
                t = f"{t}{'+' if node.expanded else ''}("
                for n in node.children:
                    t = f"{t}{node_representation(n)},"
                t += ")"
            return t

        s = ""
        for node in self.state:
            s += f"{node_representation(node)}, "
        return s
    
    def __str__(self):
        return self.message + " " + self.tree_representation


class Undo:
    LAST_STATE = "Last status"

    def __init__(self, service, tree, active=True, levels=20):
        self.service = service
        self.tree = tree
        self.active = active
        self.levels = levels
        self._lock = threading.Lock()
        self._undo_stack = []
        self._undo_index = -1
        self.mark("init")  # Set initial tree state.
        self.message = None

    def __str__(self):
        return f"Undo(#{self._undo_index} in list of {len(self._undo_stack)} states)"

    def mark(self, message=None):
        """
        Marks an undo state require a backup the tree information.

        @param message: Optional message to be applied to the tree change.

        @return:
        """
        if not self.active:
            return
        with self._lock:
            if (
                self._undo_index < 0
                or self._undo_index != len(self._undo_stack) - 1
                or self._undo_stack[self._undo_index].message != self.LAST_STATE
            ):
                # Only if the active message is not a placeholder
                self._undo_index += 1

            if message is None:
                message = self.message
            try:
                self._undo_stack.insert(
                    self._undo_index,
                    UndoState(self.tree.backup_tree(), message=message),
                )
            except KeyError:
                # Hit a concurrent issue.
                pass
            del self._undo_stack[self._undo_index + 1 :]
            while len(self._undo_stack) > self.levels:
                self._undo_stack.pop(0)
                self._undo_index -= 1
            # self.debug_me(f"Mark done")
            self.message = None
        self.service.signal("undoredo")

    def undo(self):
        """
        Performs an undo operation restoring the tree state.

        Note: because the undo.state is used directly, the UndoState's state must be
        given a fresh copy.
        @return:
        """
        with self._lock:
            if self._undo_index == 0:
                # At bottom of stack.
                return False
            if len(self._undo_stack) == 0:
                # Stack is entirely empty.
                return False
            # print (f"Index: {self._undo_index} / {len(self._undo_stack)}")
            to_be_restored = self._undo_index - 1     
            # self.debug_me(f"Undo requested: {to_be_restored}")
            if self._undo_index == len(self._undo_stack) - 1 and self._undo_stack[self._undo_index].message != self.LAST_STATE:
                # We store the current state
                self._undo_stack.append(
                    UndoState(self.tree.backup_tree(), message=self.LAST_STATE),
                )
                to_be_restored = len(self._undo_stack) - 2
            self._undo_index = to_be_restored
            try:
                undo = self._undo_stack[to_be_restored]
            except IndexError:
                # Invalid? Reset to bottom of stack
                self._undo_index = 0
                return False
            self.tree.restore_tree(undo.state)
            # try:
            #     undo.state = self.tree.backup_tree()  # Get unused copy
            # except KeyError:
            #     pass
            self.service.signal("undoredo")
            # self.debug_me("Undo done")
            return True

    def redo(self):
        """
        Performs a redo operation restoring the tree state.
        """
        with self._lock:
            if self._undo_index >= len(self._undo_stack) - 1:
                return False
            # self.debug_me(f"Redo requested: {self._undo_index + 1}")
            self._undo_index += 1
            try:
                redo = self._undo_stack[self._undo_index]
            except IndexError:
                # Invalid? Reset to top of stack
                self._undo_index = len(self._undo_stack)
                return False
            self.tree.restore_tree(redo.state)
            # try:
            #     redo.state = self.tree.backup_tree()  # Get unused copy
            # except KeyError:
            #     pass
            self.service.signal("undoredo")
            # self.debug_me("Redo done")
            return True

    def undolist(self):
        for i, v in enumerate(self._undo_stack):
            q = "*" if i == self._undo_index else " "
            yield f"{q}{str(i).ljust(5)}: state {str(v)}"

    def debug_me(self, index):
        print (f"Wanted: {index}, stack-index: {self._undo_index} - stack-size: {len(self._undo_stack)}")
        for idx, s in enumerate(self._undo_stack):
            print (f"[{idx}]{'*' if idx==self._undo_index else ' '} {'#' if idx==index else ' '} {str(s)}")
        # for idx in range(len(self._undo_stack)):
        #     print (f"[{idx}]: undo-label: '{self.undo_string(idx=idx, debug=False)}', redo-label: '{self.redo_string(idx=idx, debug=False)}'")


    def undo_string(self, idx = -1, **kwargs):
        if idx < 0:
            idx = self._undo_index
        if idx >= len(self._undo_stack):
            idx = len(self._undo_stack) - 1
        if idx <= 0 or len(self._undo_stack) == 0:
            # At bottom of stack / empty stack
            return ""
        return self._undo_stack[idx].message

    def has_undo(self, *args):
        if self._undo_index == 0:
            # At bottom of stack.
            return False
        # Stack is entirely empty.
        return len(self._undo_stack) > 0

    def redo_string(self, idx = -1, **kwargs):
        if idx < 0:
            idx = self._undo_index
        if idx > len(self._undo_stack) - 2 or len(self._undo_stack) == 0:
            return ""
        return str(self._undo_stack[idx + 1].message)

    def has_redo(self, *args):
        return self._undo_index < len(self._undo_stack) - 1 and (len(self._undo_stack) > 0)

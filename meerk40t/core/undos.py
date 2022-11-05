"""
Undoer

The undo class centralizes the undo stack and related commands. It's passed the
rootnode of the tree and can perform marks to save the current tree states and will
execute undo and redo operations for the tree.
"""


class Undo:
    def __init__(self, tree):
        self.tree = tree
        self._undo_stack = []
        self._undo_index = -1
        self.mark()  # Set initial tree state.

    def mark(self):
        self._undo_index += 1
        self._undo_stack.insert(self._undo_index, self.tree.backup_tree())
        del self._undo_stack[self._undo_index + 1:]

    def undo(self):
        if self._undo_index == 0:
            # At bottom of stack.
            return False
        self._undo_index -= 1
        undo = self._undo_stack[self._undo_index]
        self.tree.restore_tree(undo)
        return True

    def redo(self):
        if self._undo_index >= len(self._undo_stack) - 1:
            return False
        self._undo_index += 1
        redo = self._undo_stack[self._undo_index]
        self.tree.restore_tree(redo)
        return True

    def undolist(self):
        for i, v in enumerate(self._undo_stack):
            q = "*" if i == self._undo_index else " "
            yield f"{q}{str(i).ljust(5)}: undo {id(v)}:{str(v)} elements "

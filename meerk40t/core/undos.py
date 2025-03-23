"""
Undo States

The undo class centralizes the undo stack and related commands. It's passed the
rootnode of the tree and can perform marks to save the current tree states and will
execute undo and redo operations for the tree.


For every change announced in the program ( with elements.undoscope("tag"): ) 
a complete backup of the element tree is being made before applying the changes
So the undo_stack contains the state before the change. And "undo" of that 
undo_index will restore the state before.
If we have already made an undo (ie the undo_index is not the highest number 
but below) then another mark will effectively create a new history.

"""
import threading


class UndoState:
    def __init__(self, state, message=None, hold=False):
        self.state = state
        self.message = message
        self.hold = hold
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
        return self.message # + ". " + self.tree_representation


class Undo:
    LAST_STATE = "Last status"

    def __init__(self, service, tree, active=True, levels=20):
        self.debug_active = False
        self.service = service
        self.tree = tree
        self.active = active
        self.levels = max(3, levels) # at least three
        self._lock = threading.Lock()
        self._undo_stack = []
        self._undo_index = -1
        self.mark("init")  # Set initial tree state.
        self.message = None

    def __str__(self):
        return f"Undo(#{self._undo_index} in list of {len(self._undo_stack)} states)"

    def mark(self, message=None, hold=False):
        """
        Marks an undo state require a backup the tree information.

        @param message: Optional message to be applied to the tree change.

        @return:
        """
        if not self.active:
            return
        with self._lock:
            # print (f"** Mark {message} requested, current {self._undo_index} / {len(self._undo_stack)} **")
            old_idx = self._undo_index
            if self._undo_index < 0:
                self._undo_index = 0
            elif self._undo_index < len(self._undo_stack) and self._undo_stack[self._undo_index].hold:
                # Just add another one on top of it
                self._undo_index += 1
            elif self._undo_index < len(self._undo_stack) and self._undo_stack[self._undo_index].message == self.LAST_STATE:
                # Will be overwritten
                pass
            elif self._undo_index < len(self._undo_stack) - 1 and self._undo_stack[self._undo_index + 1].message != self.LAST_STATE:
                # Will be overwritten
                pass 
            else:
                # Just add another one on top of it
                self._undo_index += 1

            if message is None:
                message = self.message
            try:
                self._undo_stack.insert(
                    self._undo_index,
                    UndoState(self.tree.backup_tree(), message=message, hold=hold),
                )
            except KeyError as e:
                # Hit a concurrent issue.
                print(f"Could not save undo state: {e}")
                self._undo_index = old_idx
                return
            # print (f"Deleting #{self._undo_index + 1} and above...")
            del self._undo_stack[self._undo_index + 1 :]
            while len(self._undo_stack) > self.levels:
                self._undo_stack.pop(0)
                self._undo_index -= 1
            self.debug_me(f"Successfully inserted {message} at {self._undo_index} (old index was {old_idx})")
        self.message = None
        self.service.signal("undoredo")

    def undo(self, index = None):
        """
        Performs an undo operation restoring the tree state.

        Note: because the undo.state is used directly, the UndoState's state must be
        given a fresh copy.
        @return:
        """
        with self._lock:
            to_be_restored = index if index is not None else self._undo_index - 1
            if to_be_restored == 0:
                # At bottom of stack.
                return False
            if len(self._undo_stack) == 0:
                # Stack is entirely empty.
                return False
            self.debug_me(f"Undo requested: {to_be_restored}")
            if to_be_restored == len(self._undo_stack) - 1 and self._undo_stack[to_be_restored].message != self.LAST_STATE:
                # We store the current state, as none was stored so far
                self._undo_stack.append(
                    UndoState(self.tree.backup_tree(), message=self.LAST_STATE),
                )
                # print ("**** Did add a last state to go back to if needed ****")
            elif to_be_restored == len(self._undo_stack) - 2 and self._undo_stack[to_be_restored + 1].message == self.LAST_STATE:
                # We are at the last actively monitored index but we already have a current state -> replace it
                self._undo_stack.pop(-1)
                self._undo_stack.append(
                    UndoState(self.tree.backup_tree(), message=self.LAST_STATE),
                )
                # print ("**** Did add a last state to go back to if needed, and overwrote the last state ****")
            # print (f"Index: {self._undo_index} / {len(self._undo_stack)} - To be restored: {to_be_restored}, param: {index}")
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
            self.debug_me("Undo done")
            return True

    def redo(self, index=None):
        """
        Performs a redo operation restoring the tree state.
        """
        with self._lock:
            to_be_restored = index + 1 if index is not None else self._undo_index + 1
            to_be_restored = min(len(self._undo_stack) - 1, to_be_restored)
            self.debug_me(f"Redo requested: {index} -> will restore #{to_be_restored}")
            self._undo_index = to_be_restored
            try:
                redo = self._undo_stack[to_be_restored]
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
            self.debug_me("Redo done")
            return True

    def undolist(self):
        covered = False
        for i, v in enumerate(self._undo_stack):
            q = "*" if i == self._undo_index else " "
            covered = covered or (i == self._undo_index)
            yield f"{q}{str(i).ljust(5)}: state {str(v)}"
        if not covered:
            yield f"Strange: {self._undo_index} out of bounds..."

    def debug_me(self, request):
        if not self.debug_active:
            return
        print (f"{request}, stack-index: {self._undo_index} - stack-size: {len(self._undo_stack)}")
        for idx, s in enumerate(self._undo_stack):
            print (f"[{idx}]{'*' if idx==self._undo_index else ' '} {'#' if idx==request else ' '} {str(s)}")
            # self.debug_tree(s.state)
        # for idx in range(len(self._undo_stack)):
        #     print (f"[{idx}]: undo-label: '{self.undo_string(idx=idx, debug=False)}', redo-label: '{self.redo_string(idx=idx, debug=False)}'")


    def undo_string(self, idx = -1, **kwargs):
        self.validate()
        if idx < 0:
            idx = self._undo_index - 1
        return str(self._undo_stack[idx].message) if self.has_undo() else ""

    def has_undo(self, *args):
        self.validate()
        return self.active and self._undo_index > 0

    def redo_string(self, idx = -1, **kwargs):
        self.validate()
        if idx < 0:
            idx = self._undo_index - 1
        return str(self._undo_stack[idx + 1].message) if self.has_redo() else ""

    def has_redo(self, *args):
        self.validate()
        return self.active and self._undo_index < len(self._undo_stack) - 1

    def validate(self):
        if self.active and self._undo_stack and self._undo_stack[-1].message != self.LAST_STATE:
            # We store the current state, just to have something to fall back to if needed
            if self._undo_index >= len(self._undo_stack) - 1:
                self._undo_index += 1
            # print ("** Validate called and appending last state **")
            self._undo_stack.append(
                UndoState(self.tree.backup_tree(), message=self.LAST_STATE),
            )

    def find(self, scope:str):
        # self.debug_me(f"Looking for {scope}")
        return next(
            (
                idx
                for idx, state in enumerate(self._undo_stack)
                if state.message == scope
            ),
            -1,
        )

    def remove(self, index):
        if 0 <= index < len(self._undo_stack):
            # print (f"Removing index {index}")
            # self.debug_me("before")
            del self._undo_stack[index :]
            self._undo_index = len(self._undo_stack) - 1
            self.validate()
            # self._undo_stack.pop(index)
            # self.debug_me(f"after removing {index}")

    def rename(self, index, message):
        if 0 <= index < len(self._undo_stack):
            self._undo_stack[index].message = message
            
    def states(self, scope:str):
        self.validate()
        lower_end = 1 # Ignore First
        upper_end = len(self._undo_stack) - 1 # Ignore last
        if scope == "undo":
            upper_end = self._undo_index
        elif scope == "redo":
            lower_end = self._undo_index
        return ((idx, self._undo_stack[idx]) for idx in range(lower_end, upper_end))

    def debug_tree(self, state):
        def show_children(parent, header):
            for e in parent._children:
                print (f"{header} {e.type}")
                show_children(e, header + "--")
        for idx, n in enumerate(state):
            print(f"[{idx}] {n.type}")
            show_children(n, "--")
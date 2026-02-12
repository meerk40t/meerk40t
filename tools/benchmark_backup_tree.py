"""
Micro-benchmark for Node.backup_tree() / _build_copy_nodes() / _validate_links().

Measures wall time and object counts for trees of varying size to understand
scaling characteristics and identify the dominant cost centres.
"""

import sys
import time
from copy import copy

sys.path.insert(0, ".")

from meerk40t.core.node.node import Node


# ---------------------------------------------------------------------------
# Build a synthetic tree that resembles a real MeerK40t element tree
# ---------------------------------------------------------------------------

class FakeRoot(Node):
    """Minimal stand-in for RootNode with backup_tree from Node."""
    def __init__(self):
        super().__init__(type="root")
        self._root = self
        self._parent = None
        self.id = "root"
        self.label = "root"

    def __copy__(self):
        # Root copies don't matter for backup_tree
        return FakeRoot()

    def notify_created(self, node=None, **kwargs):
        pass
    def notify_attached(self, node=None, **kwargs):
        pass
    def notify_detached(self, node=None, **kwargs):
        pass


def make_leaf(root, type_name="elem rect", **extra):
    """Create a leaf node without going through the bootstrap registry."""
    n = Node.__new__(Node)
    Node.__init__(n, type=type_name, **extra)
    n._root = root
    return n


def build_tree(n_elems, n_ops=5, refs_per_op=None):
    """
    Build a tree with:
      - root
        - branch_ops  (n_ops op children, each with refs_per_op references)
        - branch_elems (n_elems leaf element nodes)
        - branch_reg   (empty)
    """
    root = FakeRoot()

    branch_ops = make_leaf(root, "branch ops")
    branch_ops._parent = root
    branch_elems = make_leaf(root, "branch elems")
    branch_elems._parent = root
    branch_reg = make_leaf(root, "branch reg")
    branch_reg._parent = root
    root._children = [branch_ops, branch_elems, branch_reg]

    # Populate elements
    elems = []
    for i in range(n_elems):
        e = make_leaf(root, "elem rect")
        e._parent = branch_elems
        e.id = f"e{i}"
        e._emphasized = (i % 5 == 0)
        elems.append(e)
    branch_elems._children = elems

    # Populate ops with references
    if refs_per_op is None:
        refs_per_op = min(n_elems, 20)
    for j in range(n_ops):
        op = make_leaf(root, "op engrave")
        op._parent = branch_ops
        branch_ops._children.append(op)
        for k in range(refs_per_op):
            ref = make_leaf(root, "reference")
            ref._parent = op
            target = elems[k % len(elems)] if elems else None
            ref.node = target
            if target is not None:
                target._references.append(ref)
            op._children.append(ref)

    total = 1  # root
    for branch in root._children:
        total += 1
        total += len(branch._children)
        for child in branch._children:
            total += len(child._children)

    return root, total


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------

def bench_backup_tree(root, repeats=5):
    """Time backup_tree for *repeats* iterations, return (min_ms, avg_ms, node_count_per_backup)."""
    times = []
    node_count = 0
    for _ in range(repeats):
        t0 = time.perf_counter()
        branches = root.backup_tree()
        t1 = time.perf_counter()
        times.append(t1 - t0)
        if node_count == 0:
            # count nodes in backup
            stack = list(branches)
            while stack:
                n = stack.pop()
                node_count += 1
                stack.extend(n._children)
    return min(times) * 1000, (sum(times) / len(times)) * 1000, node_count


def bench_build_copy_nodes(root, repeats=5):
    """Time just _build_copy_nodes (the copy() loop without structure rebuild)."""
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        links = root._build_copy_nodes()
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return min(times) * 1000, (sum(times) / len(times)) * 1000, len(links)


def bench_validate_links(root, repeats=5):
    """Time just _validate_links."""
    # Pre-build links once
    links_template = root._build_copy_nodes()
    times = []
    for _ in range(repeats):
        # Rebuild links each time (since validate mutates children)
        links = root._build_copy_nodes()
        t0 = time.perf_counter()
        root._validate_links(links)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return min(times) * 1000, (sum(times) / len(times)) * 1000


def bench_copy_node(root, repeats=100):
    """Time a single copy(node) call averaged over all nodes."""
    # Collect all nodes
    nodes = []
    stack = list(root._children)
    while stack:
        n = stack.pop()
        nodes.append(n)
        stack.extend(n._children)
    if not nodes:
        return 0, 0
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        for n in nodes:
            copy(n)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    per_node_min = min(times) / len(nodes) * 1e6  # microseconds
    per_node_avg = (sum(times) / len(times)) / len(nodes) * 1e6
    return per_node_min, per_node_avg, len(nodes)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    sizes = [50, 100, 250, 500, 1000, 2000, 5000]

    print("=" * 85)
    print(f"{'Elems':>7} {'Nodes':>7} │ {'backup_tree':>14} │ {'build_copy':>14} │ {'validate':>14} │ {'copy/node':>12}")
    print(f"{'':>7} {'':>7} │ {'min(ms)':>7} {'avg':>6} │ {'min(ms)':>7} {'avg':>6} │ {'min(ms)':>7} {'avg':>6} │ {'avg(μs)':>7} {'cnt':>4}")
    print("─" * 85)

    for n_elems in sizes:
        root, total_nodes = build_tree(n_elems)

        bt_min, bt_avg, bt_count = bench_backup_tree(root, repeats=5)
        bc_min, bc_avg, bc_links = bench_build_copy_nodes(root, repeats=5)
        vl_min, vl_avg = bench_validate_links(root, repeats=5)
        cn_min, cn_avg, cn_count = bench_copy_node(root, repeats=20)

        print(
            f"{n_elems:>7} {total_nodes:>7} │"
            f" {bt_min:>7.2f} {bt_avg:>6.2f} │"
            f" {bc_min:>7.2f} {bc_avg:>6.2f} │"
            f" {vl_min:>7.2f} {vl_avg:>6.2f} │"
            f" {cn_avg:>7.2f} {cn_count:>4}"
        )

    print("=" * 85)

    # Detailed breakdown for a medium tree
    print("\n--- Detailed breakdown for 1000 elements ---")
    root, total = build_tree(1000)

    # Time dict.update vs manual __dict__ copy
    nodes = []
    stack = list(root._children)
    while stack:
        n = stack.pop()
        nodes.append(n)
        stack.extend(n._children)

    # Approach 1: current copy() which uses __copy__
    repeats = 50
    t0 = time.perf_counter()
    for _ in range(repeats):
        for n in nodes:
            copy(n)
    t1 = time.perf_counter()
    copy_total = (t1 - t0) / repeats * 1000
    print(f"  copy() all {len(nodes)} nodes: {copy_total:.2f} ms")

    # Approach 2: __class__.__new__ + dict.update (skip copy dispatch)
    t0 = time.perf_counter()
    for _ in range(repeats):
        for n in nodes:
            cls = n.__class__
            obj = cls.__new__(cls)
            obj.__dict__.update(n.__dict__)
            obj._children = []
            obj._references = []
            obj._points = []
            obj._default_map = {}
    t1 = time.perf_counter()
    direct_total = (t1 - t0) / repeats * 1000
    print(f"  direct new+update all {len(nodes)} nodes: {direct_total:.2f} ms")
    if copy_total > 0:
        print(f"  speedup: {copy_total / direct_total:.2f}x")

    # Approach 3: measure dict.update alone
    sample = nodes[0]
    d = sample.__dict__
    t0 = time.perf_counter()
    count = len(nodes) * repeats
    for _ in range(count):
        new_d = {}
        new_d.update(d)
    t1 = time.perf_counter()
    print(f"  dict.update alone per node: {(t1 - t0) / count * 1e6:.3f} μs")

    # Approach 4: measure id() + dict insert
    t0 = time.perf_counter()
    for _ in range(repeats):
        links = {}
        for n in nodes:
            links[id(n)] = (n, n)  # simulate
    t1 = time.perf_counter()
    links_total = (t1 - t0) / repeats * 1000
    print(f"  id()+dict insert all {len(nodes)} nodes: {links_total:.2f} ms")

    # _build_copy_nodes: recursive vs iterative
    print("\n--- Recursive vs iterative _build_copy_nodes for 1000 elements ---")
    root2, _ = build_tree(1000)

    # Current recursive
    repeats = 20
    t0 = time.perf_counter()
    for _ in range(repeats):
        root2._build_copy_nodes()
    t1 = time.perf_counter()
    recursive_ms = (t1 - t0) / repeats * 1000
    print(f"  recursive _build_copy_nodes: {recursive_ms:.2f} ms")

    # Iterative version
    def build_copy_nodes_iterative(root_node):
        links = {id(root_node): (root_node, None)}
        root_ref = root_node._root
        stack = []
        # Push children in reverse so we process left-to-right
        for c in reversed(root_node._children):
            stack.append(c)
        while stack:
            node = stack.pop()
            # Push this node's children
            for c in reversed(node._children):
                stack.append(c)
            # Copy
            node_copy = copy(node)
            node_copy._root = root_ref
            links[id(node)] = (node, node_copy)
        return links

    t0 = time.perf_counter()
    for _ in range(repeats):
        build_copy_nodes_iterative(root2)
    t1 = time.perf_counter()
    iterative_ms = (t1 - t0) / repeats * 1000
    print(f"  iterative _build_copy_nodes: {iterative_ms:.2f} ms")
    if recursive_ms > 0:
        print(f"  speedup: {recursive_ms / iterative_ms:.2f}x")

    # Iterative version with inlined copy
    def build_copy_nodes_iterative_inlined(root_node):
        links = {id(root_node): (root_node, None)}
        root_ref = root_node._root
        stack = []
        for c in reversed(root_node._children):
            stack.append(c)
        _list = list
        _dict = dict
        while stack:
            node = stack.pop()
            children = node._children
            if children:
                for c in reversed(children):
                    stack.append(c)
            # Inline copy: skip copy() dispatch overhead
            cls = node.__class__
            node_copy = cls.__new__(cls)
            node_copy.__dict__.update(node.__dict__)
            node_copy._children = _list()
            node_copy._references = _list()
            node_copy._points = _list()
            node_copy._default_map = _dict()
            node_copy._root = root_ref
            links[id(node)] = (node, node_copy)
        return links

    t0 = time.perf_counter()
    for _ in range(repeats):
        build_copy_nodes_iterative_inlined(root2)
    t1 = time.perf_counter()
    inlined_ms = (t1 - t0) / repeats * 1000
    print(f"  iterative+inlined copy:      {inlined_ms:.2f} ms")
    if recursive_ms > 0:
        print(f"  speedup vs recursive: {recursive_ms / inlined_ms:.2f}x")

    # Combined: iterative build + validate
    def backup_tree_optimised(root_node):
        links = build_copy_nodes_iterative_inlined(root_node)
        root_node._validate_links(links)
        return [links[id(c)][1] for c in root_node._children]

    t0 = time.perf_counter()
    for _ in range(repeats):
        backup_tree_optimised(root2)
    t1 = time.perf_counter()
    opt_ms = (t1 - t0) / repeats * 1000

    t0 = time.perf_counter()
    for _ in range(repeats):
        root2.backup_tree()
    t1 = time.perf_counter()
    orig_ms = (t1 - t0) / repeats * 1000

    print(f"\n  Current backup_tree:   {orig_ms:.2f} ms")
    print(f"  Optimised backup_tree: {opt_ms:.2f} ms")
    if orig_ms > 0:
        print(f"  Overall speedup: {orig_ms / opt_ms:.2f}x")

    # Check: verify attribute attrib_list loop cost
    print("\n--- Attribute verification loop cost ---")
    attrib_list = (
        "_selected", "_emphasized", "_emphasized_time",
        "_highlighted", "_expanded", "_translated_text",
    )
    copies = [(n, copy(n)) for n in nodes]
    t0 = time.perf_counter()
    for _ in range(repeats):
        for orig, cp in copies:
            c_dict = orig.__dict__
            copy_dict = cp.__dict__
            for att in attrib_list:
                if att in c_dict:
                    c_val = c_dict[att]
                    if copy_dict.get(att) != c_val:
                        copy_dict[att] = c_val
    t1 = time.perf_counter()
    attrib_ms = (t1 - t0) / repeats * 1000
    print(f"  Attrib verification for {len(nodes)} nodes: {attrib_ms:.2f} ms")
    # Without verification (since __copy__ already uses dict.update)
    print(f"  Note: __copy__ already copies all attrs via dict.update()")
    print(f"  -> This verification loop is pure overhead if __copy__ is correct")


if __name__ == "__main__":
    main()

"""
Profile backup_tree on a realistic 10k element tree to identify bottlenecks.
"""
import sys
import os
import time
import cProfile
import pstats
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from copy import copy
from meerk40t.core.node.node import Node
from meerk40t.core.node.elem_rect import RectNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.elem_ellipse import EllipseNode
from meerk40t.core.node.elem_line import LineNode
from meerk40t.core.node.elem_text import TextNode
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.svgelements import Matrix, Color


def build_tree(n_elements=10000):
    """Build a realistic tree with mixed element types."""
    root = Node(type="root")
    root._root = root

    # Create branch structure like real MeerK40t
    branch_elems = Node(type="branch elems")
    branch_elems._parent = root
    branch_elems._root = root
    root._children.append(branch_elems)

    branch_ops = Node(type="branch ops")
    branch_ops._parent = root
    branch_ops._root = root
    root._children.append(branch_ops)

    # Approximate distribution in a real design
    node_types = [
        (RectNode, 0.30, {"x": 0, "y": 0, "width": 100, "height": 50,
                          "matrix": Matrix(), "stroke": Color("red"), "fill": Color("blue")}),
        (PathNode, 0.40, {"geometry": None, "matrix": Matrix(),
                          "stroke": Color("black"), "fill": None}),
        (EllipseNode, 0.15, {"cx": 50, "cy": 50, "rx": 30, "ry": 20,
                             "matrix": Matrix(), "stroke": Color("green"), "fill": None}),
        (LineNode, 0.10, {"x1": 0, "y1": 0, "x2": 100, "y2": 100,
                          "matrix": Matrix(), "stroke": Color("blue"), "fill": None}),
        (TextNode, 0.05, {"text": "Hello", "matrix": Matrix(),
                          "stroke": Color("black"), "fill": Color("white")}),
    ]

    import random
    random.seed(42)

    for i in range(n_elements):
        # Pick type based on distribution
        r = random.random()
        cumulative = 0
        for cls, prob, kwargs in node_types:
            cumulative += prob
            if r <= cumulative:
                try:
                    node = cls(**kwargs)
                except Exception:
                    node = Node(type="elem rect")
                break
        else:
            node = Node(type="elem rect")

        node._parent = branch_elems
        node._root = root
        branch_elems._children.append(node)

    return root


def time_backup(root, label, n_runs=5):
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        result = root.backup_tree()
        t1 = time.perf_counter()
        times.append(t1 - t0)
        del result
    avg = sum(times) / len(times)
    mn = min(times)
    print(f"{label}: avg={avg*1000:.1f}ms, min={mn*1000:.1f}ms, max={max(times)*1000:.1f}ms ({n_runs} runs)")
    return mn


def profile_backup(root):
    """cProfile the backup to find hotspots."""
    pr = cProfile.Profile()
    pr.enable()
    result = root.backup_tree()
    pr.disable()
    del result

    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    print(s.getvalue())

    s2 = StringIO()
    ps2 = pstats.Stats(pr, stream=s2).sort_stats("tottime")
    ps2.print_stats(20)
    print("=== BY TOTAL TIME ===")
    print(s2.getvalue())


def benchmark_copy_methods(root):
    """Compare copy speed: node_dict+init vs __dict__.update."""
    branch = root._children[0]  # branch elems
    nodes = branch._children[:1000]

    # Current: node_dict + ClassName(**nd)
    t0 = time.perf_counter()
    for node in nodes:
        c = copy(node)
    t1 = time.perf_counter()
    print(f"copy() x1000: {(t1-t0)*1000:.1f}ms ({(t1-t0)/len(nodes)*1e6:.1f}µs/node)")

    # Measure just node_dict
    t0 = time.perf_counter()
    for node in nodes:
        nd = node.node_dict
    t1 = time.perf_counter()
    print(f"node_dict x1000: {(t1-t0)*1000:.1f}ms ({(t1-t0)/len(nodes)*1e6:.1f}µs/node)")

    # Measure just __dict__.update
    t0 = time.perf_counter()
    for node in nodes:
        obj = node.__class__.__new__(node.__class__)
        obj.__dict__.update(node.__dict__)
        obj._children = list()
        obj._references = list()
        obj._points = list()
        obj._default_map = dict()
        obj._parent = None
        obj._root = None
    t1 = time.perf_counter()
    print(f"__new__+update x1000: {(t1-t0)*1000:.1f}ms ({(t1-t0)/len(nodes)*1e6:.1f}µs/node)")

    # Measure copy(matrix) + copy(stroke) + copy(fill)
    t0 = time.perf_counter()
    for node in nodes:
        if hasattr(node, 'matrix') and node.matrix is not None:
            copy(node.matrix)
        if hasattr(node, 'stroke') and node.stroke is not None:
            copy(node.stroke)
        if hasattr(node, 'fill') and node.fill is not None:
            copy(node.fill)
    t1 = time.perf_counter()
    print(f"copy(matrix+stroke+fill) x1000: {(t1-t0)*1000:.1f}ms ({(t1-t0)/len(nodes)*1e6:.1f}µs/node)")


if __name__ == "__main__":
    sizes = [1000, 5000, 10000]
    for n in sizes:
        print(f"\n{'='*60}")
        print(f"Tree with {n} elements")
        print(f"{'='*60}")
        root = build_tree(n)
        total = sum(1 for _ in root._children[0]._children) + 2  # + 2 branches
        print(f"Total nodes: {total}")

        time_backup(root, f"backup_tree ({n})")

        if n == 10000:
            print(f"\n--- Profiling {n}-element backup ---")
            profile_backup(root)

        if n == 1000:
            print(f"\n--- Copy method comparison ---")
            benchmark_copy_methods(root)

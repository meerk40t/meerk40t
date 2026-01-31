# Elements flattened-list cache (elems() / ops())

This document explains the caching mechanism introduced to improve performance when code repeatedly iterates the elements tree with `Elements.elems()` and `Elements.ops()`.

## Goals

- Avoid repeated full-tree traversals (expensive `flat()` calls) for common read paths.
- Preserve synchronous semantics for callers that need immediate cache invalidation (e.g., fast add/remove/clear operations used in tests and CLI commands).
- Provide developer diagnostics to inspect cache usage and `flat()` call frequency.

## When a cache is used

- A **simple per-instance cache** is used by `Elements.elems()` and `Elements.ops()` only when it is safe:
  - No `depth` argument is supplied (i.e., `depth is None`).
  - No custom `types` filter is provided (the default type filtering is allowed).
- Property filters (like `emphasized=True`, `selected=True`) are applied on top of the cached list so callers still get the right subset without rebuilding the tree.

## Invalidation strategy

Two complementary mechanisms ensure correctness and keep performance:

1. **Lazy invalidation (recommended, efficient)**
   - `RootNode` maintains a `_structure_dirty` flag that is set to `True` on structural changes (node create/destroy/attach/detach/structure change).
   - `Elements.elems()` / `Elements.ops()` check the root flag and lazily flush the cache under the `node_lock` when they detect it.
   - This reduces repeated cache invalidation during bulk operations and avoids expensive immediate traversals when many changes happen quickly.

2. **Immediate invalidation (synchronous callers / tests)**
   - `RootNode.notify_tree_structure_changed()` calls registered listeners that implement `_invalidate_elems_cache()` / `_invalidate_ops_cache()` to preserve immediate-invalidation semantics where callers expect it (for example, `fast=True` operations used in unit tests and some CLI/console commands).
   - This maintains the original, deterministic behavior for callers that depend on immediate cache clearing.

## Bulk-load and flood protection

- During large/bulk loads we avoid flooding listeners and the scheduler:
  - `pause_notify` is used to temporarily suppress per-node notification dispatch.
  - The kernel can temporarily suspend scheduled jobs (`kernel.suspend_jobs`) while the structure is static to avoid heavy `schedule_run`/`process_queue` overhead.

## Diagnostics

- A `flat_tracker` counts `flat()` invocations for `elem_branch`/`op_branch` and there is a console command `flat-stats` to inspect or reset counts.
- Unit tests for the cache behavior live in `test/test_elements_cache.py`.

## Developer notes

- Prefer calling `Elements.elems()` / `Elements.ops()` without `depth` or custom `types` when you want the performance benefits of caching.
- If a caller needs deterministic immediate cache invalidation, either rely on the synchronous notify path (e.g., fast operations that trigger `notify_tree_structure_changed`) or call the (internal) cache invalidation helper when appropriate.
- If you add code that schedules many small jobs or repeatedly modifies the tree, consider using `pause_notify`/`kernel.suspend_jobs` around the bulk operation to reduce load-time overhead.


---

*If you need more detail, see the unit tests (`test/test_elements_cache.py`) or ask for a profiling summary of a problematic scenario.*

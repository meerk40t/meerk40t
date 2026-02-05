"""Unit tests for the LayerCache validity state machine and invalidation rules.

These tests exercise the three-level cache contract defined by LayerCache in
meerk40t/gui/scene/scene.py without importing wx.  A thin ``_CacheMock``
replicates every state-transition rule so that the invariants can be verified
purely in-process.

Invariants under test
---------------------
1. Initial state: all three caches invalid.
2. ``invalidate_background()``  →  background, elements, AND composite invalid.
3. ``invalidate_elements()``    →  elements AND composite invalid; background unchanged.
4. ``invalidate_composite()``   →  only composite invalid; background and elements unchanged.
5. ``ensure_size(w, h)``        →  if (w, h) differs from the stored size,
                                    all three caches become invalid.
6. ``ensure_size(w, h)``        →  if (w, h) equals stored size, validity is
                                    preserved (no-op).
7. ``mark_background_valid()`` / ``mark_elements_valid()`` / ``mark_composite_valid()``
                                →  set the corresponding flag to True.
8. Draw-sequence scenarios that combine the above in realistic order.
"""

import unittest


class _CacheMock:
    """Minimal stand-in for LayerCache — tests only the validity state machine.

    Replicates the invalidation contract from LayerCache in scene.py:
      - invalidate_background()  →  background, elements, and composite become invalid
      - invalidate_elements()    →  elements and composite become invalid (background unchanged)
      - invalidate_composite()   →  only composite becomes invalid
      - mark_background_valid()  →  background becomes valid (others unchanged)
      - mark_elements_valid()    →  elements becomes valid (others unchanged)
      - mark_composite_valid()   →  composite becomes valid (others unchanged)
      - ensure_size(w, h)        →  if size changes, all three become invalid
    """

    def __init__(self):
        self._bg_valid = False
        self._elements_valid = False
        self._composite_valid = False
        self._size = (0, 0)

    # -- queries ----------------------------------------------------------
    @property
    def background_valid(self):
        return self._bg_valid

    @property
    def elements_valid(self):
        return self._elements_valid

    @property
    def composite_valid(self):
        return self._composite_valid

    @property
    def size(self):
        return self._size

    # -- invalidation -----------------------------------------------------
    def invalidate_background(self):
        self._bg_valid = False
        self._elements_valid = False
        self._composite_valid = False

    def invalidate_elements(self):
        self._elements_valid = False
        self._composite_valid = False

    def invalidate_composite(self):
        self._composite_valid = False

    # -- size management --------------------------------------------------
    def ensure_size(self, width, height):
        if self._size == (width, height):
            return
        self._size = (width, height)
        self._bg_valid = False
        self._elements_valid = False
        self._composite_valid = False

    # -- mark valid -------------------------------------------------------
    def mark_background_valid(self):
        self._bg_valid = True

    def mark_elements_valid(self):
        self._elements_valid = True

    def mark_composite_valid(self):
        self._composite_valid = True


# ======================================================================
# 1  Initial state
# ======================================================================
class TestLayerCacheInitialState(unittest.TestCase):
    def test_initially_all_three_invalid(self):
        cache = _CacheMock()
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_initial_size_is_zero(self):
        cache = _CacheMock()
        self.assertEqual(cache.size, (0, 0))


# ======================================================================
# 2  invalidate_background  –  clears all three
# ======================================================================
class TestInvalidateBackground(unittest.TestCase):
    def test_clears_all_three_when_all_valid(self):
        cache = _CacheMock()
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        cache.invalidate_background()
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_noop_when_already_invalid(self):
        cache = _CacheMock()
        # already invalid from __init__
        cache.invalidate_background()
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_clears_elements_and_composite_even_when_background_already_invalid(self):
        cache = _CacheMock()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        # background is still invalid from __init__
        cache.invalidate_background()
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)


# ======================================================================
# 3  invalidate_elements  –  clears elements and composite
# ======================================================================
class TestInvalidateElements(unittest.TestCase):
    def test_clears_elements_and_composite(self):
        cache = _CacheMock()
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        cache.invalidate_elements()
        self.assertTrue(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_preserves_background_when_elements_already_invalid(self):
        cache = _CacheMock()
        cache.mark_background_valid()
        # elements and composite still False from __init__
        cache.invalidate_elements()
        self.assertTrue(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_noop_when_all_already_invalid(self):
        cache = _CacheMock()
        cache.invalidate_elements()
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)


# ======================================================================
# 4  invalidate_composite  –  clears composite only
# ======================================================================
class TestInvalidateComposite(unittest.TestCase):
    def test_clears_only_composite(self):
        cache = _CacheMock()
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        cache.invalidate_composite()
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_preserves_background_and_elements_when_composite_already_invalid(self):
        cache = _CacheMock()
        cache.mark_background_valid()
        cache.mark_elements_valid()
        # composite still False from __init__
        cache.invalidate_composite()
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_noop_when_all_already_invalid(self):
        cache = _CacheMock()
        cache.invalidate_composite()
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)


# ======================================================================
# 5 & 6  ensure_size
# ======================================================================
class TestEnsureSize(unittest.TestCase):
    def test_same_size_preserves_validity(self):
        cache = _CacheMock()
        cache._size = (800, 600)
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()

        cache.ensure_size(800, 600)  # no change

        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertTrue(cache.composite_valid)
        self.assertEqual(cache.size, (800, 600))

    def test_width_change_invalidates_all_three(self):
        cache = _CacheMock()
        cache._size = (800, 600)
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()

        cache.ensure_size(1024, 600)

        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)
        self.assertEqual(cache.size, (1024, 600))

    def test_height_change_invalidates_all_three(self):
        cache = _CacheMock()
        cache._size = (800, 600)
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()

        cache.ensure_size(800, 768)

        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)
        self.assertEqual(cache.size, (800, 768))

    def test_both_dimensions_change(self):
        cache = _CacheMock()
        cache._size = (800, 600)
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()

        cache.ensure_size(1920, 1080)

        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)
        self.assertEqual(cache.size, (1920, 1080))

    def test_from_zero_size(self):
        """First ensure_size call (from 0,0) must allocate and invalidate."""
        cache = _CacheMock()
        cache.ensure_size(640, 480)
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)
        self.assertEqual(cache.size, (640, 480))


# ======================================================================
# 7  mark_valid helpers
# ======================================================================
class TestMarkValid(unittest.TestCase):
    def test_mark_background_valid(self):
        cache = _CacheMock()
        cache.mark_background_valid()
        self.assertTrue(cache.background_valid)
        self.assertFalse(cache.elements_valid)  # elements untouched
        self.assertFalse(cache.composite_valid)  # composite untouched

    def test_mark_elements_valid(self):
        cache = _CacheMock()
        cache.mark_elements_valid()
        self.assertFalse(cache.background_valid)  # background untouched
        self.assertTrue(cache.elements_valid)
        self.assertFalse(cache.composite_valid)  # composite untouched

    def test_mark_composite_valid(self):
        cache = _CacheMock()
        cache.mark_composite_valid()
        self.assertFalse(cache.background_valid)  # background untouched
        self.assertFalse(cache.elements_valid)   # elements untouched
        self.assertTrue(cache.composite_valid)

    def test_mark_all_three_valid(self):
        cache = _CacheMock()
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertTrue(cache.composite_valid)


# ======================================================================
# 8  Realistic draw-sequence scenarios
# ======================================================================
class TestDrawSequences(unittest.TestCase):
    """Simulate the typical sequences that happen in _update_buffer_ui_thread."""

    # -- helper: return a cache that has just completed its first draw ----
    def _warmed_cache(self, w=800, h=600):
        cache = _CacheMock()
        cache.ensure_size(w, h)
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        return cache

    # ----------------------------------------------------------------
    def test_first_draw_renders_all_three(self):
        """Fresh cache: all invalid → render A → render B → render C → all valid."""
        cache = _CacheMock()
        cache.ensure_size(800, 600)

        self.assertFalse(cache.background_valid)
        cache.mark_background_valid()

        self.assertFalse(cache.elements_valid)
        cache.mark_elements_valid()

        self.assertFalse(cache.composite_valid)
        cache.mark_composite_valid()

        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertTrue(cache.composite_valid)

    def test_emphasized_element_change_rerenders_only_composite(self):
        """invalidate_composite (emphasized element change) → only C re-rendered."""
        cache = self._warmed_cache()

        cache.invalidate_composite()  # simulates emphasized element modified
        self.assertTrue(cache.background_valid)   # A untouched
        self.assertTrue(cache.elements_valid)     # B untouched
        self.assertFalse(cache.composite_valid)   # C dirty

        cache.mark_composite_valid()              # re-render C
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertTrue(cache.composite_valid)

    def test_non_emphasized_element_change_rerenders_elements_and_composite(self):
        """invalidate_elements (non-emphasized element change) → B and C re-rendered."""
        cache = self._warmed_cache()

        cache.invalidate_elements()               # simulates non-emphasized element added/modified
        self.assertTrue(cache.background_valid)   # A untouched
        self.assertFalse(cache.elements_valid)    # B dirty
        self.assertFalse(cache.composite_valid)   # C dirty (cascade)

        cache.mark_elements_valid()               # re-render B
        cache.mark_composite_valid()              # re-render C
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertTrue(cache.composite_valid)

    def test_zoom_pan_rerenders_all_three(self):
        """Matrix change (zoom/pan) → invalidate_background → all three re-rendered."""
        cache = self._warmed_cache()

        cache.invalidate_background()  # simulates matrix-snapshot mismatch
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertTrue(cache.composite_valid)

    def test_successive_emphasized_changes_no_background_or_elements_rerender(self):
        """Multiple rapid emphasized element changes before next draw do not touch A or B."""
        cache = self._warmed_cache()

        cache.invalidate_composite()
        cache.invalidate_composite()
        cache.invalidate_composite()

        self.assertTrue(cache.background_valid)   # A still valid
        self.assertTrue(cache.elements_valid)     # B still valid
        self.assertFalse(cache.composite_valid)   # C dirty

    def test_background_invalidation_overrides_composite_only(self):
        """If composite-only was pending and then background fires, all three dirty."""
        cache = self._warmed_cache()

        cache.invalidate_composite()               # emphasized element change
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)

        cache.invalidate_background()              # then zoom/pan
        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

    def test_resize_during_pending_element_change(self):
        """Window resize while a composite invalidation is pending → all three dirty."""
        cache = self._warmed_cache(800, 600)

        cache.invalidate_composite()               # element changed
        cache.ensure_size(1024, 768)               # window resized

        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)
        self.assertEqual(cache.size, (1024, 768))

    def test_resize_to_same_size_after_element_change(self):
        """ensure_size with unchanged size after element change is a no-op on A and B."""
        cache = self._warmed_cache(800, 600)

        cache.invalidate_composite()
        cache.ensure_size(800, 600)  # no size change → no-op

        self.assertTrue(cache.background_valid)    # A stays valid
        self.assertTrue(cache.elements_valid)      # B stays valid
        self.assertFalse(cache.composite_valid)    # C still dirty

    def test_multiple_full_cycles(self):
        """Two complete warm → dirty → re-render cycles in a row."""
        cache = _CacheMock()
        for _ in range(2):
            cache.ensure_size(800, 600)
            cache.mark_background_valid()
            cache.mark_elements_valid()
            cache.mark_composite_valid()
            self.assertTrue(cache.background_valid)
            self.assertTrue(cache.elements_valid)
            self.assertTrue(cache.composite_valid)

            cache.invalidate_background()
            self.assertFalse(cache.background_valid)
            self.assertFalse(cache.elements_valid)
            self.assertFalse(cache.composite_valid)

    def test_theme_change_then_element_change_before_draw(self):
        """Theme (invalidate_background) followed by element change before draw.
        Background invalidation already set all three dirty, so the second
        invalidate_composite is a no-op on state."""
        cache = self._warmed_cache()

        cache.invalidate_background()   # theme change
        cache.invalidate_composite()    # element added (redundant)

        self.assertFalse(cache.background_valid)
        self.assertFalse(cache.elements_valid)
        self.assertFalse(cache.composite_valid)

        # single full re-render
        cache.mark_background_valid()
        cache.mark_elements_valid()
        cache.mark_composite_valid()
        self.assertTrue(cache.background_valid)
        self.assertTrue(cache.elements_valid)
        self.assertTrue(cache.composite_valid)


if __name__ == "__main__":
    unittest.main()

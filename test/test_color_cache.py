import unittest
from meerk40t import svgelements
from meerk40t.core import color_cache


class TestColorCache(unittest.TestCase):
    def setUp(self):
        color_cache.uninstall_color_cache()
        color_cache.clear_color_cache()

    def test_install_and_class_helpers(self):
        self.assertFalse(color_cache.install_color_cache() is False)
        self.assertTrue(hasattr(svgelements.Color, "parse"))
        # parse returns integer color
        val = svgelements.Color.parse("#ff0000")
        self.assertIsInstance(val, int)

    def test_caching_and_wrapper(self):
        color_cache.install_color_cache()
        c1 = svgelements.Color("#ff8800")
        c2 = svgelements.Color("#ff8800")
        # wrappers should wrap the same underlying object
        self.assertTrue(hasattr(c1, "_color"))
        self.assertIs(c1._color, c2._color)
        # delegated behavior
        self.assertEqual(str(c1), str(c1._color))
        self.assertEqual(int(c1), int(c1._color))

    def test_unhashable_args_fallback(self):
        color_cache.install_color_cache()

        class Unhashable:
            def __init__(self):
                self.r = 10
                self.g = 20
                self.b = 30

        x = Unhashable()
        # constructing with an unsupported object raises TypeError (same as original Color)
        with self.assertRaises(TypeError):
            svgelements.Color(x)

    def test_robust_against_nested_color_value(self):
        """Simulate corrupted state where underlying .value is itself a Color/CachedColor
        and ensure equality comparisons don't raise a TypeError (regression case).

        Also test the original unpatched `Color` class to ensure its `__eq__`
        is robust when .value is accidentally a `Color` instance.
        """
        # Cached wrapper scenario
        color_cache.install_color_cache()
        a = svgelements.Color('#ff0000')
        # Forcibly set underlying value to a Color object (bad state observed in runtime)
        a._color.value = svgelements.Color('#00ff00')
        # Should not raise and should evaluate equality correctly
        self.assertTrue(a == '#00ff00')

        # Original class scenario (no cache installed)
        color_cache.uninstall_color_cache()
        a2 = svgelements.Color('#ff0000')
        b2 = svgelements.Color('#00ff00')
        # Assign b2 (a Color instance) into a2.value simulating corruption
        a2.value = b2
        self.assertTrue(a2 == '#00ff00')


    def test_clear_and_uninstall(self):
        color_cache.install_color_cache()
        svgelements.Color("#010203")
        self.assertGreater(color_cache.get_cache_stats()["cached_colors"], 0)
        color_cache.clear_color_cache()
        self.assertEqual(color_cache.get_cache_stats()["cached_colors"], 0)
        self.assertTrue(color_cache.uninstall_color_cache())
        # After uninstall class should be restored to original
        self.assertIs(svgelements.Color, color_cache.ColorClass())

    def test_cached_equality_and_abs(self):
        """Verify cached wrapper delegates core behaviors like equality, abs, repr, str, and int."""
        color_cache.install_color_cache()
        c = svgelements.Color("#112233")
        # equality with string
        self.assertTrue(c == "#112233")
        # equality with int
        self.assertTrue(c == int(c._color.value))
        # equality with another wrapper for same spec
        c2 = svgelements.Color("#112233")
        self.assertTrue(c == c2)
        # repr/str/int delegation
        self.assertEqual(str(c), str(c._color))
        self.assertEqual(int(c), int(c._color))
        self.assertEqual(repr(c), repr(c._color))
        # abs should return opaque color (delegate)
        a = abs(c)
        self.assertIn(str(a).lower(), ("#112233", "#112233ff"))

    def test_cached_numeric_bitwise_and_and_hash(self):
        """Verify numeric ops and hashing work on the cached wrapper."""
        color_cache.install_color_cache()
        c = svgelements.Color("#123456")
        mask = 0xFFFFFFFF
        self.assertEqual((int(c) & mask), (c & mask))
        self.assertEqual((mask & int(c)), (mask & c))
        # hash is stable and derived from underlying value
        self.assertEqual(hash(c), hash(c._color.value))

    def test_cached_matches_original_properties(self):
        """Compare outputs of many properties/methods between original Color and cached wrapper."""
        specs = [
            "#ff0000",
            "#112233",
            "rgb(10,20,30)",
            "rgba(10,20,30,0.5)",
            "hsl(180,50%,50%)",
            "transparent",
            "red",
            "#00000000",
        ]
        color_cache.install_color_cache()
        orig_cls = color_cache.ColorClass()
        for spec in specs:
            with self.subTest(spec=spec):
                cached = svgelements.Color(spec)
                orig = orig_cls(spec)

                # Basic delegations
                self.assertEqual(int(orig), int(cached), f"int() mismatch for {spec}")
                self.assertEqual(str(orig), str(cached), f"str() mismatch for {spec}")
                self.assertEqual(repr(orig), repr(cached), f"repr() mismatch for {spec}")

                # Properties
                props = [
                    "hex",
                    "hexrgb",
                    "hexa",
                    "rgba",
                    "argb",
                    "rgb",
                    "red",
                    "green",
                    "blue",
                    "alpha",
                    "opacity",
                    "hue",
                    "saturation",
                    "lightness",
                    "hsl",
                    "intensity",
                    "brightness",
                    "blackness",
                    "luminance",
                    "luma",
                ]
                for p in props:
                    self.assertEqual(getattr(orig, p), getattr(cached, p), f"{p} mismatch for {spec}")

                # Class-level helpers
                self.assertEqual(orig_cls.parse(spec), svgelements.Color.parse(spec), f"parse() mismatch for {spec}")
                self.assertEqual(int(orig_cls.distinct(1)), int(svgelements.Color.distinct(1)), "distinct mismatch")

                # Equality behavior
                self.assertTrue(orig == cached)
                self.assertTrue(cached == orig)
                self.assertTrue(cached == spec or str(cached) == str(orig))

                # Over operator and distance
                other = orig_cls('#ffffff')
                self.assertEqual(orig_cls.over(orig, other), svgelements.Color.over(cached, other))
                self.assertEqual(orig_cls.distance(orig, other), svgelements.Color.distance(cached, other))


if __name__ == "__main__":
    unittest.main()

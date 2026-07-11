import unittest

from test import bootstrap

from meerk40t.core.units import Length


class TestConsoleSetTyped(unittest.TestCase):
    def test_set_keeps_typed_value_live(self):
        """
        `set` on a Length-typed registered setting must keep the live
        attribute typed (consumers call e.g. `.mm`), not replace it with str.
        """
        kernel = bootstrap.bootstrap()
        try:
            root = kernel.root
            root.setting(Length, "typed_test_length", Length("235mm"))
            kernel.console("set typed_test_length 410mm\n")
            value = root.typed_test_length
            self.assertIsInstance(value, Length)
            self.assertAlmostEqual(value.mm, 410.0)
        finally:
            kernel()

    def test_set_unknown_attribute_reports(self):
        """
        `set` on a missing attribute must not create it.
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel.console("set no_such_attribute_xyz 5\n")
            self.assertFalse(hasattr(kernel.root, "no_such_attribute_xyz"))
        finally:
            kernel()

    def test_typed_setting_round_trip_persistence(self):
        """
        Length-typed settings must survive write_persistent_dict and read
        back through the registered type.
        """
        kernel = bootstrap.bootstrap()
        try:
            settings = kernel  # Kernel subclasses Settings
            settings.write_persistent_dict(
                "typed_test", {"width": Length("410mm"), "plain": 5}
            )
            stored = settings.read_persistent(str, "typed_test", "width")
            self.assertEqual(str(Length(stored)), str(Length("410mm")))
            self.assertEqual(
                settings.read_persistent(int, "typed_test", "plain"), 5
            )
        finally:
            kernel()


if __name__ == "__main__":
    unittest.main()

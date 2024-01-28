import unittest

from meerk40t.core.units import Length


class TestElementLength(unittest.TestCase):
    """Tests the functionality of the Length Element."""

    def test_length_init(self):
        self.assertRaises(ValueError, lambda: Length("12garbage"))

    def test_length_init2(self):
        self.assertRaises(ValueError, lambda: Length(amount="12garbage"))

    def test_length_parsing(self):
        self.assertAlmostEqual(Length("10cm"), (Length("100mm")))
        self.assertNotEqual(Length("1mm"), 0)
        self.assertNotEqual(Length("1cm"), 0)
        self.assertNotEqual(Length("1in"), 0)
        self.assertNotEqual(Length("1px"), 0)
        self.assertNotEqual(Length("1pc"), 0)
        self.assertNotEqual(Length("1pt"), 0)
        self.assertNotEqual(Length("1%", relative_length=100), 0)
        self.assertEqual(Length("50%", relative_length=100), 50.0)

    def test_length_division(self):
        self.assertAlmostEqual(Length("1mm") // Length("1mm"), 1.0)
        self.assertAlmostEqual(Length("1mm") / Length("1mm"), 1.0)
        self.assertAlmostEqual(Length("1in") / "1in", 1.0)
        self.assertAlmostEqual(Length("1cm") / "1mm", 10.0)

    def test_length_multiplication(self):
        self.assertEqual(Length("1mm") * 10, Length("1cm"))

    def test_length_addition(self):
        a = Length("0mm", digits=2)
        a += "2in"
        a += "2mil"
        a *= 1.7
        self.assertEqual(str(a), "86.45mm")
        self.assertEqual(a.mm, 86.45)

        self.assertEqual(a.um, 86446.36)
        self.assertEqual(a.cm, 8.64)

    def test_length_compare(self):
        self.assertTrue(Length("1in") < Length("2.6cm"))
        self.assertTrue(Length("1in") < "2.6cm")
        self.assertFalse(Length("1in") < "2.5cm")
        self.assertTrue(Length("10mm") >= "1cm")
        self.assertTrue(Length("10mm") <= "1cm")
        self.assertTrue(Length("11mm") >= "1cm")
        self.assertTrue(Length("10mm") <= "1.1cm")
        self.assertFalse(Length("11mm") <= "1cm")
        self.assertFalse(Length("10mm") >= "1.1cm")
        self.assertRaises(ValueError, lambda: Length("20%") > "1in")
        self.assertEqual(max(Length("1in"), Length("2.5cm")), "1in")

import unittest

from src.tools.calculator import calculate


class CalculatorTests(unittest.TestCase):
    def test_operator_precedence(self):
        self.assertEqual(calculate("2 + 3 * 4"), 14.0)

    def test_square_root(self):
        self.assertEqual(calculate("sqrt(16)"), 4.0)

    def test_trigonometric_function(self):
        self.assertAlmostEqual(calculate("sin(pi / 2)"), 1.0)

    def test_dangerous_expression_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate("__import__('os').system('dir')")


if __name__ == "__main__":
    unittest.main()

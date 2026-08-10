import unittest

from app.pbm_model.metrics import calculate_gof, fit_statistics


class MetricTests(unittest.TestCase):
    def test_perfect_fit_statistics(self):
        statistics = fit_statistics([1, 2, 3, 4], [1, 2, 3, 4], parameter_count=1)
        self.assertEqual(statistics["sse"], 0.0)
        self.assertEqual(statistics["rmse"], 0.0)
        self.assertEqual(statistics["r_squared"], 1.0)
        self.assertEqual(statistics["gof_percent"], 100.0)

    def test_gof_requires_positive_degrees_of_freedom(self):
        with self.assertRaisesRegex(ValueError, "four fit points"):
            calculate_gof([1, 2, 3], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()

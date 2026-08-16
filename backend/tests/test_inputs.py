import unittest

import numpy as np

from app.pbm_model.optimization_simulation import _read_experimental_csv, _read_initial_moments


VALID_EXPERIMENT = """;BHMW;
;14 mg/g;
Time(min);d43;DF
0;0.414;1.65
0.5;11.525;1.65
1.4;23.135;1.7925
2.3;26.589;1.8982
3.3;32.217;1.9764
dF 0;;1.79
dF max;;2.19
"""


class InputValidationTests(unittest.TestCase):
    def test_explicit_df_max_footer_is_required(self):
        measurements, df_max, df0 = _read_experimental_csv(VALID_EXPERIMENT)
        self.assertEqual(len(measurements), 5)
        self.assertAlmostEqual(df_max, 2.19)
        self.assertAlmostEqual(df0, 1.79)

        without_footer = VALID_EXPERIMENT.replace("dF max;;2.19\n", "")
        with self.assertRaisesRegex(ValueError, "dF max"):
            _read_experimental_csv(without_footer)

    def test_explicit_df0_footer_is_required(self):
        without_df0 = VALID_EXPERIMENT.replace("dF 0;;1.79\n", "")
        with self.assertRaisesRegex(ValueError, "dF 0"):
            _read_experimental_csv(without_df0)

    def test_time_must_start_at_zero_and_increase_strictly(self):
        shifted = VALID_EXPERIMENT.replace("0;0.414", "0.1;0.414", 1)
        with self.assertRaisesRegex(ValueError, "start at 0"):
            _read_experimental_csv(shifted)

        duplicate = VALID_EXPERIMENT.replace("0.5;11.525", "0;11.525")
        with self.assertRaisesRegex(ValueError, "increase strictly"):
            _read_experimental_csv(duplicate)

        unsorted = VALID_EXPERIMENT.replace("0.5;11.525", "1.5;11.525")
        with self.assertRaisesRegex(ValueError, "increase strictly"):
            _read_experimental_csv(unsorted)

    def test_moment_file_requires_exactly_five_positive_values(self):
        moments = _read_initial_moments("value\n1\n0.679\n0.82\n1.8\n7\n")
        np.testing.assert_allclose(moments, [1, 0.679, 0.82, 1.8, 7])
        with self.assertRaisesRegex(ValueError, "exactly five"):
            _read_initial_moments("value\n1\n2\n3\n4\n")
        with self.assertRaisesRegex(ValueError, "positive"):
            _read_initial_moments("value\n1\n2\n3\n4\n-5\n")


if __name__ == "__main__":
    unittest.main()

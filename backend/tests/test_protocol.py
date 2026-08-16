import unittest

import numpy as np
import pandas as pd

from app.pbm_model.eqmom import fit_gamma
from app.pbm_model.optimization import PROTOCOL_VERSION, _prepare_optimization


class ProtocolTests(unittest.TestCase):
    def test_material_name_does_not_change_shear_rate_or_fit_window(self):
        data = pd.DataFrame(
            {
                "Time(min)": [0.0, 0.5, 1.4, 2.3],
                "d43": [0.414, 11.525, 23.135, 26.589],
                "DF": [1.65, 1.65, 1.7925, 1.8982],
            }
        )
        model, _, _, _, _, fit_indices = _prepare_optimization(
            data,
            700,
            100,
            np.array([1, 0.57, 0.82, 1.8, 7]),
            2.19,
        )
        self.assertEqual(PROTOCOL_VERSION, "EQMOM-PCC-2STAGE-1.2")
        self.assertEqual(model.shear_rate, 700)
        np.testing.assert_array_equal(fit_indices, [1, 2, 3])

    def test_explicit_df0_is_independent_from_first_experimental_df(self):
        data = pd.DataFrame(
            {
                "Time(min)": [0.0, 0.5, 1.4, 2.3],
                "d43": [2.73, 79.307, 101.558, 92.93],
                "DF": [1.65, 1.79, 2.09, 2.23],
            }
        )
        model, gamma, _, _, _, _ = _prepare_optimization(
            data,
            312,
            100,
            np.array([1, 1.3997, 2.4478, 5.3484, 14.601]),
            2.39,
            df0=1.79,
        )
        self.assertAlmostEqual(data["DF"].iloc[0], 1.65)
        self.assertAlmostEqual(model.df0, 1.79)
        self.assertGreater(gamma, 0.0)

    def test_e3_8_matlab_default_df0_reproduces_published_gamma(self):
        time = np.array(
            [0, 0.5, 1.4, 2.3, 3.3, 4.2, 5.1, 6, 6.9, 7.9, 8.8, 9.7, 10.6, 11.5, 12.5, 13.4, 14.3]
        )
        observed_df = np.array(
            [1.65, 1.59, 2.08, 2.24, 2.34, 2.4, 2.45, 2.48, 2.51, 2.53, 2.54, 2.55, 2.56, 2.56, 2.57, 2.58, 2.58]
        )
        gamma, _ = fit_gamma(time, observed_df, 2.58, df0=observed_df[0])
        self.assertAlmostEqual(gamma, 0.382221467, places=8)


if __name__ == "__main__":
    unittest.main()

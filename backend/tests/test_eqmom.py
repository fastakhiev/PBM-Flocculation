import unittest

import numpy as np

from app.pbm_model.eqmom import (
    EQMOMCancelled,
    EQMOMConfig,
    _two_node_lognormal,
    fit_gamma,
    moments_from_distribution,
    simulate_eqmom,
)


TIME_E2_6 = np.array(
    [0, 0.5, 1.4, 2.3, 3.3, 4.2, 5.1, 6.0, 6.9, 7.9, 8.8, 9.7, 10.6, 11.5, 12.5, 13.4, 14.3]
)
DF_E2_6 = np.array(
    [1.65, 1.91, 2.14, 2.23, 2.30, 2.35, 2.39, 2.43, 2.47, 2.50, 2.60, 2.59, 2.59, 2.63, 2.59, 2.57, 2.55]
)
MOMENTS_E2_6 = np.array([1.0, 1.0439, 1.3993, 2.4084, 5.3226])
TIME_BHMW_14 = np.array(
    [0, 0.5, 1.4, 2.3, 3.3, 4.2, 5.1, 6.0, 6.9, 7.9, 8.8, 9.7, 10.6, 11.5, 12.5, 13.4, 14.3]
)
DF_BHMW_14 = np.array(
    [1.65, 1.65, 1.7925, 1.8982, 1.9764, 2.0343, 2.0773, 2.1091, 2.1326,
     2.1501, 2.163, 2.1726, 2.1797, 2.185, 2.1889, 2.1918, 2.1939]
)


class EQMOMTests(unittest.TestCase):
    def test_e1_8_gamma_uses_the_documented_df_max(self):
        time = np.array([0, 0.5, 1.4, 2.3, 3.3, 4.2, 5.1, 6.0, 6.9, 7.8, 8.8, 9.7, 10.6, 11.5, 12.4, 13.3])
        df = np.array([1.6, 1.85, 2.13, 2.22, 2.3, 2.34, 2.36, 2.38, 2.4, 2.4, 2.41, 2.42, 2.42, 2.41, 2.41, 2.41])
        gamma, _ = fit_gamma(time, df, 2.51)
        self.assertAlmostEqual(gamma, 0.429977445, delta=5e-8)

    def test_gamma_matches_matlab_control_case(self):
        gamma, error = fit_gamma(TIME_E2_6, DF_E2_6, 2.55)
        self.assertAlmostEqual(gamma, 0.4329231, places=6)
        self.assertGreaterEqual(error, 0.0)

    def test_bhmw_gamma_uses_every_measurement_after_time_zero(self):
        gamma, error = fit_gamma(TIME_BHMW_14, DF_BHMW_14, 2.19)
        explicit_gamma, explicit_error = fit_gamma(
            TIME_BHMW_14,
            DF_BHMW_14,
            2.19,
            fit_indices=np.arange(1, TIME_BHMW_14.size),
        )
        self.assertAlmostEqual(gamma, explicit_gamma, places=12)
        self.assertAlmostEqual(error, explicit_error, places=12)
        self.assertGreaterEqual(error, 0.0)

    def test_distribution_is_converted_to_normalized_moments(self):
        moments = moments_from_distribution([1, 1], df0=2.0, primary_diameter_nm=100)
        diameters = np.array([0.1, 0.1 * np.sqrt(2.0)])
        expected = np.array([np.mean(diameters**order) for order in range(5)])
        np.testing.assert_allclose(moments, expected)

    def test_lognormal_inversion_uses_first_matlab_canonical_boundary(self):
        weights, nodes, sigma = _two_node_lognormal(
            np.array([1.0, 0.57, 0.82, 1.8, 7.0])
        )
        self.assertAlmostEqual(sigma**2, 0.42256962419625416, places=12)
        self.assertAlmostEqual(nodes[0], 2.77555756e-16, delta=1e-24)
        self.assertTrue(np.all(weights >= 0.0))
        self.assertTrue(np.all(nodes > 0.0))

    def test_e2_6_table_parameters_produce_finite_reference_trajectory(self):
        gamma, _ = fit_gamma(TIME_E2_6, DF_E2_6, 2.55)
        config = EQMOMConfig(
            time_minutes=TIME_E2_6,
            moments0=MOMENTS_E2_6,
            df0=DF_E2_6[0],
            df_max=2.55,
            shear_rate=312,
            primary_diameter_nm=100,
        )
        d43, predicted_df = simulate_eqmom(0.80, 49.2, gamma, config)
        self.assertTrue(np.all(np.isfinite(d43)))
        self.assertAlmostEqual(d43[0], 2.21, places=2)
        self.assertAlmostEqual(d43[-1], 44.9401, places=3)
        self.assertAlmostEqual(predicted_df[-1], 2.5481, places=3)

    def test_simulation_honors_cancellation(self):
        config = EQMOMConfig(
            time_minutes=np.array([0.0, 0.1]),
            moments0=MOMENTS_E2_6,
            df0=1.65,
            df_max=2.55,
            shear_rate=312,
            primary_diameter_nm=100,
            cancel_check=lambda: True,
        )
        with self.assertRaises(EQMOMCancelled):
            simulate_eqmom(0.8, 49.2, 0.43, config)


if __name__ == "__main__":
    unittest.main()

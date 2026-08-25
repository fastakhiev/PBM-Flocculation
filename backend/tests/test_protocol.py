import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from app.pbm_model.optimization import (
    PROTOCOL_VERSION,
    _prepare_optimization,
    _run_multistart_least_squares,
    _stage_two_functions,
)


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
        self.assertEqual(PROTOCOL_VERSION, "EQMOM-PCC-2STAGE-1.6")
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

    def test_python_multistart_finds_the_best_valid_least_squares_solution(self):
        def residual(parameters):
            return np.array([parameters[0] - 0.35, (parameters[1] - 56.0) / 100.0])

        residual.invalid_sse = 1e6
        with patch(
            "app.pbm_model.optimization.MULTISTART_POINTS",
            ((0.1, 20.0), (0.8, 200.0)),
        ):
            parameters, error = _run_multistart_least_squares(residual)

        np.testing.assert_allclose(parameters, [0.35, 56.0], rtol=0.0, atol=1e-6)
        self.assertLess(error, 1e-12)

    def test_python_multistart_refines_every_supplied_start(self):
        def residual(parameters):
            residual.last_valid = True
            return np.asarray(parameters, dtype=float)

        residual.invalid_sse = 1e6
        residual.last_valid = False
        starts = ((0.1, 20.0), (0.5, 80.0), (0.9, 200.0))
        with (
            patch("app.pbm_model.optimization.MULTISTART_POINTS", starts),
            patch("app.pbm_model.optimization.least_squares") as solver,
        ):
            _run_multistart_least_squares(residual)

        self.assertEqual(solver.call_count, len(starts))
        for call, start in zip(solver.call_args_list, starts, strict=True):
            np.testing.assert_allclose(call.args[1], start)

    def test_invalid_residual_preserves_matlab_search_direction(self):
        context = SimpleNamespace(gamma=0.4, model=object())
        observed = np.array([1.0, 2.0, 3.0])

        with patch(
            "app.pbm_model.optimization.simulate_eqmom",
            side_effect=ValueError("invalid trajectory"),
        ):
            _, residual = _stage_two_functions(context, observed)
            low_alpha = residual(np.array([0.1, 300.0]))
            high_alpha = residual(np.array([0.9, 20.0]))

        self.assertFalse(np.array_equal(low_alpha, high_alpha))
        self.assertGreater(float(low_alpha @ low_alpha), residual.invalid_sse)
        self.assertGreater(float(high_alpha @ high_alpha), residual.invalid_sse)
        self.assertFalse(residual.last_valid)

    def test_valid_candidate_is_kept_even_when_sse_exceeds_invalid_penalty(self):
        def residual(parameters):
            residual.last_valid = True
            return np.array([100.0 + parameters[0], 100.0 + parameters[1]])

        residual.invalid_sse = 1.0
        residual.last_valid = False
        with patch(
            "app.pbm_model.optimization.MULTISTART_POINTS",
            ((0.1, 20.0),),
        ):
            parameters, error = _run_multistart_least_squares(residual)

        self.assertIsNotNone(parameters)
        self.assertGreater(error, residual.invalid_sse)


if __name__ == "__main__":
    unittest.main()

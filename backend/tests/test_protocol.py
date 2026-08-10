import unittest

import numpy as np
import pandas as pd

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
            np.array([1, 0.679, 0.82, 1.8, 7]),
            2.19,
        )
        self.assertEqual(PROTOCOL_VERSION, "EQMOM-PCC-2STAGE-1.0")
        self.assertEqual(model.shear_rate, 700)
        np.testing.assert_array_equal(fit_indices, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()

import numpy as np
import pandas as pd

from app.pbm_model.eqmom import EQMOMConfig, simulate_eqmom


def run_realtime_simulation(
    opt_params, csv_data, G, do, dFmax_val, initial_state=None, cancel_check=None
):
    del initial_state  # EQMOM simulation always starts from the calibrated initial moments.
    moments = np.asarray(opt_params.get("moments", []), dtype=float)
    if moments.shape != (5,):
        raise ValueError("Initial EQMOM moments are missing. Run optimization again before simulation.")

    experimental_time = csv_data["Time(min)"].to_numpy(dtype=float)
    relative_time = experimental_time - experimental_time[0]
    end_time = float(relative_time[-1])
    display_step = 0.1
    dense_time = np.arange(0.0, end_time + display_step / 2.0, display_step)
    if dense_time[-1] < end_time:
        dense_time = np.append(dense_time, end_time)
    else:
        dense_time[-1] = end_time

    config = EQMOMConfig(
        time_minutes=dense_time,
        moments0=moments,
        df0=float(csv_data["DF"].iloc[0]),
        df_max=float(dFmax_val),
        shear_rate=float(G),
        primary_diameter_nm=float(do),
        cancel_check=cancel_check,
    )
    d43_model, df_model = simulate_eqmom(
        float(opt_params["amax"]),
        float(opt_params["B"]),
        float(opt_params["gama"]),
        config,
    )
    results_df = pd.DataFrame(
        {
            "time": dense_time,
            # Keep the existing response names so the current frontend remains compatible.
            "VMD_corrected": d43_model,
            "DF_corrected": df_model,
            "VMD_pure_forecast": d43_model,
        }
    )
    return results_df, None

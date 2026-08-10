import numpy as np


def fit_statistics(observed, predicted, *, parameter_count: int) -> dict[str, float | int | None]:
    observed_array = np.asarray(observed, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    if observed_array.shape != predicted_array.shape or observed_array.ndim != 1:
        raise ValueError("Observed and predicted values must be one-dimensional arrays of equal length.")
    if observed_array.size == 0 or np.any(~np.isfinite(observed_array)) or np.any(~np.isfinite(predicted_array)):
        raise ValueError("Fit statistics require finite, non-empty arrays.")

    residual = predicted_array - observed_array
    sse = float(residual @ residual)
    rmse = float(np.sqrt(np.mean(residual**2)))
    centered = observed_array - np.mean(observed_array)
    total_sum_squares = float(centered @ centered)
    r_squared = None if total_sum_squares <= 0 else float(1.0 - sse / total_sum_squares)

    degrees_of_freedom = int(observed_array.size - parameter_count)
    standard_error = None if degrees_of_freedom <= 0 else float(np.sqrt(sse / degrees_of_freedom))
    mean_observed = float(np.mean(observed_array))
    gof_percent = None
    if standard_error is not None and mean_observed != 0:
        gof_percent = float(100.0 * (mean_observed - standard_error) / mean_observed)

    return {
        "n": int(observed_array.size),
        "parameter_count": int(parameter_count),
        "degrees_of_freedom": degrees_of_freedom,
        "sse": sse,
        "rmse": rmse,
        "r_squared": r_squared,
        "standard_error": standard_error,
        "gof_percent": gof_percent,
    }


def calculate_gof(d_exp, d_model):
    statistics = fit_statistics(d_exp, d_model, parameter_count=3)
    if statistics["gof_percent"] is None:
        raise ValueError("At least four fit points are required to calculate GOF.")
    return statistics["gof_percent"]

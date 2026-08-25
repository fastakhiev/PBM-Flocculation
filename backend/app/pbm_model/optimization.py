import os
import time
from typing import Callable

import numpy as np
from scipy.optimize import least_squares

from app.pbm_model.eqmom import (
    EQMOMConfig,
    EQMOMError,
    SINGLE_NODE_PROJECTION_LOG_TOLERANCE,
    fit_gamma,
    simulate_eqmom,
)
from app.pbm_model.metrics import fit_statistics


MULTISTART_MAX_EVALUATIONS = 3000
MULTISTART_FUNCTION_TOLERANCE = 1e-9
MULTISTART_STEP_TOLERANCE = 1e-9
MULTISTART_OPTIMALITY_TOLERANCE = 1e-8
MULTISTART_POINTS = (
    (0.10, 20.0),
    (0.15, 30.0),
    (0.20, 40.0),
    (0.25, 50.0),
    (0.30, 50.0),
    (0.35, 55.0),
    (0.35, 60.0),
    (0.40, 65.0),
    (0.45, 70.0),
    (0.50, 75.0),
    (0.55, 80.0),
    (0.60, 85.0),
    (0.65, 90.0),
    (0.70, 95.0),
    (0.75, 100.0),
    (0.80, 110.0),
    (0.85, 120.0),
    (0.90, 130.0),
    (0.95, 140.0),
    (0.99, 400.0),
)

ALPHA_BOUNDS = (1e-6, 1.0)
B_BOUNDS = (1e-8, 360.0)
PROTOCOL_VERSION = "EQMOM-PCC-2STAGE-1.6"


class OptimizationCancelled(RuntimeError):
    pass


def _raise_if_cancelled(cancel_check: Callable[[], bool] | None) -> None:
    if cancel_check is not None and cancel_check():
        raise OptimizationCancelled("Optimization was cancelled.")


def make_eqmom_config(csv_data, G, do, moments, df_max, cancel_check=None, df0=None):
    time_values = csv_data["Time(min)"].to_numpy(dtype=float)
    relative_time = time_values - time_values[0]
    df_values = csv_data["DF"].to_numpy(dtype=float)
    return EQMOMConfig(
        time_minutes=relative_time,
        moments0=np.asarray(moments, dtype=float),
        df0=float(df_values[0]) if df0 is None else float(df0),
        df_max=float(df_max),
        shear_rate=float(G),
        primary_diameter_nm=float(do),
        dt_seconds=float(os.getenv("PBM_EQMOM_DT_SECONDS", "1.0")),
        cancel_check=cancel_check,
    )


def _stage_two_functions(config, observed_d43, fit_indices=None, cancel_check=None):
    observed = np.asarray(observed_d43, dtype=float)
    indices = (
        np.arange(1, observed.size, dtype=int)
        if fit_indices is None
        else np.asarray(fit_indices, dtype=int)
    )
    if indices.ndim != 1 or indices.size < 2:
        raise ValueError("At least two d43 measurements are required for Stage 2.")
    scale = max(float(np.std(observed[indices], ddof=1)), 1.0)
    penalty = indices.size * (4.0 * scale) ** 2

    def invalid_residual(parameters):
        parameter_lower = np.array([ALPHA_BOUNDS[0], B_BOUNDS[0]])
        parameter_span = np.array(
            [
                ALPHA_BOUNDS[1] - ALPHA_BOUNDS[0],
                B_BOUNDS[1] - B_BOUNDS[0],
            ]
        )
        normalized = (
            np.asarray(parameters, dtype=float) - parameter_lower
        ) / parameter_span
        direction = normalized[0] - normalized[1]
        return (
            4.0 * scale
            + 0.05 * scale * direction * np.linspace(-1.0, 1.0, indices.size)
        )

    def residual(parameters):
        _raise_if_cancelled(cancel_check)
        try:
            predicted, _ = simulate_eqmom(
                float(parameters[0]),
                float(parameters[1]),
                config.gamma,
                config.model,
            )
            values = predicted[indices] - observed[indices]
            if np.any(~np.isfinite(values)):
                residual.last_valid = False
                return invalid_residual(parameters)
            residual.last_valid = True
            return values
        except (EQMOMError, ValueError, FloatingPointError, np.linalg.LinAlgError):
            residual.last_valid = False
            return invalid_residual(parameters)

    def objective(parameters):
        values = residual(parameters)
        return float(values @ values)

    residual.invalid_sse = penalty
    residual.last_valid = False
    return objective, residual


class _OptimizationContext:
    def __init__(self, model: EQMOMConfig, gamma: float):
        self.model = model
        self.gamma = gamma


def _prepare_optimization(csv_data, G, do, moments, df_max, cancel_check=None, df0=None):
    # The supplied MATLAB protocol excludes only the initial measurement,
    # which is fixed by the initial conditions. No material-specific fitting
    # windows or substituted operating conditions are applied.
    fit_indices = np.arange(1, len(csv_data), dtype=int)
    model = make_eqmom_config(csv_data, G, do, moments, df_max, cancel_check, df0)
    df_exp = csv_data["DF"].to_numpy(dtype=float)
    gamma, gamma_sse = fit_gamma(
        model.time_minutes,
        df_exp,
        model.df_max,
        df0=model.df0,
        fit_indices=fit_indices,
    )
    context = _OptimizationContext(model, gamma)
    objective, residual = _stage_two_functions(
        context,
        csv_data["d43"].to_numpy(dtype=float),
        fit_indices=fit_indices,
        cancel_check=cancel_check,
    )
    return model, gamma, gamma_sse, objective, residual, fit_indices


def _run_multistart_least_squares(residual, cancel_check=None):
    lower = np.array([ALPHA_BOUNDS[0], B_BOUNDS[0]], dtype=float)
    upper = np.array([ALPHA_BOUNDS[1], B_BOUNDS[1]], dtype=float)
    best_parameters = None
    best_error = np.inf

    def is_valid(error):
        return bool(
            getattr(
                residual,
                "last_valid",
                error < float(residual.invalid_sse) * (1.0 - 1e-12),
            )
        )

    def tracked_residual(parameters):
        nonlocal best_parameters, best_error
        values = residual(parameters)
        error = float(values @ values)
        if (
            np.all(np.isfinite(parameters))
            and np.isfinite(error)
            and is_valid(error)
            and error < best_error
        ):
            best_parameters = np.asarray(parameters, dtype=float).copy()
            best_error = error
        return values

    for raw_start in MULTISTART_POINTS:
        _raise_if_cancelled(cancel_check)
        start = np.clip(np.asarray(raw_start, dtype=float), lower, upper)
        try:
            least_squares(
                tracked_residual,
                start,
                bounds=(lower, upper),
                method="trf",
                jac="2-point",
                ftol=MULTISTART_FUNCTION_TOLERANCE,
                xtol=MULTISTART_STEP_TOLERANCE,
                gtol=MULTISTART_OPTIMALITY_TOLERANCE,
                max_nfev=MULTISTART_MAX_EVALUATIONS,
            )
        except (EQMOMError, ValueError, FloatingPointError, np.linalg.LinAlgError):
            continue

    _raise_if_cancelled(cancel_check)
    return best_parameters, best_error


def _optimization_response(
    parameters,
    best_fun,
    gamma,
    gamma_sse,
    model,
    G,
    do,
    e1_index,
    dosage,
    elapsed,
    message,
    observed_d43,
    observed_df,
    fit_indices,
    algorithm,
):
    predicted_d43, predicted_df = simulate_eqmom(
        parameters[0], parameters[1], gamma, model
    )
    d43_metrics = fit_statistics(
        observed_d43[fit_indices], predicted_d43[fit_indices], parameter_count=3
    )
    df_metrics = fit_statistics(
        observed_df[fit_indices], predicted_df[fit_indices], parameter_count=1
    )
    initial_model_d43 = float(predicted_d43[0])
    initial_experimental_d43 = float(observed_d43[0])
    relative_initial_difference = (
        abs(initial_model_d43 - initial_experimental_d43)
        / initial_experimental_d43
    )
    warnings = []
    if relative_initial_difference > 0.05:
        warnings.append(
            "Initial M4/M3 differs from experimental d43 by more than 5%; "
            "verify the moment normalization and d43 units."
        )
    df_above_max_count = int(
        np.count_nonzero(np.asarray(observed_df, dtype=float) > model.df_max)
    )
    if df_above_max_count:
        warnings.append(
            f"{df_above_max_count} experimental DF value(s) exceed DF_max; "
            "verify the limiting DF value and measurement rounding."
        )
    return {
        "success": True,
        "amax": float(parameters[0]),
        "B": float(parameters[1]),
        "gama": float(gamma),
        "df0": float(model.df0),
        "g": float(G),
        "do": float(do),
        "cpamm": e1_index,
        "dosage": int(dosage),
        "optimization_time": round(elapsed, 2),
        "error": float(best_fun),
        "df_error": float(gamma_sse),
        "metrics": {"d43": d43_metrics, "df": df_metrics},
        "moments": model.moments0.tolist(),
        "d43_model": predicted_d43.tolist(),
        "df_model": predicted_df.tolist(),
        "protocol": {
            "version": PROTOCOL_VERSION,
            "description": "Two-stage EQMOM calibration matching the supplied general MATLAB protocol.",
            "stage_1": "gamma fitted to DF at every measurement after time zero",
            "stage_2": "alpha_max and B fitted to d43 at every measurement after time zero",
            "fit_indices_zero_based": fit_indices.tolist(),
            "experimental_shear_rate_s-1": float(G),
            "model_shear_rate_s-1": float(model.shear_rate),
            "model_initial_df": float(model.df0),
            "experimental_initial_df": float(observed_df[0]),
            "dt_seconds": float(model.dt_seconds),
            "parameter_bounds": {"alpha_max": list(ALPHA_BOUNDS), "B": list(B_BOUNDS)},
            "model_constants": {
                "kinematic_viscosity_m2_s": float(model.kinematic_viscosity),
                "temperature_k": float(model.temperature),
                "boltzmann_constant_j_k": float(model.boltzmann_constant),
                "dynamic_viscosity_pa_s": float(model.dynamic_viscosity),
                "collision_x": float(model.collision_x),
                "collision_y": float(model.collision_y),
                "secondary_quadrature_order": int(model.secondary_quadrature_order),
                "d43_scale": float(model.d43_scale),
                "minimum_substep_seconds": float(model.minimum_substep_seconds),
                "maximum_substeps": int(model.maximum_substeps),
                "sigma_minimum": float(model.sigma_minimum),
                "single_node_projection_log_tolerance": (
                    SINGLE_NODE_PROJECTION_LOG_TOLERANCE
                ),
            },
        },
        "algorithm": algorithm,
        "trajectories": {
            "time_minutes": model.time_minutes.tolist(),
            "d43_experimental": np.asarray(observed_d43, dtype=float).tolist(),
            "d43_model": predicted_d43.tolist(),
            "df_experimental": np.asarray(observed_df, dtype=float).tolist(),
            "df_model": predicted_df.tolist(),
        },
        "diagnostics": {
            "initial_model_d43": initial_model_d43,
            "initial_experimental_d43": initial_experimental_d43,
            "relative_initial_difference": relative_initial_difference,
            "df_observed_above_df_max_count": df_above_max_count,
            "warnings": warnings,
        },
        "message": message,
    }


def run_optimization(
    csv_data, G, do, moments, df_max, e1_index, dosage, cancel_check=None, df0=None
):
    start_time = time.monotonic()
    model, gamma, gamma_sse, _objective, residual, fit_indices = _prepare_optimization(
        csv_data, G, do, moments, df_max, cancel_check, df0
    )
    parameters, best_fun = _run_multistart_least_squares(residual, cancel_check)
    elapsed = time.monotonic() - start_time
    if parameters is not None and np.isfinite(best_fun):
        return _optimization_response(
            parameters,
            best_fun,
            gamma,
            gamma_sse,
            model,
            G,
            do,
            e1_index,
            dosage,
            elapsed,
            "Two-stage Python multi-start least-squares optimization finished.",
            csv_data["d43"].to_numpy(dtype=float),
            csv_data["DF"].to_numpy(dtype=float),
            fit_indices,
            {
                "name": "Python Multi-start Least Squares (PMLS)",
                "solver": "scipy.optimize.least_squares",
                "method": "trust-region reflective",
                "finite_difference": "forward two-point",
                "supplied_start_points": [list(value) for value in MULTISTART_POINTS],
                "local_start_count": len(MULTISTART_POINTS),
                "invalid_starts_receive_finite_directional_residual": True,
                "function_tolerance": MULTISTART_FUNCTION_TOLERANCE,
                "step_tolerance": MULTISTART_STEP_TOLERANCE,
                "optimality_tolerance": MULTISTART_OPTIMALITY_TOLERANCE,
                "max_function_evaluations_per_start": MULTISTART_MAX_EVALUATIONS,
                "deterministic": True,
            },
        )
    return {
        "success": False,
        "message": "Python multi-start least-squares optimization failed to find a valid trajectory.",
    }

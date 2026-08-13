import os
import time
from contextlib import redirect_stdout
from typing import Callable

import numpy as np
from scipy.optimize import differential_evolution, least_squares

from app.pbm_model.eqmom import EQMOMConfig, EQMOMError, fit_gamma, simulate_eqmom
from app.pbm_model.metrics import fit_statistics


DE_MAXITER = int(os.getenv("PBM_DE_MAXITER", "50"))
DE_POPSIZE = int(os.getenv("PBM_DE_POPSIZE", "10"))
DE_TOL = float(os.getenv("PBM_DE_TOL", "0.02"))
GA_MAX_ITERATIONS = int(os.getenv("PBM_GA_MAX_ITERATIONS", "50"))
GA_POPULATION_SIZE = int(os.getenv("PBM_GA_POPULATION_SIZE", "30"))
GA_MAX_ITERATION_WITHOUT_IMPROV = int(os.getenv("PBM_GA_MAX_ITERATION_WITHOUT_IMPROV", "12"))
RANDOM_SEED = int(os.getenv("PBM_RANDOM_SEED", "2026"))
POLISH_TOLERANCE = 1e-7
POLISH_MAX_EVALUATIONS = 60
POLISH_START_FRACTIONS = ((0.25, 0.10), (0.50, 0.50), (0.75, 0.90))

ALPHA_BOUNDS = (1e-6, 1.0)
B_BOUNDS = (1e-8, 500.0)
PROTOCOL_VERSION = "EQMOM-PCC-2STAGE-1.1"


class OptimizationCancelled(RuntimeError):
    pass


def _raise_if_cancelled(cancel_check: Callable[[], bool] | None) -> None:
    if cancel_check is not None and cancel_check():
        raise OptimizationCancelled("Optimization was cancelled.")


def make_eqmom_config(csv_data, G, do, moments, df_max, cancel_check=None):
    time_values = csv_data["Time(min)"].to_numpy(dtype=float)
    relative_time = time_values - time_values[0]
    df_values = csv_data["DF"].to_numpy(dtype=float)
    return EQMOMConfig(
        time_minutes=relative_time,
        moments0=np.asarray(moments, dtype=float),
        df0=float(df_values[0]),
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
    scale = max(float(np.std(observed[indices])), 1.0)
    penalty = indices.size * (4.0 * scale) ** 2

    def residual(parameters):
        _raise_if_cancelled(cancel_check)
        try:
            predicted, _ = simulate_eqmom(float(parameters[0]), float(parameters[1]), config.gamma, config.model)
            values = predicted[indices] - observed[indices]
            if np.any(~np.isfinite(values)):
                return np.full(indices.size, np.sqrt(penalty / indices.size))
            return values
        except (EQMOMError, ValueError, FloatingPointError, np.linalg.LinAlgError):
            return np.full(indices.size, np.sqrt(penalty / indices.size))

    def objective(parameters):
        values = residual(parameters)
        return float(values @ values)

    return objective, residual


class _OptimizationContext:
    def __init__(self, model: EQMOMConfig, gamma: float):
        self.model = model
        self.gamma = gamma


def _prepare_optimization(csv_data, G, do, moments, df_max, cancel_check=None):
    # The supplied MATLAB protocol excludes only the initial measurement,
    # which is fixed by the initial conditions. No material-specific fitting
    # windows or substituted operating conditions are applied.
    fit_indices = np.arange(1, len(csv_data), dtype=int)
    model = make_eqmom_config(csv_data, G, do, moments, df_max, cancel_check)
    df_exp = csv_data["DF"].to_numpy(dtype=float)
    gamma, gamma_sse = fit_gamma(
        model.time_minutes,
        df_exp,
        model.df_max,
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


def _polish_candidate(parameters, residual, cancel_check=None):
    lower = np.array([ALPHA_BOUNDS[0], B_BOUNDS[0]])
    upper = np.array([ALPHA_BOUNDS[1], B_BOUNDS[1]])
    starts = [
        np.asarray(parameters, dtype=float),
        *(lower + np.asarray(fraction) * (upper - lower) for fraction in POLISH_START_FRACTIONS),
    ]
    best_parameters = starts[0]
    best_values = residual(best_parameters)
    best_error = float(best_values @ best_values)

    for start in starts:
        _raise_if_cancelled(cancel_check)
        try:
            result = least_squares(
                residual,
                start,
                bounds=(lower, upper),
                ftol=POLISH_TOLERANCE,
                xtol=POLISH_TOLERANCE,
                gtol=POLISH_TOLERANCE,
                max_nfev=POLISH_MAX_EVALUATIONS,
            )
            error = float(result.fun @ result.fun)
            if np.all(np.isfinite(result.x)) and np.isfinite(error) and error < best_error:
                best_parameters = result.x
                best_error = error
        except (EQMOMError, ValueError, FloatingPointError, np.linalg.LinAlgError):
            continue
    return np.asarray(best_parameters, dtype=float), best_error


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
    predicted_d43, predicted_df = simulate_eqmom(parameters[0], parameters[1], gamma, model)
    d43_metrics = fit_statistics(observed_d43[fit_indices], predicted_d43[fit_indices], parameter_count=3)
    df_metrics = fit_statistics(observed_df[fit_indices], predicted_df[fit_indices], parameter_count=1)
    initial_model_d43 = float(predicted_d43[0])
    initial_experimental_d43 = float(observed_d43[0])
    relative_initial_difference = abs(initial_model_d43 - initial_experimental_d43) / initial_experimental_d43
    warnings = []
    if relative_initial_difference > 0.05:
        warnings.append(
            "Initial M4/M3 differs from experimental d43 by more than 5%; "
            "verify the moment normalization and d43 units."
        )
    df_above_max_count = int(np.count_nonzero(np.asarray(observed_df, dtype=float) > model.df_max))
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
            "dt_seconds": float(model.dt_seconds),
            "random_seed": RANDOM_SEED,
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
            },
            "least_squares_polish": {
                "start_fractions": [list(value) for value in POLISH_START_FRACTIONS],
                "ftol": POLISH_TOLERANCE,
                "xtol": POLISH_TOLERANCE,
                "gtol": POLISH_TOLERANCE,
                "max_function_evaluations_per_start": POLISH_MAX_EVALUATIONS,
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


def run_optimization(csv_data, G, do, moments, df_max, e1_index, dosage, cancel_check=None):
    start_time = time.monotonic()
    model, gamma, gamma_sse, objective, residual, fit_indices = _prepare_optimization(
        csv_data, G, do, moments, df_max, cancel_check
    )
    _raise_if_cancelled(cancel_check)
    result = differential_evolution(
        objective,
        [ALPHA_BOUNDS, B_BOUNDS],
        maxiter=DE_MAXITER,
        popsize=DE_POPSIZE,
        tol=DE_TOL,
        polish=False,
        disp=False,
        updating="immediate",
        workers=1,
        strategy="best1bin",
        mutation=(0.5, 1.0),
        recombination=0.7,
        init="latinhypercube",
        seed=RANDOM_SEED,
        callback=lambda _x, _convergence: bool(cancel_check and cancel_check()),
    )
    _raise_if_cancelled(cancel_check)
    elapsed = time.monotonic() - start_time
    if np.all(np.isfinite(result.x)) and np.isfinite(result.fun):
        parameters, best_fun = _polish_candidate(result.x, residual, cancel_check)
        elapsed = time.monotonic() - start_time
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
            "Two-stage EQMOM optimization finished.",
            csv_data["d43"].to_numpy(dtype=float),
            csv_data["DF"].to_numpy(dtype=float),
            fit_indices,
            {
                "name": "Differential Evolution Algorithm (DEA)",
                "max_iterations": DE_MAXITER,
                "population_size_multiplier": DE_POPSIZE,
                "population_size": 2 * DE_POPSIZE,
                "tolerance": DE_TOL,
                "strategy": "best1bin",
                "mutation": [0.5, 1.0],
                "recombination": 0.7,
                "initialization": "latinhypercube",
                "updating": "immediate",
                "workers": 1,
                "deterministic_least_squares_polish": True,
            },
        )
    return {"success": False, "message": "EQMOM optimization failed to find a finite solution."}


def run_optimization_ga(csv_data, G, do, moments, df_max, e1_index, dosage, cancel_check=None):
    # geneticalgorithm imports its optional plotting stack at module load time.
    # Keep that cost out of application startup and DEA-only sessions.
    from geneticalgorithm import geneticalgorithm as ga

    class FastGeneticAlgorithm(ga):
        def sim(self, variables):
            return self.f(variables)

    start_time = time.monotonic()
    eqmom_model, gamma, gamma_sse, objective, residual, fit_indices = _prepare_optimization(
        csv_data, G, do, moments, df_max, cancel_check
    )
    algorithm_param = {
        "max_num_iteration": GA_MAX_ITERATIONS,
        "population_size": GA_POPULATION_SIZE,
        "mutation_probability": 0.1,
        "elit_ratio": 0.01,
        "crossover_probability": 0.5,
        "parents_portion": 0.3,
        "crossover_type": "uniform",
        "max_iteration_without_improv": GA_MAX_ITERATION_WITHOUT_IMPROV,
    }
    model = FastGeneticAlgorithm(
        function=objective,
        dimension=2,
        variable_type="real",
        variable_boundaries=np.array([ALPHA_BOUNDS, B_BOUNDS]),
        algorithm_parameters=algorithm_param,
        convergence_curve=False,
        progress_bar=False,
    )
    random_state = np.random.get_state()
    try:
        np.random.seed(RANDOM_SEED)
        with open(os.devnull, "w", encoding="utf-8") as output_sink, redirect_stdout(output_sink):
            model.run()
    finally:
        np.random.set_state(random_state)
    _raise_if_cancelled(cancel_check)
    elapsed = time.monotonic() - start_time
    if model.best_variable is not None and np.isfinite(model.best_function):
        parameters, best_fun = _polish_candidate(model.best_variable, residual, cancel_check)
        elapsed = time.monotonic() - start_time
        return _optimization_response(
            parameters,
            best_fun,
            gamma,
            gamma_sse,
            eqmom_model,
            G,
            do,
            e1_index,
            dosage,
            elapsed,
            "Two-stage EQMOM Genetic Algorithm optimization finished.",
            csv_data["d43"].to_numpy(dtype=float),
            csv_data["DF"].to_numpy(dtype=float),
            fit_indices,
            {
                "name": "Genetic Algorithm (GA)",
                "max_iterations": GA_MAX_ITERATIONS,
                "population_size": GA_POPULATION_SIZE,
                "mutation_probability": algorithm_param["mutation_probability"],
                "elitism_ratio": algorithm_param["elit_ratio"],
                "crossover_probability": algorithm_param["crossover_probability"],
                "parents_portion": algorithm_param["parents_portion"],
                "crossover_type": algorithm_param["crossover_type"],
                "max_iterations_without_improvement": GA_MAX_ITERATION_WITHOUT_IMPROV,
                "deterministic_least_squares_polish": True,
            },
        )
    return {"success": False, "message": "EQMOM Genetic Algorithm failed to find a finite solution."}

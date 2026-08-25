from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import minimize_scalar


class EQMOMError(RuntimeError):
    pass


class EQMOMCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class EQMOMConfig:
    time_minutes: np.ndarray
    moments0: np.ndarray
    df0: float
    df_max: float
    shear_rate: float
    primary_diameter_nm: float
    dt_seconds: float = 1.0
    kinematic_viscosity: float = 1e-6
    temperature: float = 296.0
    boltzmann_constant: float = 1.380622e-23
    dynamic_viscosity: float = 1e-3
    collision_x: float = 0.1
    collision_y: float = 0.2
    secondary_quadrature_order: int = 5
    d43_scale: float = 1.0
    minimum_substep_seconds: float | None = None
    maximum_substeps: int = 4096
    sigma_minimum: float = 1e-12
    cancel_check: Callable[[], bool] | None = None

    def __post_init__(self) -> None:
        time = np.asarray(self.time_minutes, dtype=float)
        moments = np.asarray(self.moments0, dtype=float)
        if time.ndim != 1 or time.size < 2 or not np.all(np.isfinite(time)):
            raise ValueError("At least two finite measurement times are required.")
        if abs(time[0]) > 1e-12 or np.any(np.diff(time) <= 0):
            raise ValueError("Measurement time must start at zero and increase strictly.")
        if moments.shape != (5,) or np.any(~np.isfinite(moments)) or np.any(moments <= 0):
            raise ValueError("Initial EQMOM moments must contain five positive finite values.")
        if self.dt_seconds <= 0 or self.shear_rate <= 0 or self.primary_diameter_nm <= 0:
            raise ValueError("dt, shear rate, and primary diameter must be positive.")
        minimum_substep = (
            self.dt_seconds / 1024.0
            if self.minimum_substep_seconds is None
            else float(self.minimum_substep_seconds)
        )
        if minimum_substep <= 0 or minimum_substep > self.dt_seconds:
            raise ValueError("The minimum substep must be positive and no larger than dt.")
        if self.maximum_substeps <= 0 or self.sigma_minimum <= 0:
            raise ValueError("Adaptive integration limits must be positive.")
        object.__setattr__(self, "time_minutes", time)
        object.__setattr__(self, "moments0", moments)
        object.__setattr__(self, "minimum_substep_seconds", minimum_substep)

    @property
    def sample_steps(self) -> np.ndarray:
        return np.rint(self.time_minutes * 60.0 / self.dt_seconds).astype(int)

    @property
    def energy_dissipation(self) -> float:
        return self.shear_rate**2 * self.kinematic_viscosity

    @property
    def primary_diameter_m(self) -> float:
        return self.primary_diameter_nm * 1e-9


def moments_from_distribution(distribution, df0: float, primary_diameter_nm: float) -> np.ndarray:
    counts = np.asarray(distribution, dtype=float).reshape(-1)
    if counts.size == 0 or np.any(~np.isfinite(counts)) or np.any(counts < 0):
        raise ValueError("Initial distribution must contain finite non-negative values.")
    total = counts.sum()
    if total <= 0:
        raise ValueError("Initial distribution must contain at least one positive value.")
    if df0 <= 0 or primary_diameter_nm <= 0:
        raise ValueError("Initial DF and primary diameter must be positive.")

    weights = counts / total
    bins = np.arange(counts.size, dtype=float)
    diameters_um = primary_diameter_nm * 1e-3 * 2.0 ** (bins / df0)
    return np.array([np.sum(weights * diameters_um**order) for order in range(5)])


def simulate_df(gamma: float, config: EQMOMConfig, times_minutes=None) -> np.ndarray:
    times = config.time_minutes if times_minutes is None else np.asarray(times_minutes, dtype=float)
    steps = np.rint(times * 60.0 / config.dt_seconds).astype(int)
    factor = 1.0 - gamma * config.dt_seconds / 60.0
    if factor < 0:
        raise EQMOMError("Gamma is too large for the selected integration step.")
    return config.df_max - (config.df_max - config.df0) * factor**steps


def fit_gamma(
    time_minutes,
    df_exp,
    df_max: float,
    *,
    df0: float | None = None,
    upper: float = 10.0,
    fit_indices=None,
) -> tuple[float, float]:
    time = np.asarray(time_minutes, dtype=float)
    observed = np.asarray(df_exp, dtype=float)
    if time.shape != observed.shape or time.size < 2:
        raise ValueError("TIME and DF must contain the same number of values.")

    dt_seconds = 1.0
    steps = np.rint(time * 60.0 / dt_seconds).astype(int)
    initial_df = float(observed[0]) if df0 is None else float(df0)
    if not np.isfinite(initial_df) or initial_df <= 0:
        raise ValueError("DF0 must be a positive finite value.")
    indices = (
        np.arange(1, observed.size, dtype=int)
        if fit_indices is None
        else np.asarray(fit_indices, dtype=int)
    )
    if indices.ndim != 1 or indices.size == 0 or np.any(indices <= 0) or np.any(indices >= observed.size):
        raise ValueError("Gamma fit indices must refer to measurements after time zero.")

    def objective(gamma: float) -> float:
        factor = 1.0 - gamma * dt_seconds / 60.0
        if factor < 0:
            return 1e30
        predicted = df_max - (df_max - initial_df) * factor**steps
        residual = predicted[indices] - observed[indices]
        return float(residual @ residual)

    result = minimize_scalar(
        objective,
        bounds=(0.0, upper),
        method="bounded",
        options={"xatol": 1e-10, "maxiter": 300},
    )
    if not result.success or not np.isfinite(result.fun):
        raise EQMOMError(f"Gamma optimization failed: {result.message}")
    return float(result.x), float(result.fun)


def _chebyshev_coefficients(reduced: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a0 = reduced[1]
    s22 = reduced[2] - a0 * reduced[1]
    b1 = s22
    z1 = a0
    with np.errstate(divide="ignore", invalid="ignore"):
        z2 = b1 / z1
        a1 = (reduced[3] - a0 * reduced[2]) / s22 - reduced[1]
        z3 = a1 - z2
        s33 = (
            reduced[4]
            - a0 * reduced[3]
            - a1 * (reduced[3] - a0 * reduced[2])
            - b1 * reduced[2]
        )
        b2 = s33 / s22
        z4 = b2 / z3
    return (
        np.array([z1, z2, z3, z4]),
        np.array([a0, a1]),
        np.array([b1, b2]),
    )


def _matlab_lognormal_boundary(
    normalized: np.ndarray,
    variance_limit: float,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Port the four-slot Ridder search from computeLogNormalNew.m."""
    relative_tolerance = 1e-10
    maximum_evaluations = 100
    orders = np.arange(5, dtype=float)
    coordinates = np.zeros((4, 4))
    recurrence_a = np.zeros((2, 4))
    recurrence_b = np.zeros((2, 4))
    sigma_squared = np.array([0.0, np.nan, np.nan, variance_limit])

    def evaluate(slot: int) -> None:
        reduced = normalized * np.exp(-0.5 * orders**2 * sigma_squared[slot])
        (
            coordinates[:, slot],
            recurrence_a[:, slot],
            recurrence_b[:, slot],
        ) = _chebyshev_coefficients(reduced)

    evaluate(0)
    evaluations = 1
    raw_coordinates = coordinates[:, 0]
    if np.any(~np.isfinite(raw_coordinates)) or np.any(raw_coordinates < -relative_tolerance):
        raise EQMOMError("The moment vector is not realizable.")

    degenerate = np.flatnonzero(raw_coordinates < relative_tolerance)
    if degenerate.size:
        raw_coordinates[degenerate[0]] = 0.0
        return (
            0.0,
            recurrence_a[:, 0],
            recurrence_b[:, 0],
            raw_coordinates.copy(),
            raw_coordinates * relative_tolerance,
        )

    evaluate(3)
    evaluations += 1
    reference_coordinates = raw_coordinates * relative_tolerance
    sigma_tolerance = variance_limit * relative_tolerance

    # MATLAB pointer vector p = [1 2 3 4 1 4 0], converted to zero-based slots.
    pointers = [0, 1, 2, 3, 0, 3, -1]
    status = 0

    def ridder_step(coordinate_index: int, *, final_coordinate: bool) -> None:
        nonlocal evaluations, status
        pointers[4] = 0
        pointers[5] = 3

        middle_slot = pointers[1]
        sigma_squared[middle_slot] = 0.5 * (
            sigma_squared[pointers[0]] + sigma_squared[pointers[3]]
        )
        evaluate(middle_slot)
        evaluations += 1

        middle_positive = coordinates[coordinate_index, middle_slot] > 0.0
        later_negative = (
            not final_coordinate
            and middle_positive
            and np.any(coordinates[coordinate_index + 1 :, middle_slot] < 0.0)
        )
        if later_negative:
            pointers[3], pointers[1] = pointers[1], pointers[3]
            return
        if middle_positive:
            pointers[4] = 1
        else:
            pointers[5] = 1

        left_value = coordinates[coordinate_index, pointers[0]]
        middle_value = coordinates[coordinate_index, middle_slot]
        right_value = coordinates[coordinate_index, pointers[3]]
        radicand = middle_value**2 - left_value * right_value
        if not np.isfinite(radicand) or radicand <= 0.0:
            raise EQMOMError("The MATLAB EQMOM width search became invalid.")

        ridder_slot = pointers[2]
        sigma_squared[ridder_slot] = sigma_squared[middle_slot] + (
            (sigma_squared[middle_slot] - sigma_squared[pointers[0]])
            * middle_value
            / np.sqrt(radicand)
        )
        evaluate(ridder_slot)
        evaluations += 1

        ridder_positive = coordinates[coordinate_index, ridder_slot] > 0.0
        later_negative = (
            not final_coordinate
            and ridder_positive
            and np.any(coordinates[coordinate_index + 1 :, ridder_slot] < 0.0)
        )
        if (
            not later_negative
            and ridder_positive
            and sigma_squared[ridder_slot] > sigma_squared[pointers[pointers[4]]]
        ):
            pointers[4] = 2
        if (
            not ridder_positive
            and sigma_squared[ridder_slot] < sigma_squared[pointers[pointers[5]]]
        ):
            pointers[5] = 2

        candidate_left = pointers[pointers[4]]
        pointers[0], pointers[pointers[4]] = candidate_left, pointers[0]
        candidate_right = pointers[pointers[5]]
        pointers[3], pointers[pointers[5]] = candidate_right, pointers[3]

        if final_coordinate and (
            coordinates[coordinate_index, pointers[0]]
            < reference_coordinates[coordinate_index]
        ):
            coordinates[coordinate_index, pointers[0]] = 0.0
            status = 1
        elif sigma_squared[pointers[3]] - sigma_squared[pointers[0]] < sigma_tolerance:
            status = 1
        elif evaluations > maximum_evaluations:
            status = 5

    coordinate_index = 0
    while status == 0 and coordinate_index < 3:
        if coordinates[coordinate_index, pointers[3]] > 0.0:
            coordinate_index += 1
            continue
        ridder_step(coordinate_index, final_coordinate=False)

    while status == 0:
        ridder_step(3, final_coordinate=True)

    if status != 1:
        raise EQMOMError("The MATLAB EQMOM width search did not converge.")

    left_slot = pointers[0]
    return (
        float(sigma_squared[left_slot]),
        recurrence_a[:, left_slot].copy(),
        recurrence_b[:, left_slot].copy(),
        coordinates[:, left_slot].copy(),
        reference_coordinates,
    )


def _matlab_eigen_jacobi(
    diagonal: np.ndarray,
    squared_off_diagonal: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Port eigenJacobi.m, including its rounding near a zero eigenvalue."""
    diagonal = np.asarray(diagonal, dtype=float)
    order = diagonal.size
    jacobi = np.diag(diagonal)
    for index in range(1, order):
        value = np.sqrt(squared_off_diagonal[index - 1])
        jacobi[index - 1, index] = value
        jacobi[index, index - 1] = value

    vectors = np.eye(order)
    eigenvalues = diagonal.copy()
    accumulated = diagonal.copy()
    corrections = np.zeros(order)

    for iteration in range(1, 101):
        threshold = sum(
            abs(jacobi[row, column])
            for row in range(order - 1)
            for column in range(row + 1, order)
        ) / (4.0 * order)
        if threshold == 0.0:
            break

        for row in range(order):
            for column in range(row + 1, order):
                gap = 10.0 * abs(jacobi[row, column])
                matlab_epsilon = np.spacing(min(abs(eigenvalues[row]), abs(eigenvalues[column])))
                if iteration > 4 and gap < matlab_epsilon:
                    jacobi[row, column] = 0.0
                    continue
                if threshold > abs(jacobi[row, column]):
                    continue

                difference = eigenvalues[column] - eigenvalues[row]
                if gap < np.spacing(abs(difference)):
                    tangent = jacobi[row, column] / difference
                else:
                    theta = 0.5 * difference / jacobi[row, column]
                    tangent = 1.0 / (abs(theta) + np.hypot(1.0, theta))
                    if theta < 0.0:
                        tangent = -tangent

                cosine = 1.0 / np.hypot(1.0, tangent)
                sine = tangent * cosine
                tau = sine / (1.0 + cosine)
                shift = tangent * jacobi[row, column]
                corrections[row] -= shift
                corrections[column] += shift
                eigenvalues[row] -= shift
                eigenvalues[column] += shift
                jacobi[row, column] = 0.0

                for index in range(row):
                    first = jacobi[index, row]
                    second = jacobi[index, column]
                    jacobi[index, row] = first - sine * (second + first * tau)
                    jacobi[index, column] = second + sine * (first - second * tau)
                for index in range(row + 1, column):
                    first = jacobi[row, index]
                    second = jacobi[index, column]
                    jacobi[row, index] = first - sine * (second + first * tau)
                    jacobi[index, column] = second + sine * (first - second * tau)
                for index in range(column + 1, order):
                    first = jacobi[row, index]
                    second = jacobi[column, index]
                    jacobi[row, index] = first - sine * (second + first * tau)
                    jacobi[column, index] = second + sine * (first - second * tau)
                for index in range(order):
                    first = vectors[index, row]
                    second = vectors[index, column]
                    vectors[index, row] = first - sine * (second + first * tau)
                    vectors[index, column] = second + sine * (first - second * tau)

        accumulated += corrections
        eigenvalues = accumulated.copy()
        corrections.fill(0.0)

    indices = np.argsort(eigenvalues)
    return vectors[0, indices] ** 2, eigenvalues[indices]


def _two_node_lognormal(moments: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    moments = np.asarray(moments, dtype=float)
    if moments.shape != (5,) or np.any(moments <= 0) or np.any(~np.isfinite(moments)):
        raise EQMOMError("The moment vector is not realizable.")

    normalized = moments / moments[0]
    variance_limit = np.log(normalized[2] / normalized[1] ** 2)
    if not np.isfinite(variance_limit) or variance_limit <= 1e-14:
        raise EQMOMError("The moment vector is degenerate.")

    (
        sigma_squared,
        recurrence_a,
        recurrence_b,
        boundary_coordinates,
        reference_coordinates,
    ) = _matlab_lognormal_boundary(normalized, variance_limit)

    coordinate_number = 4
    for index in range(4):
        if boundary_coordinates[index] <= reference_coordinates[index]:
            coordinate_number = index + 1
            break
    node_count = (coordinate_number + coordinate_number % 2) // 2

    if recurrence_b[0] <= 0 or not np.isfinite(recurrence_b[0]):
        raise EQMOMError("The reduced moment vector is not realizable.")

    if node_count == 2:
        normalized_weights, nodes = _matlab_eigen_jacobi(
            recurrence_a,
            recurrence_b[:1],
        )
        weights = moments[0] * normalized_weights
    else:
        nodes = np.array([recurrence_a[0], 0.5])
        weights = np.array([moments[0], 0.0])

    active = weights > 0.0
    if np.any(nodes[active] <= 0) or np.any(weights < 0) or np.any(~np.isfinite(nodes)):
        raise EQMOMError("The MATLAB EQMOM quadrature is invalid.")
    return weights, nodes, float(np.sqrt(max(sigma_squared, 0.0)))


def _gauss_wigert(order: int, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    if order <= 1 or sigma < 0 or not np.isfinite(sigma):
        raise EQMOMError("Invalid secondary quadrature settings.")
    if sigma < 1e-12:
        weights = np.zeros(order)
        weights[0] = 1.0
        nodes = np.ones(order)
        return weights, nodes

    z = np.exp(0.5 * sigma**2)
    z2 = z * z
    z3 = z2 * z
    c0 = z2
    c1 = z
    c2 = z
    jacobi = np.zeros((order, order))
    jacobi[0, 0] = z
    jacobi[1, 1] = ((z2 + 1.0) * c0 - 1.0) * c1
    jacobi[0, 1] = jacobi[1, 0] = np.sqrt(c0 - 1.0) * c2
    for index in range(1, order - 1):
        c0 *= z2
        c1 *= z2
        c2 *= z3
        jacobi[index + 1, index + 1] = ((z2 + 1.0) * c0 - 1.0) * c1
        jacobi[index + 1, index] = jacobi[index, index + 1] = np.sqrt(c0 - 1.0) * c2
    nodes, vectors = np.linalg.eigh(jacobi)
    return vectors[0, :] ** 2, nodes


def _moment_derivative(moments: np.ndarray, df: float, alpha_max: float, binding: float, config: EQMOMConfig):
    primary_weights, primary_nodes, sigma = _two_node_lognormal(moments)
    if not np.isfinite(sigma) or sigma <= config.sigma_minimum:
        raise EQMOMError("The EQMOM quadrature width is invalid.")
    secondary_weights, secondary_nodes = _gauss_wigert(config.secondary_quadrature_order, sigma)

    weights = (primary_weights[:, None] * secondary_weights[None, :]).reshape(-1)
    radii = (primary_nodes[:, None] * secondary_nodes[None, :]).reshape(-1)
    active = weights > 0
    weights = weights[active]
    radii = radii[active]

    r1 = radii[:, None]
    r2 = radii[None, :]
    common_weight = weights[:, None] * weights[None, :]
    ratio = np.minimum(r1, r2) / np.maximum(r1, r2)
    collision_efficiency = alpha_max * np.exp(-config.collision_x * (1.0 - ratio**df) ** 2)

    log_penalty = df * config.collision_y * np.log(
        (r1 * r2) / config.primary_diameter_m**2
    )
    inverse_size_penalty = np.exp(np.clip(-log_penalty, -745.0, 700.0))
    brownian = (
        2.0 * config.boltzmann_constant * config.temperature / (3.0 * config.dynamic_viscosity)
    ) * ((r1 + r2) ** 2 / (r1 * r2))
    shear = 1.294 * config.shear_rate * (r1 + r2) ** 3
    weighted_collision = common_weight * collision_efficiency * inverse_size_penalty

    orders = np.arange(5, dtype=float)
    merged = (r1**df + r2**df)[:, :, None] ** (orders / df)
    loss_power = r1[:, :, None] ** orders
    aggregation_birth = np.sum(
        weighted_collision[:, :, None] * merged * (brownian + shear / 2.0)[:, :, None], axis=(0, 1)
    )
    aggregation_loss = np.sum(
        weighted_collision[:, :, None] * loss_power * (brownian + shear)[:, :, None], axis=(0, 1)
    )

    denominator = (0.414 * df - 0.211) * radii * config.energy_dissipation
    if np.any(denominator <= 0) or np.any(~np.isfinite(denominator)):
        raise EQMOMError("The breakup-kernel denominator is invalid.")
    breakup_rate = np.sqrt(4.0 / (15.0 * np.pi)) * config.shear_rate * np.exp(-binding / denominator)
    single_weight = weights * breakup_rate
    powers = radii[:, None] ** orders
    fragmentation_birth = np.sum(
        single_weight[:, None] * powers * 2.0 ** ((df - orders) / df), axis=0
    )
    fragmentation_loss = np.sum(single_weight[:, None] * powers, axis=0)

    return (
        aggregation_birth - aggregation_loss + fragmentation_birth - fragmentation_loss
    )


def _valid_moment_state(moments: np.ndarray, config: EQMOMConfig) -> bool:
    if moments.shape != (5,) or np.any(~np.isfinite(moments)) or np.any(moments <= 0):
        return False
    sigma_squared_estimate = np.log((moments[0] * moments[2]) / moments[1] ** 2)
    return bool(
        np.isfinite(sigma_squared_estimate)
        and sigma_squared_estimate > config.sigma_minimum**2
    )


def _advance_adaptive(
    moments: np.ndarray,
    df: float,
    alpha_max: float,
    binding: float,
    config: EQMOMConfig,
) -> np.ndarray:
    remaining = config.dt_seconds
    step_size = config.dt_seconds
    attempts = 0
    derivative = None

    while remaining > 10.0 * np.finfo(float).eps * config.dt_seconds:
        if config.cancel_check is not None and config.cancel_check():
            raise EQMOMCancelled("Simulation was cancelled.")
        attempts += 1
        if attempts > config.maximum_substeps:
            raise EQMOMError("Maximum adaptive substep count was exceeded.")
        step_size = min(step_size, remaining)
        if derivative is None:
            derivative = _moment_derivative(moments, df, alpha_max, binding, config)
        candidate = moments + step_size * derivative
        if _valid_moment_state(candidate, config):
            moments = candidate
            remaining -= step_size
            derivative = None
            if remaining > 0:
                step_size = min(2.0 * step_size, remaining)
            continue
        step_size /= 2.0
        if step_size < config.minimum_substep_seconds:
            raise EQMOMError("Minimum adaptive substep reached before a valid moment update.")
    return moments


def simulate_eqmom(alpha_max: float, binding: float, gamma: float, config: EQMOMConfig) -> tuple[np.ndarray, np.ndarray]:
    if not (0 < alpha_max <= 1) or binding < 0 or gamma < 0:
        raise EQMOMError("EQMOM parameters are outside their valid ranges.")

    sample_steps = config.sample_steps
    if np.any(np.diff(sample_steps) <= 0):
        raise EQMOMError("Measurement times are not unique on the integration grid.")
    df_samples = simulate_df(gamma, config)
    df_full = simulate_df(
        gamma,
        config,
        np.arange(sample_steps[-1] + 1, dtype=float) * config.dt_seconds / 60.0,
    )

    moments = config.moments0.copy()
    d43 = np.full(config.time_minutes.size, np.nan)
    d43[0] = config.d43_scale * moments[4] / moments[3]
    next_sample = 1

    for step in range(sample_steps[-1]):
        if step % 64 == 0 and config.cancel_check is not None and config.cancel_check():
            raise EQMOMCancelled("Simulation was cancelled.")
        moments = _advance_adaptive(moments, df_full[step], alpha_max, binding, config)
        completed_step = step + 1
        if next_sample < sample_steps.size and completed_step == sample_steps[next_sample]:
            d43[next_sample] = config.d43_scale * moments[4] / moments[3]
            next_sample += 1

    if np.any(~np.isfinite(d43)):
        raise EQMOMError("EQMOM did not produce all requested samples.")
    return d43, df_samples

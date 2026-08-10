from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import brentq, minimize_scalar


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
    collision_y: float = 0.1
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
    upper: float = 10.0,
    fit_indices=None,
) -> tuple[float, float]:
    time = np.asarray(time_minutes, dtype=float)
    observed = np.asarray(df_exp, dtype=float)
    if time.shape != observed.shape or time.size < 2:
        raise ValueError("TIME and DF must contain the same number of values.")

    dt_seconds = 1.0
    steps = np.rint(time * 60.0 / dt_seconds).astype(int)
    df0 = float(observed[0])
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
        predicted = df_max - (df_max - df0) * factor**steps
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


def _hankel_determinant(reduced: np.ndarray) -> float:
    matrix = np.array(
        [
            [reduced[0], reduced[1], reduced[2]],
            [reduced[1], reduced[2], reduced[3]],
            [reduced[2], reduced[3], reduced[4]],
        ]
    )
    return float(np.linalg.det(matrix))


def _two_node_lognormal(moments: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    moments = np.asarray(moments, dtype=float)
    if moments.shape != (5,) or np.any(moments <= 0) or np.any(~np.isfinite(moments)):
        raise EQMOMError("The moment vector is not realizable.")

    characteristic = moments[1] / moments[0]
    normalized = moments / (moments[0] * characteristic ** np.arange(5))
    variance_limit = np.log(normalized[2] / normalized[1] ** 2)
    if not np.isfinite(variance_limit) or variance_limit <= 1e-14:
        raise EQMOMError("The moment vector is degenerate.")

    orders = np.arange(5, dtype=float)

    def determinant(sigma_squared: float) -> float:
        reduced = normalized * np.exp(-0.5 * orders**2 * sigma_squared)
        return _hankel_determinant(reduced)

    left = 0.0
    right = variance_limit * (1.0 - 1e-12)
    f_left = determinant(left)
    f_right = determinant(right)
    scale = max(abs(f_left), abs(f_right), 1.0)

    if abs(f_left) <= 1e-12 * scale:
        sigma_squared = 0.0
    elif f_left * f_right < 0:
        sigma_squared = brentq(determinant, left, right, xtol=1e-12, rtol=1e-12, maxiter=100)
    else:
        grid = np.linspace(left, right, 65)
        values = np.array([determinant(value) for value in grid])
        crossings = np.flatnonzero(values[:-1] * values[1:] <= 0)
        if crossings.size == 0:
            raise EQMOMError("Could not determine the log-normal EQMOM width.")
        index = int(crossings[-1])
        sigma_squared = brentq(
            determinant, grid[index], grid[index + 1], xtol=1e-12, rtol=1e-12, maxiter=100
        )

    reduced = moments * np.exp(-0.5 * orders**2 * sigma_squared)
    a0 = reduced[1] / reduced[0]
    norm1 = reduced[2] - 2.0 * a0 * reduced[1] + a0**2 * reduced[0]
    if norm1 <= 0 or not np.isfinite(norm1):
        raise EQMOMError("The reduced moment vector is not realizable.")
    b1 = norm1 / reduced[0]
    a1 = (
        reduced[3] - 2.0 * a0 * reduced[2] + a0**2 * reduced[1]
    ) / norm1
    jacobi = np.array([[a0, np.sqrt(b1)], [np.sqrt(b1), a1]])
    nodes, vectors = np.linalg.eigh(jacobi)
    weights = reduced[0] * vectors[0, :] ** 2
    if np.any(nodes <= 0) or np.any(weights < 0):
        # Rounded experimental moments can land immediately on the one-node
        # realizability boundary. MATLAB's solver pads that reconstruction to
        # two nodes with a zero second weight.
        sigma_squared = variance_limit
        reduced = moments * np.exp(-0.5 * orders**2 * sigma_squared)
        nodes = np.array([reduced[1] / reduced[0], 0.5 * reduced[1] / reduced[0]])
        weights = np.array([reduced[0], 0.0])
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

    log_penalty = df * 2.0 * config.collision_y * np.log(
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

    while remaining > 10.0 * np.finfo(float).eps * config.dt_seconds:
        if config.cancel_check is not None and config.cancel_check():
            raise EQMOMCancelled("Simulation was cancelled.")
        attempts += 1
        if attempts > config.maximum_substeps:
            raise EQMOMError("Maximum adaptive substep count was exceeded.")
        step_size = min(step_size, remaining)
        derivative = _moment_derivative(moments, df, alpha_max, binding, config)
        candidate = moments + step_size * derivative
        if _valid_moment_state(candidate, config):
            moments = candidate
            remaining -= step_size
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

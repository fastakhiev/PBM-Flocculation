import asyncio
import hashlib
import logging
import platform
import time
from importlib.metadata import PackageNotFoundError, version
from io import StringIO

import numpy as np
import pandas as pd
import scipy

from app.core.jobs import Job, cancel_job, create_job, get_job, run_job_in_thread
from app.pbm_model.optimization import (
    PROTOCOL_VERSION,
    run_optimization,
    run_optimization_ga,
    run_optimization_matlab,
)
from app.pbm_model.realtime import run_realtime_simulation
from app.version import APP_VERSION


_PREVIOUS_STATE: dict | None = None


def _distribution_version(distribution: str, fallback: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return fallback


def check_status(task_id: str) -> Job | None:
    return get_job(task_id)


def stop_task(task_id: str) -> bool:
    return cancel_job(task_id)


def _read_experimental_csv(csv_text: str) -> tuple[pd.DataFrame, float, float]:
    raw = pd.read_csv(StringIO(csv_text), sep=";", skiprows=2, engine="python", dtype=str)
    raw.columns = [str(column).strip().lstrip("\ufeff") for column in raw.columns]
    required = ["Time(min)", "d43", "DF"]
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"Experimental CSV is missing columns: {', '.join(missing)}")
    time_labels = raw["Time(min)"].fillna("").str.strip().str.lower().str.replace("_", " ", regex=False)
    df_max_rows = time_labels.isin({"df max", "dfmax"})
    df0_rows = time_labels.isin({"df 0", "df0"})
    if int(df_max_rows.sum()) != 1:
        raise ValueError("Experimental CSV must contain exactly one 'dF max' metadata row.")
    if int(df0_rows.sum()) != 1:
        raise ValueError("Experimental CSV must contain exactly one 'dF 0' metadata row.")

    def read_metadata(rows: pd.Series, label: str) -> float:
        value_text = str(raw.loc[rows, "DF"].iloc[0]).strip().replace(",", ".")
        try:
            value = float(value_text)
        except ValueError as error:
            raise ValueError(f"The DF value in the '{label}' row must be numeric.") from error
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{label.replace('dF', 'DF')} must be a positive finite value.")
        return value

    df_max = read_metadata(df_max_rows, "dF max")
    df0 = read_metadata(df0_rows, "dF 0")

    metadata_rows = df_max_rows | df0_rows
    measurement_rows = raw.loc[~metadata_rows, required].copy()
    measurement_rows = measurement_rows.dropna(how="all")
    for column in required:
        measurement_rows[column] = pd.to_numeric(
            measurement_rows[column].astype(str).str.strip().str.replace(",", "."), errors="coerce"
        )
    if measurement_rows.isna().any(axis=None):
        raise ValueError("Every experimental measurement must contain numeric Time(min), d43, and DF values.")
    measurements = measurement_rows.astype(float)
    if len(measurements) < 5:
        raise ValueError(
            "Experimental CSV must contain at least five complete measurements "
            "so the three-parameter GOF has positive degrees of freedom."
        )
    measurements.reset_index(drop=True, inplace=True)
    times = measurements["Time(min)"].to_numpy(dtype=float)
    if not np.isclose(times[0], 0.0, rtol=0.0, atol=1e-12):
        raise ValueError("Experimental time must start at 0 minutes.")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Experimental time must increase strictly without duplicate values.")
    if np.any(measurements[["d43", "DF"]].to_numpy(dtype=float) <= 0):
        raise ValueError("Experimental d43 and DF values must be positive.")
    return measurements, df_max, df0


def _read_initial_moments(csv_text: str) -> np.ndarray:
    data = pd.read_csv(StringIO(csv_text), sep=";", engine="python")
    moment_columns = [f"M{index}" for index in range(5)]
    if all(column in data.columns for column in moment_columns):
        moments = np.array(
            [float(str(data.loc[data.index[0], column]).replace(",", ".")) for column in moment_columns]
        )
    elif "value" in data.columns:
        moments = pd.to_numeric(
            data["value"].astype(str).str.replace(",", "."), errors="coerce"
        ).dropna().to_numpy(dtype=float)
        if moments.size != 5:
            raise ValueError("The value column must contain exactly five rows: M0, M1, M2, M3, M4.")
    elif "initial_distribution" in data.columns:
        raise ValueError(
            "The uploaded initial_distribution belongs to the discrete PBM. "
            "The EQMOM model requires the experimental initial moments M0, M1, M2, M3, M4 used in the paper."
        )
    else:
        raise ValueError(
            "Initial CSV must contain either a value column with five rows or the five columns M0, M1, M2, M3, M4."
        )
    if moments.shape != (5,) or np.any(~np.isfinite(moments)) or np.any(moments <= 0):
        raise ValueError("Initial EQMOM moments must be five positive finite values.")
    return moments


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optimization_task_impl(
    csv_str_exp,
    csv_str_init,
    g,
    do,
    e1_index,
    optimization_algorithm,
    dosage,
    experimental_filename,
    moments_filename,
    *,
    cancel_event=None,
):
    try:
        csv_data_exp, df_max, DF0_val = _read_experimental_csv(csv_str_exp)
        G_val = float(g)
        do_val = float(do)
        moments = _read_initial_moments(csv_str_init)

        if not np.isfinite(G_val) or G_val <= 0 or not np.isfinite(do_val) or do_val <= 0:
            raise ValueError("Shear rate and primary particle diameter must be positive finite values.")

        cancel_check = cancel_event.is_set if cancel_event is not None else None
        args = (
            csv_data_exp, G_val, do_val, moments, df_max, e1_index, dosage,
            cancel_check, DF0_val,
        )
        if optimization_algorithm == "Differential Evolution Algorithm (DEA)":
            results = run_optimization(*args)
        elif optimization_algorithm == "Genetic Algorithm (GA)":
            results = run_optimization_ga(*args)
        elif optimization_algorithm == "MATLAB-compatible Multi-start Least Squares (MLS)":
            results = run_optimization_matlab(*args)
        else:
            raise ValueError("Unknown optimization algorithm")

        if not results.get("success"):
            return results
        results["gof"] = results["metrics"]["d43"]["gof_percent"]
        results["provenance"] = {
            "software_version": APP_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "experimental_file": experimental_filename,
            "moments_file": moments_filename,
            "experimental_sha256": _sha256_text(csv_str_exp),
            "moments_sha256": _sha256_text(csv_str_init),
            "runtime": {
                "python": platform.python_version(),
                "operating_system": platform.platform(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "pandas": pd.__version__,
                "geneticalgorithm": _distribution_version("geneticalgorithm", "1.0.2"),
            },
        }
        return results
    except Exception:
        logging.exception("EQMOM optimization task failed")
        raise


def _simulation_task_impl(opt_params, G, do, csv_str, mode="realtime", *, cancel_event=None):
    global _PREVIOUS_STATE
    start_time = time.monotonic()
    try:
        _PREVIOUS_STATE = None
        if mode != "realtime":
            raise ValueError("Unknown simulation mode")
        experimental, df_max, file_df0 = _read_experimental_csv(csv_str)
        simulation_params = dict(opt_params)
        saved_df0 = simulation_params.get("df0")
        if saved_df0 is None:
            simulation_params["df0"] = file_df0
        elif not np.isclose(float(saved_df0), file_df0, rtol=0.0, atol=1e-12):
            raise ValueError(
                "The experimental CSV dF 0 value differs from the DF0 used for the saved optimization."
            )
        relative_time = experimental["Time(min)"].to_numpy(dtype=float)
        relative_time -= relative_time[0]
        results_df, _ = run_realtime_simulation(
            simulation_params,
            experimental,
            dFmax_val=df_max,
            G=float(G),
            do=float(do),
            initial_state=None,
            cancel_check=cancel_event.is_set if cancel_event is not None else None,
        )
        return {
            "time": results_df["time"].tolist(),
            "VMD_corrected": results_df["VMD_corrected"].tolist(),
            "DF_corrected": results_df["DF_corrected"].tolist(),
            "time_exp": relative_time.tolist(),
            "d43_exp": experimental["d43"].tolist(),
            "df_exp": experimental["DF"].tolist(),
            "simulation_time": round(time.monotonic() - start_time, 2),
        }
    except Exception as error:
        logging.exception("EQMOM simulation task failed")
        return {"success": False, "message": str(error)}


async def optimization_task(
    csv_str_exp,
    csv_str_init,
    g,
    do,
    e1_index,
    optimization_algorithm,
    dosage,
    experimental_filename,
    moments_filename,
) -> str:
    job = create_job()
    asyncio.create_task(
        run_job_in_thread(
            job,
            _optimization_task_impl,
            csv_str_exp,
            csv_str_init,
            g,
            do,
            e1_index,
            optimization_algorithm,
            dosage,
            experimental_filename,
            moments_filename,
        )
    )
    return job.id


async def simulation_task(opt_params, G, do, csv_str, mode="realtime") -> str:
    job = create_job()
    asyncio.create_task(run_job_in_thread(job, _simulation_task_impl, opt_params, G, do, csv_str, mode))
    return job.id


def reset_previous_state() -> None:
    global _PREVIOUS_STATE
    _PREVIOUS_STATE = None


def has_previous_state() -> bool:
    return _PREVIOUS_STATE is not None

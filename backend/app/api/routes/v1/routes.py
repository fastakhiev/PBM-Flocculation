from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from app.schemas.schemas import SaveOptimizationResults
from app.api.dependencies.data import PUBLISHED_REFERENCE_DATA, PUBLISHED_REFERENCE_DOI
from app.core.jobs import cancel_job, get_job
from app.core.db import (
    clear_active_optimization,
    get_active_optimization,
    get_optimization_report,
    save_optimization_result,
)
import asyncio
from typing import List
from sse_starlette.sse import EventSourceResponse
import json


router = APIRouter()
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALGORITHMS = {
    "Differential Evolution Algorithm (DEA)",
    "Genetic Algorithm (GA)",
    "MATLAB-compatible Multi-start Least Squares (MLS)",
}


async def _read_csv_upload(upload: UploadFile, label: str) -> str:
    if Path(upload.filename or "").suffix.lower() != ".csv":
        raise HTTPException(status_code=422, detail=f"{label} must be a .csv file.")
    contents = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{label} exceeds the 2 MB upload limit.")
    try:
        return contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail=f"{label} must use UTF-8 encoding.") from error

@router.post("/start_optimize")
async def start_optimize(
        data: List = Form(...),
        file_exp: UploadFile = File(...),
        file_init: UploadFile = File(...)
):
    from app.pbm_model.optimization_simulation import optimization_task

    if len(data) != 5:
        raise HTTPException(status_code=422, detail="Exactly five optimization form values are required.")
    if str(data[3]) not in ALGORITHMS:
        raise HTTPException(status_code=422, detail="Unknown optimization algorithm.")
    try:
        g = float(data[0])
        primary_diameter = float(data[1])
        dosage = int(data[4])
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="G, d0, and dosage must be numeric.") from error
    if g <= 0 or primary_diameter <= 0 or dosage <= 0:
        raise HTTPException(status_code=422, detail="G, d0, and dosage must be positive.")
    csv_str_exp = await _read_csv_upload(file_exp, "Experimental data")
    csv_str_init = await _read_csv_upload(file_init, "Initial moments")

    task_id = await optimization_task(
        csv_str_exp,
        csv_str_init,
        g,
        primary_diameter,
        str(data[2]).strip(),
        str(data[3]),
        dosage,
        file_exp.filename or "experimental.csv",
        file_init.filename or "moments.csv",
    )
    return str(task_id)


async def event_generator_decimer(task_id: str):
    try:
        while True:
            job = get_job(task_id)
            if job is None:
                yield {"data": json.dumps({"status": "failed", "error": "Task not found"})}
                break

            if job.status == "completed":
                yield {"data": json.dumps({"status": "completed", "result": job.result})}
                break

            if job.status == "failed":
                yield {"data": json.dumps({"status": "failed", "error": job.error or "Unknown error"})}
                break

            if job.status == "cancelled":
                yield {"data": json.dumps({"status": "cancelled"})}
                break

            yield {"data": json.dumps({"status": "processing"})}

            await asyncio.sleep(1)
    except Exception as e:
        error_info = {"status": "failed", "error": str(e)}
        yield {"data": json.dumps(error_info)}


@router.get("/get_result_optimization/{task_id}")
async def get_result_decimer(task_id: str):
    return EventSourceResponse(event_generator_decimer(str(task_id)))


@router.delete("/stop_task/{task_id}")
async def stop_optimization(task_id: str):
    if not cancel_job(task_id):
        raise HTTPException(status_code=404, detail="Running task not found.")
    return Response(status_code=200, content="ok")


@router.post("/save_optimization_results")
async def save_optimization_results(data: SaveOptimizationResults):
    job = get_job(data.task_id)
    if job is None or job.status != "completed" or not isinstance(job.result, dict):
        raise HTTPException(status_code=409, detail="Optimization task is not completed.")
    res = job.result
    if not res.get("success"):
        raise HTTPException(status_code=409, detail="A failed optimization cannot be saved.")
    report_json = json.dumps(res, ensure_ascii=True, allow_nan=False, sort_keys=True)
    save_optimization_result(
        data.task_id,
        res,
        report_json,
        datetime.now(timezone.utc).isoformat(),
    )
    return Response(status_code=200, content="ok")


@router.post("/start_simulation")
async def start_simulation(file: UploadFile = File(...)):
    from app.pbm_model.optimization_simulation import simulation_task

    csv_str = await _read_csv_upload(file, "Experimental data")
    data = get_active_optimization()
    if data is None:
        raise HTTPException(status_code=409, detail="Run and save an optimization before simulation.")
    task_id = await simulation_task(
        {
            "amax": data["amax"],
            "B": data["b"],
            "gama": data["gama"],
            "df0": data["df0"],
            "moments": json.loads(data["moments_json"]) if data["moments_json"] else None,
        },
        data["g"],
        data["do"],
        csv_str
    )
    return str(task_id)


@router.delete("/reset_state")
async def reset_state():
    from app.pbm_model.optimization_simulation import reset_previous_state

    reset_previous_state()
    return Response(status_code=200, content="ok")


@router.get("/get_result_simulation/{task_id}")
async def get_result_simulation(task_id: str):
    return EventSourceResponse(event_generator_decimer(str(task_id)))


@router.get("/check_simulation_state")
async def check_simulation_state():
    from app.pbm_model.optimization_simulation import has_previous_state

    return {"has_state": has_previous_state()}


@router.get("/check_optimization")
async def check_optimization():
    active = get_active_optimization()
    if active is None:
        return {
            "response": False
        }
    else:
        return {
            "response": True,
            "g": active["g"],
            "do": active["do"],
            "cpamm": active["cpamm"],
            "dosage": active["dosage"],
            "amax": active["amax"],
            "b": active["b"],
            "gama": active["gama"],
            "df0": active["df0"],
            "gof": active["gof"],
            "optimization_time": active["optimization_time"],
            "audit_run_id": active["audit_run_id"],
            "published_reference_data": PUBLISHED_REFERENCE_DATA.get(active["cpamm"]),
            "published_reference_label": "Published Table 2 reference (not optimizer output)",
            "published_reference_doi": PUBLISHED_REFERENCE_DOI,
        }


@router.get("/optimization_report")
async def optimization_report():
    active = get_active_optimization()
    if active is None or not active["audit_run_id"]:
        raise HTTPException(status_code=404, detail="No saved optimization report was found.")
    report = get_optimization_report(active["audit_run_id"])
    if report is None:
        raise HTTPException(status_code=404, detail="The audit report is unavailable.")
    job_id, report_json = report
    return Response(
        content=report_json,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="optimization-{job_id}.json"'},
    )


@router.delete("/delete_optimization_data")
async def delete_optimization_data():
    clear_active_optimization()
    return Response(status_code=200, content="ok")

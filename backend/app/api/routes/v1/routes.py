from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import Response
from app.pbm_model.optimization_simulation import optimization_task, check_status, stop_task, simulation_task
from app.schemas.schemas import SaveOptimizationResults
from app.models.optimized import Optimized
from app.core.redis_async import redis_async
from app.api.dependencies.data import OPTIMUM_DATA
import asyncio
from typing import List
from sse_starlette.sse import EventSourceResponse
import json


router = APIRouter()

@router.post("/start_optimize")
async def start_optimize(
        data: List = Form(...),
        file_exp: UploadFile = File(...),
        file_init: UploadFile = File(...)
):
    contents_exp = await file_exp.read()
    csv_str_exp = contents_exp.decode("utf-8")

    contents_init = await file_init.read()
    csv_str_init = contents_init.decode("utf-8")

    task = optimization_task.delay(csv_str_exp, csv_str_init, data[0], data[1], data[2], data[3], data[4])
    return str(task)


async def event_generator_decimer(task_id: str):
    try:
        while True:
            task_result = check_status(task_id)

            if task_result.ready():
                if task_result.successful():
                    res_from_redis = await redis_async.get(task_id)
                    final_result = json.loads(res_from_redis)

                    final_data = {
                        "status": "completed",
                        "result": final_result
                    }
                    yield {"data": json.dumps(final_data)}
                else:
                    error_info = {"status": "failed", "error": "Задача провалена на бэкенде"}
                    yield {"data": json.dumps(error_info)}

                break
            else:
                processing_status = {"status": "processing"}
                yield {"data": json.dumps(processing_status)}

            await asyncio.sleep(1)
    except Exception as e:
        error_info = {"status": "failed", "error": str(e)}
        yield {"data": json.dumps(error_info)}


@router.get("/get_result_optimization/{task_id}")
async def get_result_decimer(task_id: str):
    return EventSourceResponse(event_generator_decimer(str(task_id)))


@router.delete("/stop_task/{task_id}")
async def stop_optimization(task_id: str):
    stop_task(task_id)
    return Response(status_code=200, content="ok")


@router.post("/save_optimization_results")
async def save_optimization_results(data: SaveOptimizationResults):
    res_from_redis = await redis_async.get(data.task_id)
    res = json.loads(res_from_redis)
    await Optimized.objects.delete(each=True)
    await Optimized.objects.create(**{
        "g": res["g"],
        "do": res["do"],
        "cpamm": res["cpamm"],
        "dosage": res["dosage"],
        "amax": res["amax"],
        "b": res["B"],
        "gama": res["gama"],
        "gof": res["gof"],
        "optimization_time": res["optimization_time"]
    })
    await redis_async.delete(data.task_id)
    return Response(status_code=200, content="ok")


@router.post("/start_simulation")
async def start_simulation(file: UploadFile = File(...)):
    content = await file.read()
    csv_str = content.decode("utf-8")
    data_list = await Optimized.objects.all()
    data = data_list[0]
    task = simulation_task.delay(
        {
            "amax": data.amax,
            "B": data.b,
            "gama": data.gama
        },
        data.g,
        data.do,
        csv_str
    )
    return str(task)


@router.delete("/reset_state")
async def reset_state():
    await redis_async.delete("previous")
    return Response(status_code=200, content="ok")


@router.get("/get_result_simulation/{task_id}")
async def get_result_simulation(task_id: str):
    return EventSourceResponse(event_generator_decimer(str(task_id)))


@router.get("/check_simulation_state")
async def check_simulation_state():
    response = await redis_async.get("previous")
    if response is None:
        return {"has_state": False}
    else:
        return {"has_state": True}


@router.get("/check_optimization")
async def check_optimization():
    response = await Optimized.objects.all()
    if len(response) == 0:
        return {
            "response": False
        }
    else:
        return {
            "response": True,
            "g": response[0].g,
            "do": response[0].do,
            "cpamm": response[0].cpamm,
            "dosage": response[0].dosage,
            "amax": response[0].amax,
            "b": response[0].b,
            "gama": response[0].gama,
            "gof": response[0].gof,
            "optimization_time": response[0].optimization_time,
            "optimum_data": OPTIMUM_DATA[response[0].cpamm]
        }


@router.delete("/delete_optimization_data")
async def delete_optimization_data():
    await Optimized.objects.delete(each=True)
    return Response(status_code=200, content="ok")

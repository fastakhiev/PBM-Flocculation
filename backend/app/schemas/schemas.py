from pydantic import BaseModel

class StartOptimize(BaseModel):
    g: float
    d_fo: float
    d_f_max: float
    d_o: float


class SaveOptimizationResults(BaseModel):
    task_id: str

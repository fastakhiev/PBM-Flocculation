from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.db import database

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    await database.connect()
    print("start")


@app.on_event("shutdown")
async def shutdown() -> None:
    await database.disconnect()
    print("stop")


app.include_router(router)

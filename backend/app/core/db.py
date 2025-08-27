import ormar
from databases import Database
from sqlalchemy import MetaData, create_engine
from app.core import config


database_url = (
    f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:"
    f"{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
)
database = Database(database_url)
metadata = MetaData()

base_ormar_config = ormar.OrmarConfig(
    metadata=metadata, database=database, engine=create_engine(database_url)
)
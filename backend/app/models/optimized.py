import ormar
from app.core.db import base_ormar_config
from uuid import UUID, uuid4


class Optimized(ormar.Model):
    ormar_config = base_ormar_config.copy(tablename="optimized")
    id: UUID = ormar.UUID(primary_key=True, default=uuid4)
    g: float = ormar.Float(nullable=False)
    do: float = ormar.Float(nullable=False)
    cpamm: str = ormar.String(max_length=512, nullable=False)
    dosage: int = ormar.Integer(nullable=False)
    amax: float = ormar.Float(nullable=False)
    b: float = ormar.Float(nullable=False)
    gama: float = ormar.Float(nullable=False)
    gof: float = ormar.Float(nullable=False)
    optimization_time: float = ormar.Float(nullable=False)

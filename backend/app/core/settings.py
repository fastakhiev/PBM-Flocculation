from functools import lru_cache
import os


class Settings:
    # SQLite file location. If relative, resolved against current working directory.
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "pbm.sqlite3")
    CORS_ORIGINS: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8080,http://localhost:8080",
        ).split(",")
        if origin.strip()
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

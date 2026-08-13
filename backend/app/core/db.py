from __future__ import annotations

import os
import json
import sqlite3
import sys
import threading
from pathlib import Path
from uuid import uuid4

from app.core import config


_DB_LOCK = threading.RLock()


def _database_path() -> Path:
    if getattr(sys, "frozen", False):
        if sys.platform == "win32" and os.getenv("LOCALAPPDATA"):
            base_dir = Path(os.environ["LOCALAPPDATA"]) / "PBM-Flocculation"
        else:
            base_dir = Path.home() / ".local" / "share" / "PBM-Flocculation"
    else:
        base_dir = Path.cwd()
    path = Path(config.SQLITE_PATH)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(), timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_db_and_tables() -> None:
    with _DB_LOCK, _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS optimization_runs (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                software_version TEXT NOT NULL,
                protocol_version TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                experimental_sha256 TEXT NOT NULL,
                moments_sha256 TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS optimized (
                id TEXT PRIMARY KEY,
                g REAL NOT NULL,
                do REAL NOT NULL,
                cpamm TEXT NOT NULL,
                dosage INTEGER NOT NULL,
                amax REAL NOT NULL,
                b REAL NOT NULL,
                gama REAL NOT NULL,
                df0 REAL,
                gof REAL NOT NULL,
                optimization_time REAL NOT NULL,
                moments_json TEXT,
                audit_run_id TEXT
            )
            """
        )
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(optimized)").fetchall()
        }
        if "moments_json" not in columns:
            connection.execute("ALTER TABLE optimized ADD COLUMN moments_json TEXT")
        if "audit_run_id" not in columns:
            connection.execute("ALTER TABLE optimized ADD COLUMN audit_run_id TEXT")
        if "df0" not in columns:
            connection.execute("ALTER TABLE optimized ADD COLUMN df0 REAL")


def save_optimization_result(job_id: str, result: dict, report_json: str, created_at: str) -> str:
    provenance = result["provenance"]
    with _DB_LOCK, _connect() as connection:
        existing = connection.execute(
            "SELECT id FROM optimization_runs WHERE job_id = ?", (job_id,)
        ).fetchone()
        audit_id = existing["id"] if existing else str(uuid4())
        if existing is None:
            connection.execute(
                """
                INSERT INTO optimization_runs (
                    id, job_id, created_at, software_version, protocol_version,
                    algorithm, experimental_sha256, moments_sha256, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    job_id,
                    created_at,
                    provenance["software_version"],
                    provenance["protocol_version"],
                    result["algorithm"]["name"],
                    provenance["experimental_sha256"],
                    provenance["moments_sha256"],
                    report_json,
                ),
            )
        connection.execute("DELETE FROM optimized")
        connection.execute(
            """
            INSERT INTO optimized (
                id, g, do, cpamm, dosage, amax, b, gama, df0, gof,
                optimization_time, moments_json, audit_run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                result["g"],
                result["do"],
                result["cpamm"],
                result["dosage"],
                result["amax"],
                result["B"],
                result["gama"],
                result.get("df0"),
                result["gof"],
                result["optimization_time"],
                json.dumps(result["moments"]),
                audit_id,
            ),
        )
    return audit_id


def get_active_optimization() -> dict | None:
    with _DB_LOCK, _connect() as connection:
        row = connection.execute("SELECT * FROM optimized LIMIT 1").fetchone()
    return None if row is None else dict(row)


def get_optimization_report(audit_run_id: str) -> tuple[str, str] | None:
    with _DB_LOCK, _connect() as connection:
        row = connection.execute(
            "SELECT job_id, report_json FROM optimization_runs WHERE id = ?", (audit_run_id,)
        ).fetchone()
    if row is None:
        return None
    return row["job_id"], row["report_json"]


def clear_active_optimization() -> None:
    with _DB_LOCK, _connect() as connection:
        connection.execute("DELETE FROM optimized")

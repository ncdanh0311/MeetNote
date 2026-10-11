"""Small SQLite repository for job state and result metadata."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class JobsRepository:
    def __init__(self, database: str | Path):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    result_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )

    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create(self, job_id: str, filename: str, engine: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO jobs
                   (job_id, filename, engine, status, message, created_at, updated_at)
                   VALUES (?, ?, ?, 'queued', 'Đang chờ xử lý...', ?, ?)""",
                (job_id, filename, engine, now, now),
            )

    def update(self, job_id: str, **values) -> None:
        allowed = {"status", "message", "result_path"}
        if not values or values.keys() - allowed:
            raise ValueError("Unsupported job fields")
        values["updated_at"] = datetime.now(timezone.utc).isoformat()
        assignments = ", ".join(f"{key} = ?" for key in values)
        parameters = [*values.values(), job_id]
        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE jobs SET {assignments} WHERE job_id = ?", parameters
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Unknown job: {job_id}")

    def get(self, job_id: str) -> dict | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_recent(self, limit: int = 20) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT job_id, filename, engine, status, message, created_at
                   FROM jobs ORDER BY created_at DESC LIMIT ?""",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def fail_interrupted_jobs(self) -> list[str]:
        """Mark unfinished jobs clearly if the local server restarted mid-run."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT job_id FROM jobs WHERE status IN "
                "('queued', 'splitting', 'transcribing', 'summarizing')"
            ).fetchall()
            connection.execute(
                """UPDATE jobs
                   SET status = 'error',
                       message = 'Server đã khởi động lại khi job đang chạy. Hãy tải file lên lại.',
                       updated_at = ?
                   WHERE status IN ('queued', 'splitting', 'transcribing', 'summarizing')""",
                (now,),
            )
        return [row["job_id"] for row in rows]

    def ping(self) -> bool:
        with self._connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return True

import json
import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from typing import Any, Generator, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "refactoring_history.db")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional SQLite connection with dictionary-style row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the refactoring_history table and safely migrate older schemas if needed."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refactoring_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filename TEXT NOT NULL,
                mode TEXT NOT NULL,
                target_stack TEXT NOT NULL,
                custom_instructions TEXT NOT NULL,
                detected_language TEXT NOT NULL,
                detected_framework TEXT NOT NULL,
                original_code TEXT NOT NULL,
                refactored_code TEXT NOT NULL,
                summary TEXT NOT NULL,
                changes_made_json TEXT NOT NULL,
                dependency_migrations_json TEXT NOT NULL,
                breaking_changes_json TEXT NOT NULL,
                verification_steps_json TEXT NOT NULL,
                confidence_score INTEGER NOT NULL,
                model_used TEXT NOT NULL,
                lines_before INTEGER NOT NULL DEFAULT 0,
                lines_after INTEGER NOT NULL DEFAULT 0,
                second_agent_model TEXT NOT NULL DEFAULT '',
                second_agent_verdict TEXT NOT NULL DEFAULT '',
                second_agent_notes_json TEXT NOT NULL DEFAULT '[]',
                second_agent_score INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Safely add new columns if refactoring_history.db was created in an earlier step
        existing_cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(refactoring_history)").fetchall()
        }
        migrations = {
            "lines_before": "INTEGER NOT NULL DEFAULT 0",
            "lines_after": "INTEGER NOT NULL DEFAULT 0",
            "second_agent_model": "TEXT NOT NULL DEFAULT ''",
            "second_agent_verdict": "TEXT NOT NULL DEFAULT ''",
            "second_agent_notes_json": "TEXT NOT NULL DEFAULT '[]'",
            "second_agent_score": "INTEGER NOT NULL DEFAULT 0",
        }
        for col_name, col_def in migrations.items():
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE refactoring_history ADD COLUMN {col_name} {col_def}")

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_refactoring_history_created_at
            ON refactoring_history (created_at DESC, id DESC)
            """
        )


def _safe_load_json_list(raw_value: str) -> list[str]:
    """Safely deserialize a JSON array stored as text."""
    try:
        parsed = json.loads(raw_value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _count_lines(text: str) -> int:
    """Count non-empty/normalized lines in a code snippet."""
    if not text:
        return 0
    return len(text.replace("\r\n", "\n").split("\n"))


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a SQLite Row into a clean API-ready dictionary."""
    original_code = row["original_code"]
    refactored_code = row["refactored_code"]
    lines_before = row["lines_before"] if row["lines_before"] > 0 else _count_lines(original_code)
    lines_after = row["lines_after"] if row["lines_after"] > 0 else _count_lines(refactored_code)

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "filename": row["filename"],
        "mode": row["mode"],
        "target_stack": row["target_stack"],
        "custom_instructions": row["custom_instructions"],
        "detected_language": row["detected_language"],
        "detected_framework": row["detected_framework"],
        "original_code": original_code,
        "refactored_code": refactored_code,
        "summary": row["summary"],
        "changes_made": _safe_load_json_list(row["changes_made_json"]),
        "dependency_migrations": _safe_load_json_list(row["dependency_migrations_json"]),
        "breaking_changes_and_risks": _safe_load_json_list(row["breaking_changes_json"]),
        "verification_steps": _safe_load_json_list(row["verification_steps_json"]),
        "confidence_score": row["confidence_score"],
        "model_used": row["model_used"],
        "lines_before": lines_before,
        "lines_after": lines_after,
        "second_agent_model": row["second_agent_model"],
        "second_agent_verdict": row["second_agent_verdict"],
        "second_agent_notes": _safe_load_json_list(row["second_agent_notes_json"]),
        "second_agent_score": row["second_agent_score"],
    }


def save_refactoring_record(
    *,
    filename: str,
    mode: str,
    target_stack: str,
    custom_instructions: str,
    detected_language: str,
    detected_framework: str,
    original_code: str,
    refactored_code: str,
    summary: str,
    changes_made: list[str],
    dependency_migrations: list[str],
    breaking_changes_and_risks: list[str],
    verification_steps: list[str],
    confidence_score: int,
    model_used: str,
    second_agent_model: str = "",
    second_agent_verdict: str = "",
    second_agent_notes: Optional[list[str]] = None,
    second_agent_score: int = 0,
) -> dict[str, Any]:
    """Insert a completed refactoring run into SQLite and return the saved record."""
    lines_before = _count_lines(original_code)
    lines_after = _count_lines(refactored_code)
    notes_list = second_agent_notes or []

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO refactoring_history (
                filename,
                mode,
                target_stack,
                custom_instructions,
                detected_language,
                detected_framework,
                original_code,
                refactored_code,
                summary,
                changes_made_json,
                dependency_migrations_json,
                breaking_changes_json,
                verification_steps_json,
                confidence_score,
                model_used,
                lines_before,
                lines_after,
                second_agent_model,
                second_agent_verdict,
                second_agent_notes_json,
                second_agent_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                mode,
                target_stack,
                custom_instructions,
                detected_language,
                detected_framework,
                original_code,
                refactored_code,
                summary,
                json.dumps(changes_made),
                json.dumps(dependency_migrations),
                json.dumps(breaking_changes_and_risks),
                json.dumps(verification_steps),
                confidence_score,
                model_used,
                lines_before,
                lines_after,
                second_agent_model,
                second_agent_verdict,
                json.dumps(notes_list),
                second_agent_score,
            ),
        )
        record_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM refactoring_history WHERE id = ?",
            (record_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError("Failed to retrieve the newly saved refactoring record.")
    return _row_to_dict(row)


def get_refactoring_history(limit: int = 50) -> list[dict[str, Any]]:
    """Fetch recent refactoring runs ordered from newest to oldest."""
    safe_limit = max(1, min(limit, 200))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM refactoring_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_refactoring_by_id(record_id: int) -> Optional[dict[str, Any]]:
    """Fetch a single refactoring record by its primary key ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM refactoring_history WHERE id = ?",
            (record_id,),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def delete_refactoring_by_id(record_id: int) -> bool:
    """Delete a single refactoring record by ID. Returns True if a row was removed."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM refactoring_history WHERE id = ?",
            (record_id,),
        )
        return cursor.rowcount > 0


def clear_refactoring_history() -> int:
    """Delete all refactoring history records and return the number removed."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM refactoring_history")
        return cursor.rowcount


def get_analytics_summary() -> dict[str, Any]:
    """Compute aggregated metrics and chart series from SQLite history."""
    items = get_refactoring_history(limit=200)
    total_runs = len(items)
    if total_runs == 0:
        return {
            "total_runs": 0,
            "average_confidence": 0,
            "total_migrations": 0,
            "total_improvements": 0,
            "total_lines_before": 0,
            "total_lines_after": 0,
            "dual_agent_runs": 0,
            "languages": [],
            "modes": [],
            "recent_trend": [],
        }

    total_conf = sum(int(item["confidence_score"]) for item in items)
    total_migrations = sum(len(item["dependency_migrations"]) for item in items)
    total_improvements = sum(len(item["changes_made"]) for item in items)
    total_lines_before = sum(int(item["lines_before"]) for item in items)
    total_lines_after = sum(int(item["lines_after"]) for item in items)
    dual_agent_runs = sum(1 for item in items if item.get("second_agent_model"))

    lang_counts = Counter(item["detected_language"] or "Unknown" for item in items)
    mode_counts = Counter(item["mode"] or "full_autonomous" for item in items)

    recent_trend = [
        {
            "id": item["id"],
            "filename": item["filename"],
            "confidence_score": item["confidence_score"],
            "lines_before": item["lines_before"],
            "lines_after": item["lines_after"],
        }
        for item in reversed(items[:8])
    ]

    return {
        "total_runs": total_runs,
        "average_confidence": round(total_conf / total_runs),
        "total_migrations": total_migrations,
        "total_improvements": total_improvements,
        "total_lines_before": total_lines_before,
        "total_lines_after": total_lines_after,
        "dual_agent_runs": dual_agent_runs,
        "languages": [{"name": k, "count": v} for k, v in lang_counts.most_common(6)],
        "modes": [{"name": k, "count": v} for k, v in mode_counts.most_common(4)],
        "recent_trend": recent_trend,
    }
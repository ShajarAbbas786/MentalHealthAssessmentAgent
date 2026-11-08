"""SQLite storage functions for assessment records."""

import json
import sqlite3

from datetime import datetime, timezone

from config import DATABASE_PATH


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    return connection


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------

def initialize_database():

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS assessment_records (

                assessment_id TEXT PRIMARY KEY,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                answers_json TEXT NOT NULL,

                validation_json TEXT NOT NULL,

                summary TEXT DEFAULT '',

                completion_status TEXT DEFAULT 'incomplete',

                review_status TEXT DEFAULT 'pending',

                professional_attention INTEGER DEFAULT 0,

                reviewer_decision TEXT DEFAULT 'pending',

                reviewer_notes TEXT DEFAULT ''

            )
        """)

        # Database migration for older project versions

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(assessment_records)"
            ).fetchall()
        }

        if "updated_at" not in columns:

            connection.execute(
                "ALTER TABLE assessment_records "
                "ADD COLUMN updated_at TEXT DEFAULT ''"
            )

        if "review_status" not in columns:

            connection.execute(
                "ALTER TABLE assessment_records "
                "ADD COLUMN review_status TEXT DEFAULT 'pending'"
            )

        connection.commit()


# --------------------------------------------------
# SAVE ASSESSMENT RECORD
# --------------------------------------------------

def save_record(
    assessment_id,
    answers,
    validation,
    completion_status,
    professional_attention,
    review_status="pending"
):

    initialize_database()

    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:

        connection.execute("""

            INSERT INTO assessment_records (

                assessment_id,
                created_at,
                updated_at,
                answers_json,
                validation_json,
                completion_status,
                review_status,
                professional_attention

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(assessment_id) DO UPDATE SET

                updated_at = excluded.updated_at,

                answers_json = excluded.answers_json,

                validation_json = excluded.validation_json,

                completion_status = excluded.completion_status,

                review_status = excluded.review_status,

                professional_attention = excluded.professional_attention

        """, (

            assessment_id,

            now,

            now,

            json.dumps(
                answers,
                ensure_ascii=False
            ),

            json.dumps(
                validation,
                ensure_ascii=False
            ),

            completion_status,

            review_status,

            int(bool(professional_attention))

        ))

        connection.commit()


# --------------------------------------------------
# UPDATE ASSESSMENT RECORD
# --------------------------------------------------

def update_record(
    assessment_id,
    *,
    summary=None,
    completion_status=None,
    review_status=None,
    reviewer_decision=None,
    reviewer_notes=None
):

    initialize_database()

    fields = []
    values = []

    updates = [

        ("summary", summary),

        ("completion_status", completion_status),

        ("review_status", review_status),

        ("reviewer_decision", reviewer_decision),

        ("reviewer_notes", reviewer_notes)

    ]

    for column, value in updates:

        if value is not None:

            fields.append(f"{column} = ?")

            values.append(value)

    fields.append("updated_at = ?")

    values.append(
        datetime.now(timezone.utc).isoformat()
    )

    values.append(assessment_id)

    with get_connection() as connection:

        connection.execute(

            f"""
            UPDATE assessment_records

            SET {', '.join(fields)}

            WHERE assessment_id = ?
            """,

            values

        )

        connection.commit()


# --------------------------------------------------
# CONVERT DATABASE RECORD
# --------------------------------------------------

def _convert_record(row):

    item = dict(row)

    item["answers"] = json.loads(
        item.pop("answers_json")
    )

    item["validation"] = json.loads(
        item.pop("validation_json")
    )

    item["professional_attention"] = bool(
        item["professional_attention"]
    )

    return item


# --------------------------------------------------
# RETRIEVE ONE ASSESSMENT
# --------------------------------------------------

def get_record(assessment_id):

    initialize_database()

    with get_connection() as connection:

        row = connection.execute(

            """
            SELECT *

            FROM assessment_records

            WHERE assessment_id = ?
            """,

            (assessment_id,)

        ).fetchone()

    return _convert_record(row) if row else None


# --------------------------------------------------
# RETRIEVE PREVIOUS ASSESSMENTS
# --------------------------------------------------

def get_recent_records(limit=20):

    initialize_database()

    limit = max(
        1,
        min(int(limit), 200)
    )

    with get_connection() as connection:

        rows = connection.execute(

            """
            SELECT *

            FROM assessment_records

            ORDER BY updated_at DESC

            LIMIT ?
            """,

            (limit,)

        ).fetchall()

    return [
        _convert_record(row)
        for row in rows
    ]
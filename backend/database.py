
import sqlite3
import os
import json

from pathlib import Path
from datetime import datetime, timezone


# --------------------------------------------------
# Database path configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# Render uses its persistent disk when configured.
# Otherwise, use local backend storage.
if os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/certiai_certificates.db")
else:
    DB_PATH = BASE_DIR / "certificates.db"


# --------------------------------------------------
# Database connection
# --------------------------------------------------

def get_connection():
    """Create a connection to the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


# --------------------------------------------------
# Initialize database
# --------------------------------------------------

def initialize_database():
    """Create the required database tables."""

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                certificate_id TEXT NOT NULL UNIQUE,
                participant_name TEXT NOT NULL,
                event TEXT NOT NULL,
                organization TEXT NOT NULL,
                certificate_date TEXT NOT NULL,
                achievement TEXT NOT NULL,
                generated_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS custom_template_layouts (
                template_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL,
                layout_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


# --------------------------------------------------
# Save certificate
# --------------------------------------------------

def save_certificate(
    certificate_id,
    name,
    event,
    organization,
    certificate_date,
    achievement
):
    """Save a certificate record."""

    generated_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO certificates (
                certificate_id,
                participant_name,
                event,
                organization,
                certificate_date,
                achievement,
                generated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            certificate_id,
            name,
            event,
            organization,
            certificate_date,
            achievement,
            generated_at
        ))


# --------------------------------------------------
# Retrieve all certificates
# --------------------------------------------------

def get_all_certificates():
    """Retrieve all saved certificates."""

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM certificates
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


# --------------------------------------------------
# Retrieve certificate by ID
# --------------------------------------------------

def get_certificate(certificate_id):
    """Retrieve a certificate using its ID."""

    with get_connection() as connection:
        row = connection.execute("""
            SELECT * FROM certificates
            WHERE certificate_id = ?
        """, (certificate_id,)).fetchone()

        return dict(row) if row else None


# --------------------------------------------------
# Save custom template layout
# --------------------------------------------------

def save_template_layout(
    template_id,
    filename,
    image_width,
    image_height,
    layout
):
    """Save or update the editable layout for a custom template."""

    if not isinstance(layout, dict):
        raise ValueError("Layout must be a dictionary")

    now = datetime.now(timezone.utc).isoformat()
    layout_json = json.dumps(layout)

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO custom_template_layouts (
                template_id,
                filename,
                image_width,
                image_height,
                layout_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(template_id) DO UPDATE SET
                filename = excluded.filename,
                image_width = excluded.image_width,
                image_height = excluded.image_height,
                layout_json = excluded.layout_json,
                updated_at = excluded.updated_at
        """, (
            template_id,
            filename,
            image_width,
            image_height,
            layout_json,
            now,
            now
        ))


# --------------------------------------------------
# Retrieve custom template layout
# --------------------------------------------------

def get_template_layout(template_id):
    """Retrieve a custom template and its saved layout."""

    with get_connection() as connection:
        row = connection.execute("""
            SELECT * FROM custom_template_layouts
            WHERE template_id = ?
        """, (template_id,)).fetchone()

        if not row:
            return None

        result = dict(row)

        layout_json = result.pop("layout_json", "{}")

        try:
            result["layout"] = json.loads(layout_json)
        except (json.JSONDecodeError, TypeError):
            result["layout"] = {}

        return result


# --------------------------------------------------
# Run database initialization
# --------------------------------------------------

if __name__ == "__main__":
    initialize_database()

    print("CertiAI database initialized successfully.")
    print(f"Database location: {DB_PATH}")

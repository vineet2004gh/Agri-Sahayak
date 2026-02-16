import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import bcrypt
from pathlib import Path


def get_db_connection():
    # Anchor the DB file to the backend directory to avoid path confusion
    db_path = Path(__file__).resolve().parent / "documents.db"
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    # Ensure foreign key constraints are enforced for every connection
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _normalize_phone_number(phone: Optional[str]) -> Optional[str]:
    """Normalize phone numbers to E.164 for India (+91XXXXXXXXXX).

    - If input is 10 digits, prefix with +91.
    - If input is 12 digits starting with 91, prefix with +.
    - If input already has + and digits, keep + and digits only.
    - Strip spaces, dashes, and other non-digits.
    """
    if not phone:
        return None
    raw = phone.strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    # Fallback: preserve plus if originally present, otherwise add it
    if raw.startswith("+"):
        return "+" + digits
    return "+" + digits


# Initialize the database tables if they don't exist
with get_db_connection() as conn:
    cursor = conn.cursor()

    # Create users table (new)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            district TEXT,
            crop TEXT,
            state TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            phone_number TEXT,
            language TEXT
        )
        """
    )

    # Ensure 'state' column exists for legacy DBs
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cursor.fetchall()]
    if "state" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN state TEXT")
    if "email" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "password_hash" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "phone_number" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
    if "language" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN language TEXT")

    # Ensure unique index on email (if provided)
    cursor.execute("PRAGMA index_list(users)")
    existing_indexes = [row[1] for row in cursor.fetchall()]  # row[1] is index name
    if "idx_users_email_unique" not in existing_indexes:
        # Partial unique index so multiple NULL emails are allowed
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL"
        )
    # Ensure unique index on phone_number (if provided)
    cursor.execute("PRAGMA index_list(users)")
    existing_indexes = [row[1] for row in cursor.fetchall()]
    if "idx_users_phone_unique" not in existing_indexes:
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users(phone_number) WHERE phone_number IS NOT NULL"
        )

    # Ensure conversations table matches the new schema (with user_id)
    cursor.execute("PRAGMA table_info(conversations)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    needs_recreate = (
        ("user_id" not in existing_columns) or
        ("pdf_id" in existing_columns)
    )

    if needs_recreate:
        # Rename old table if it exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE conversations RENAME TO conversations_legacy")

        # Create new conversations table with user_id and FK
        cursor.execute(
            """
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Drop legacy table if present (no automatic data migration possible)
        cursor.execute("DROP TABLE IF EXISTS conversations_legacy")

    # Ensure conversation_id column exists
    cursor.execute("PRAGMA table_info(conversations)")
    conv_cols = [row[1] for row in cursor.fetchall()]
    if "conversation_id" not in conv_cols:
        cursor.execute("ALTER TABLE conversations ADD COLUMN conversation_id TEXT")
    if "title" not in conv_cols:
        cursor.execute("ALTER TABLE conversations ADD COLUMN title TEXT")

    conn.commit()


def insert_conversation(user_id: str, question: str, answer: Optional[str], conversation_id: Optional[str] = None, title: Optional[str] = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Only set the title on the first entry of a conversation
        # Subsequent entries will have title=NULL
        cursor.execute(
            "INSERT INTO conversations (user_id, question, answer, timestamp, conversation_id, title) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, question, answer, datetime.now(), conversation_id, title),
        )
        conn.commit()


def fetch_conversations(user_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT question, answer, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def fetch_user_conversation_summaries(user_id: str) -> List[Dict[str, Any]]:
    """Return list of {conversation_id, title, first_timestamp} for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                c.conversation_id,
                -- Use the explicit title if it exists, otherwise fallback to the first question
                COALESCE(c.title, c.question) AS title,
                c.timestamp AS first_timestamp
            FROM conversations c
            JOIN (
                SELECT conversation_id, MIN(timestamp) AS first_ts
                FROM conversations
                WHERE user_id = ? AND conversation_id IS NOT NULL
                GROUP BY conversation_id
            ) t
            ON c.conversation_id = t.conversation_id AND c.timestamp = t.first_ts
            ORDER BY first_timestamp DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def fetch_conversation_by_id(conversation_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, question, answer, timestamp FROM conversations WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

def insert_user(
    name: str,
    district: Optional[str] = None,
    crop: Optional[str] = None,
    state: Optional[str] = None,
    email: Optional[str] = None,
    password_hash: Optional[str] = None,
    phone_number: Optional[str] = None,
    language: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Create a new user row. If user_id is not provided, generate a UUID."""
    new_user_id = user_id or str(uuid.uuid4())
    normalized_phone = _normalize_phone_number(phone_number)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, name, district, crop, state, email, password_hash, phone_number, language) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_user_id, name, district, crop, state, email, password_hash, normalized_phone, language),
        )
        conn.commit()
    return new_user_id


def fetch_users() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, district, crop, state, email, phone_number, language FROM users ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]


def fetch_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, district, crop, state, email, phone_number, language FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, district, crop, state, email, password_hash, phone_number, language FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_user_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Normalize lookup to match stored canonical format
        normalized = _normalize_phone_number(phone_number)
        for probe in [normalized, phone_number]:
            if not probe:
                continue
            cursor.execute(
                "SELECT id, name, district, crop, state, email, password_hash, phone_number, language FROM users WHERE phone_number = ?",
                (probe,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False

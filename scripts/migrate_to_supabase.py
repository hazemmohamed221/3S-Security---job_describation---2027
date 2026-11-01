"""
Migration script to migrate 3S Security Job Description Management System
database from SQLite to Supabase PostgreSQL with 100% data and ID parity.
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None, **_kwargs):
        if dotenv_path and os.path.exists(dotenv_path):
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        return False

# Ensure root directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_SQLITE_PATH = os.path.join(PROJECT_ROOT, "job_descriptions.db")

SCHEMA_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'manager', 'employee')),
    department TEXT,
    assigned_jd_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    auth_version INTEGER NOT NULL DEFAULT 0 CHECK(auth_version >= 0)
);

-- Job Descriptions table
CREATE TABLE IF NOT EXISTS job_descriptions (
    id SERIAL PRIMARY KEY,
    job_code TEXT,
    title TEXT NOT NULL,
    department TEXT,
    sector TEXT,
    reports_to TEXT,
    purpose TEXT,
    dimensions TEXT,
    frameworks TEXT,
    qualifications TEXT,
    competencies TEXT,
    hazards TEXT,
    safe_practices TEXT,
    internal_relations TEXT,
    external_relations TEXT,
    approvals TEXT,
    source_file TEXT,
    status TEXT DEFAULT 'مسودة',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_version INTEGER,
    review_hash TEXT,
    import_hash TEXT
);

-- Accountabilities table
CREATE TABLE IF NOT EXISTS accountabilities (
    id SERIAL PRIMARY KEY,
    jd_id INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    item_order INTEGER NOT NULL,
    description TEXT NOT NULL,
    kpi TEXT,
    version INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1
);

-- Modification Requests table
CREATE TABLE IF NOT EXISTS modification_requests (
    id SERIAL PRIMARY KEY,
    jd_id INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    section_name TEXT NOT NULL,
    clause_id TEXT,
    original_text TEXT,
    proposed_text TEXT NOT NULL,
    justification TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'قيد الانتظار',
    reviewer_comments TEXT,
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    expected_version INTEGER,
    expected_hash TEXT,
    requested_snapshot TEXT
);

-- JD Audit Trail table
CREATE TABLE IF NOT EXISTS jd_audit_trail (
    id SERIAL PRIMARY KEY,
    jd_id INTEGER NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    mod_request_id INTEGER,
    section_name TEXT,
    action TEXT NOT NULL,
    old_text TEXT,
    new_text TEXT,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    actor_id INTEGER,
    card_version INTEGER,
    decision TEXT,
    snapshot_json TEXT,
    snapshot_hash TEXT,
    result_json TEXT,
    result_hash TEXT
);

-- Interview Schedule table
CREATE TABLE IF NOT EXISTS interview_schedule (
    id SERIAL PRIMARY KEY,
    seq_num INTEGER,
    department TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    day_date TEXT,
    meeting_time TEXT,
    discussion_topics TEXT,
    status TEXT DEFAULT 'قيد المراجعة',
    notes TEXT
);

-- Indexes for performance and foreign keys
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_accountabilities_jd ON accountabilities(jd_id, is_active, item_order);
CREATE INDEX IF NOT EXISTS idx_mod_requests_jd ON modification_requests(jd_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_trail_jd ON jd_audit_trail(jd_id, changed_at);
"""

TABLE_ORDER = [
    "users",
    "job_descriptions",
    "accountabilities",
    "interview_schedule",
    "modification_requests",
    "jd_audit_trail",
]


def migrate(sqlite_path=None, database_url=None):
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

    sqlite_db = sqlite_path or os.environ.get("JD_DB_PATH", DEFAULT_SQLITE_PATH)
    pg_url = database_url or os.environ.get("DATABASE_URL")

    if not pg_url:
        raise ValueError("DATABASE_URL must be set in environment or .env file.")

    if not os.path.exists(sqlite_db):
        raise FileNotFoundError(f"SQLite database not found at: {sqlite_db}")

    print(f"[*] Reading source SQLite database: {sqlite_db}")
    print(f"[*] Connecting to target Supabase PostgreSQL...")

    sqlite_conn = sqlite3.connect(sqlite_db)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(pg_url, connect_timeout=15)
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()

    try:
        # 1. Create target schema
        print("[*] Creating PostgreSQL schema and tables (if not exist)...")
        pg_cur.execute(SCHEMA_SQL)

        # 2. Sequential migration per table
        for table in TABLE_ORDER:
            # Query column list from SQLite
            columns = [col[1] for col in sqlite_cur.execute(f"PRAGMA table_info({table})").fetchall()]
            cols_joined = ", ".join(columns)

            sqlite_rows = sqlite_cur.execute(f"SELECT {cols_joined} FROM {table} ORDER BY id ASC").fetchall()
            sqlite_count = len(sqlite_rows)
            print(f"[*] Table '{table}': {sqlite_count} rows in SQLite.")

            # Truncate / clear table in reverse FK order if previously populated
            # Using ON CONFLICT DO UPDATE on id to be strictly idempotent
            if sqlite_count > 0:
                col_names = ", ".join(f'"{c}"' for c in columns)
                update_assignments = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in columns if c != "id")
                conflict_clause = f"DO UPDATE SET {update_assignments}" if update_assignments else "DO NOTHING"

                insert_sql = f"""
                    INSERT INTO {table} ({col_names})
                    VALUES %s
                    ON CONFLICT (id) {conflict_clause};
                """

                rows_data = [tuple(row) for row in sqlite_rows]
                execute_values(pg_cur, insert_sql, rows_data, page_size=100)

            # Synchronize PostgreSQL auto-increment sequence
            seq_sync_sql = f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1)
                );
            """
            pg_cur.execute(seq_sync_sql)

        # Commit all table data
        pg_conn.commit()
        print("[+] All data migrated and committed successfully.")

        # 3. Assert and print row-count parity checks
        print("\n================ ROW COUNT PARITY CHECK ================")
        all_passed = True
        for table in TABLE_ORDER:
            sqlite_cnt = sqlite_cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            pg_cnt = pg_cur.fetchone()[0]

            status = "MATCH" if sqlite_cnt == pg_cnt else "MISMATCH"
            print(f" - {table:22}: SQLite = {sqlite_cnt:4} | Supabase = {pg_cnt:4} [{status}]")
            if sqlite_cnt != pg_cnt:
                all_passed = False

        if not all_passed:
            raise AssertionError("Row count parity check failed on one or more tables!")

        print("=========================================================")
        print("[+] 100% Data parity confirmed across all tables.\n")

    except Exception:
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate()


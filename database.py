import sqlite3
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "grader.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                email               TEXT UNIQUE NOT NULL,
                password            TEXT NOT NULL,
                email_verified      INTEGER DEFAULT 0,
                verification_code   TEXT,
                verification_sent_at TIMESTAMP,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migration: add email verification columns if upgrading an existing DB
        try:
            db.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            db.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            db.execute("ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        # Grandfather in existing users (they were created before verification existed)
        db.execute("UPDATE users SET email_verified = 1 WHERE email_verified IS NULL")
        db.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                year        TEXT NOT NULL,
                division    TEXT NOT NULL,
                contest     TEXT NOT NULL,
                passed      INTEGER NOT NULL DEFAULT 0,
                total       INTEGER NOT NULL DEFAULT 0,
                code        TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS submission_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id   INTEGER NOT NULL,
                test_index      INTEGER NOT NULL,
                input           TEXT,
                expected        TEXT,
                actual          TEXT,
                status          TEXT NOT NULL,
                runtime_ms      REAL,
                FOREIGN KEY (submission_id) REFERENCES submissions(id)
            )
        """)
        db.commit()


def create_user(email, password):
    with get_db() as db:
        try:
            db.execute(
                "INSERT INTO users (email, password) VALUES (?, ?)",
                (email, generate_password_hash(password)),
            )
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def create_pending_user(email, password, code):
    """Creates an unverified user with a verification code."""
    with get_db() as db:
        try:
            db.execute(
                "INSERT INTO users (email, password, email_verified, verification_code, verification_sent_at) "
                "VALUES (?, ?, 0, ?, datetime('now'))",
                (email, generate_password_hash(password), code),
            )
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def verify_email_code(email, code):
    """Checks the code and marks the user as verified. Returns True on success."""
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ? AND email_verified = 0 "
            "AND verification_code = ? "
            "AND verification_sent_at > datetime('now', '-15 minutes')",
            (email, code),
        ).fetchone()
        if user:
            db.execute(
                "UPDATE users SET email_verified = 1, verification_code = NULL, "
                "verification_sent_at = NULL WHERE email = ?",
                (email,),
            )
            db.commit()
            return True
        return False


def resend_verification_code(email):
    """Generates a new code for the user and returns it, or None if not found / already verified."""
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ? AND email_verified = 0",
            (email,),
        ).fetchone()
        if not user:
            return None
        code = f"{random.randint(100000, 999999)}"
        db.execute(
            "UPDATE users SET verification_code = ?, verification_sent_at = datetime('now') WHERE email = ?",
            (code, email),
        )
        db.commit()
        return code


def get_user_by_email(email):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def verify_user(email, password):
    user = get_user_by_email(email)
    if user and user["email_verified"] and check_password_hash(user["password"], password):
        return user
    return None


def save_submission(user_id, year, division, contest, passed, total, code):
    with get_db() as db:
        cursor = db.execute(
            """INSERT INTO submissions (user_id, year, division, contest, passed, total, code)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, year, division, contest, passed, total, code),
        )
        db.commit()
        return cursor.lastrowid


def get_recent_submissions(user_id, limit=5):
    with get_db() as db:
        return db.execute(
            """SELECT year, division, contest, passed, total, created_at
               FROM submissions
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()


def get_user_submissions(user_id):
    with get_db() as db:
        return db.execute(
            """SELECT * FROM submissions
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()


def get_contest_result(user_id, year, division, contest):
    with get_db() as db:
        return db.execute(
            """SELECT passed, total FROM submissions
               WHERE user_id = ? AND year = ? AND division = ? AND contest = ?
               ORDER BY passed DESC LIMIT 1""",
            (user_id, year, division, contest),
        ).fetchone()


def save_submission_results(submission_id, results):
    with get_db() as db:
        for r in results:
            db.execute(
                """INSERT INTO submission_results
                   (submission_id, test_index, input, expected, actual, status, runtime_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (submission_id, r["test_index"], r["input"], r["expected"],
                 r["actual"], r["status"], r.get("runtime_ms"))
            )
        db.commit()


def get_submission_history(user_id, year=None, division=None, contest=None):
    with get_db() as db:
        query = """SELECT s.id, s.year, s.division, s.contest,
                          s.passed, s.total, s.created_at,
                          AVG(sr.runtime_ms) as avg_runtime
                   FROM submissions s
                   LEFT JOIN submission_results sr ON sr.submission_id = s.id
                   WHERE s.user_id = ?"""
        params = [user_id]
        if year:
            query += " AND s.year = ?"
            params.append(year)
        if division:
            query += " AND s.division = ?"
            params.append(division)
        if contest:
            query += " AND s.contest = ?"
            params.append(contest)
        query += " GROUP BY s.id ORDER BY s.created_at DESC"
        return db.execute(query, params).fetchall()


def get_submission_detail(submission_id):
    with get_db() as db:
        return db.execute(
            """SELECT * FROM submission_results
               WHERE submission_id = ?
               ORDER BY test_index""",
            (submission_id,),
        ).fetchall()


def get_leaderboard_most_solved(limit=20):
    with get_db() as db:
        return db.execute("""
            SELECT u.email, COUNT(*) as solved_count
            FROM submissions s
            JOIN users u ON u.id = s.user_id
            WHERE s.passed = s.total AND s.total > 0
            GROUP BY s.user_id
            ORDER BY solved_count DESC
            LIMIT ?
        """, (limit,)).fetchall()


def get_leaderboard_fastest_solves():
    with get_db() as db:
        return db.execute("""
            SELECT u.email, s.year, s.division, s.contest,
                   MIN(sr.runtime_ms) as best_runtime
            FROM submissions s
            JOIN users u ON u.id = s.user_id
            JOIN submission_results sr ON sr.submission_id = s.id
            WHERE s.passed = s.total AND s.total > 0
            GROUP BY s.id
            ORDER BY best_runtime ASC
        """).fetchall()


def get_leaderboard_longest(limit=20):
    with get_db() as db:
        return db.execute("""
            SELECT email, created_at
            FROM users
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,)).fetchall()


def get_worst_performing_cases(user_id, year, division, contest):
    with get_db() as db:
        return db.execute(
            """SELECT sr.test_index, sr.input, sr.expected,
                      COUNT(*) as fail_count
               FROM submission_results sr
               JOIN submissions s ON s.id = sr.submission_id
               WHERE s.user_id = ? AND s.year = ? AND s.division = ? AND s.contest = ?
                     AND sr.status != 'PASS'
               GROUP BY sr.test_index
               ORDER BY fail_count DESC""",
            (user_id, year, division, contest),
        ).fetchall()

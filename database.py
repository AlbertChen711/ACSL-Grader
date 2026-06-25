import sqlite3
import os
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
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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


def get_user_by_email(email):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def verify_user(email, password):
    user = get_user_by_email(email)
    if user and check_password_hash(user["password"], password):
        return user
    return None


def save_submission(user_id, year, division, contest, passed, total, code):
    with get_db() as db:
        db.execute(
            """INSERT INTO submissions (user_id, year, division, contest, passed, total, code)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, year, division, contest, passed, total, code),
        )
        db.commit()


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
               ORDER BY created_at DESC LIMIT 1""",
            (user_id, year, division, contest),
        ).fetchone()

import sqlite3
from contextlib import contextmanager

@contextmanager
def get_connection():
    conn = sqlite3.connect('data/data.db')
    try:
        yield conn
    finally:
        conn.close()

def get_users_count():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count

def get_all_user_ids():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        user_ids = [row[0] for row in cursor.fetchall()]
        return user_ids
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Tuple


os.makedirs('data', exist_ok=True)

@contextmanager
def get_connection():
    conn = sqlite3.connect('data/data.db')
    try:
        yield conn
    finally:
        conn.close()


def create_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                user_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN start_param TEXT')
        except sqlite3.OperationalError:        
            pass
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN status TEXT DEFAULT "active"')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT "❌Не подписан"')
        except sqlite3.OperationalError:        
            pass
        
        conn.commit()


def check_user(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        return user


def add_user(user_id, username, start_param=None):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (user_id, user_name, join_date, last_activity, status, start_param, subscription_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, current_time, current_time, 'active', start_param, '❌Не подписан'))
            conn.commit()
    except sqlite3.IntegrityError:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Оновлюємо тільки last_activity, start_param залишаємо без змін
            cursor.execute('''
                UPDATE users SET last_activity = ? WHERE user_id = ?
            ''', (current_time, user_id))
            
            conn.commit()

def update_user_activity(user_id):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_activity = ? WHERE user_id = ?
        ''', (current_time, user_id))
        
        conn.commit()


def update_user_start_param(user_id, start_param):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET start_param = ? WHERE user_id = ?
        ''', (start_param, user_id))
        
        conn.commit()

def get_user_start_param(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT start_param FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        return result[0] if result else None


def get_users_by_status(status: str) -> List[Tuple]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE status = ?', (status,))
        return cursor.fetchall()



def change_user_channel_status(user_id: int, channel_status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET channel_status = ? WHERE user_id = ?', (channel_status, user_id))
        conn.commit()
        return cursor.rowcount > 0


def get_start_params_stats():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT start_param, COUNT(*) as count 
            FROM users 
            WHERE start_param IS NOT NULL 
            GROUP BY start_param 
            ORDER BY count DESC
        ''') 
        
        stats = cursor.fetchall()
        return stats


def get_users_count():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        
        return count

def get_users_list(page=1, per_page=100):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        
        cursor.execute('''
            SELECT user_id, user_name, join_date, last_activity, start_param
            FROM users 
            ORDER BY join_date DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        users = cursor.fetchall()
        
        return users

def get_total_pages(per_page=100):
    total_users = get_users_count()
    return (total_users + per_page - 1) // per_page


def get_all_users():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, user_name, join_date, last_activity, start_param
            FROM users 
            ORDER BY join_date DESC
        ''')
        
        users = cursor.fetchall()
        return users


def update_user_status(user_id: int, status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET status = ?, last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (status, user_id))
        conn.commit()
        return cursor.rowcount > 0


def get_user_status(user_id: int) -> Optional[str]: 
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None



def update_user_status_by_action(user_id: int, action: str) -> bool:
    status_priority = {
        "start": 1,
        "captcha_passed": 2,
        "answers_viewed": 3, 
        "private_lesson_viewed": 4,
        "tariffs_viewed": 5,
        "clothes_tariff_viewed": 6,
        "tech_tariff_viewed": 7,
        "tech_payment_clicked": 8,
        "clothes_payment_clicked": 9
    }
    
    status_mapping = {
        "start": "Нажал старт",
        "captcha_passed": "Прошел капчу",
        "answers_viewed": "Посмотрел ответы", 
        "private_lesson_viewed": "Посмотрел приватный урок",
        "tariffs_viewed": "Посмотрел тарифы",
        "clothes_tariff_viewed": "Посмотрел тарифы одежда",
        "tech_tariff_viewed": "Посмотрел тарифы техника",
        "tech_payment_clicked": "Нажал оплатить техника",
        "clothes_payment_clicked": "Нажал оплатить одежда"
    }
    
    new_status = status_mapping.get(action)
    if not new_status:
        return False
    
    current_status = get_user_status(user_id)
    if not current_status:
        return update_user_status(user_id, new_status)
    
    current_priority = 0
    for action_key, priority in status_priority.items():
        if status_mapping[action_key] == current_status:
            current_priority = priority
            break
    
    new_priority = status_priority.get(action, 0)
    
    if new_priority >= current_priority:
        return update_user_status(user_id, new_status)
    
    print(f"⚠️ Не можна змінити статус з '{current_status}' (пріоритет {current_priority}) на '{new_status}' (пріоритет {new_priority})")
    return False


def admin_update_user_status(user_id: int, new_status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET status = ?, last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_status, user_id))
        conn.commit()
        return cursor.rowcount > 0


def get_users_with_statuses(page: int = 1, per_page: int = 20) -> tuple:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        total_pages = (total_users + per_page - 1) // per_page
        
        offset = (page - 1) * per_page
        cursor.execute('''
            SELECT user_id, user_name, join_date, last_activity, start_param, status, subscription_status
            FROM users 
            ORDER BY last_activity DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        users = cursor.fetchall()
        return users, total_users, total_pages, page, per_page


def update_subscription_status(user_id: int, subscription_status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET subscription_status = ?, last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (subscription_status, user_id))
        conn.commit()
        return cursor.rowcount > 0


def get_subscription_status(user_id: int) -> Optional[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT subscription_status FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else "❌Не подписан"


def get_users_with_subscription_statuses(page: int = 1, per_page: int = 20) -> tuple:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        total_pages = (total_users + per_page - 1) // per_page
        
        offset = (page - 1) * per_page
        cursor.execute('''
            SELECT user_id, user_name, join_date, last_activity, start_param, status, subscription_status
            FROM users 
            ORDER BY last_activity DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        users = cursor.fetchall()
        return users, total_users, total_pages, page, per_page


def get_subscription_stats() -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT subscription_status, COUNT(*) as count
            FROM users 
            GROUP BY subscription_status
        ''')
        
        stats = {}
        for row in cursor.fetchall():
            status, count = row
            stats[status] = count
        
        return stats


def admin_delete_user(user_id: int) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting user {user_id}: {e}")
        return False


# =========================
# Analytics helpers
# =========================

def _normalize_date_range(start_date: Optional[str], end_date: Optional[str]) -> Tuple[str, str]:
    """Return ISO date strings YYYY-MM-DD for SQLite date() comparisons.
    If not provided, defaults to last 30 days window.
    """
    from datetime import datetime, timedelta
    if not end_date:
        end = datetime.now().date()
    else:
        # Accept YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS]
        try:
            end = datetime.fromisoformat(end_date).date()
        except ValueError:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

    if not start_date:
        start = end - timedelta(days=29)
    else:
        try:
            start = datetime.fromisoformat(start_date).date()
        except ValueError:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()

    return (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))


def get_analytics_counts(start_date: Optional[str] = None, end_date: Optional[str] = None, param: Optional[str] = None) -> dict:
    """Return total counts: joined via links, moved to payment, paid within date range.
    - joined: users with start_param not null, filtered by join_date
    - to_payment: users whose current status is one of payment-clicked, filtered by last_activity
    - paid: users whose current status is one of paid, filtered by last_activity
    Optionally filter by specific start_param.
    """
    start_iso, end_iso = _normalize_date_range(start_date, end_date)

    params: List = [start_iso, end_iso]
    param_clause = ""
    if param:
        param_clause = " AND start_param = ?"
        params.append(param)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Joined via links (start_param present) within join_date window
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM users
            WHERE start_param IS NOT NULL
              AND date(join_date) BETWEEN date(?) AND date(?)
              {param_clause}
            """,
            tuple(params)
        )
        joined_count = cursor.fetchone()[0]

        # Moved to payment stage
        pay_params: List = [start_iso, end_iso]
        pay_clause = ""
        if param:
            pay_clause = " AND start_param = ?"
            pay_params.append(param)
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM users
            WHERE status IN ('Нажал оплатить техника','Нажал оплатить одежда')
              AND date(last_activity) BETWEEN date(?) AND date(?)
              {pay_clause}
            """,
            tuple(pay_params)
        )
        to_payment_count = cursor.fetchone()[0]

        # Paid
        paid_params: List = [start_iso, end_iso]
        paid_clause = ""
        if param:
            paid_clause = " AND start_param = ?"
            paid_params.append(param)
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM users
            WHERE status IN ('Оплатил одежду','Оплатил технику')
              AND date(last_activity) BETWEEN date(?) AND date(?)
              {paid_clause}
            """,
            tuple(paid_params)
        )
        paid_count = cursor.fetchone()[0]

        return {
            "joined": joined_count,
            "to_payment": to_payment_count,
            "paid": paid_count,
            "start_date": start_iso,
            "end_date": end_iso,
            "param": param or None
        }


def get_analytics_timeseries(start_date: Optional[str] = None, end_date: Optional[str] = None, param: Optional[str] = None) -> List[Tuple[str, int, int, int]]:
    """Return daily series: (day, joined, to_payment, paid) for each date in range.
    If no data for a day, include zero row.
    """
    start_iso, end_iso = _normalize_date_range(start_date, end_date)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Joined per day
        join_params: List = [start_iso, end_iso]
        join_clause = ""
        if param:
            join_clause = " AND start_param = ?"
            join_params.append(param)
        cursor.execute(
            f"""
            SELECT date(join_date) AS day, COUNT(*)
            FROM users
            WHERE start_param IS NOT NULL
              AND date(join_date) BETWEEN date(?) AND date(?)
              {join_clause}
            GROUP BY day
            ORDER BY day
            """,
            tuple(join_params)
        )
        join_rows = {row[0]: row[1] for row in cursor.fetchall()}

        # Payment clicks per day
        pay_params: List = [start_iso, end_iso]
        pay_clause = ""
        if param:
            pay_clause = " AND start_param = ?"
            pay_params.append(param)
        cursor.execute(
            f"""
            SELECT date(last_activity) AS day, COUNT(*)
            FROM users
            WHERE status IN ('Нажал оплатить техника','Нажал оплатить одежда')
              AND date(last_activity) BETWEEN date(?) AND date(?)
              {pay_clause}
            GROUP BY day
            ORDER BY day
            """,
            tuple(pay_params)
        )
        pay_rows = {row[0]: row[1] for row in cursor.fetchall()}

        # Paid per day
        paid_params: List = [start_iso, end_iso]
        paid_clause = ""
        if param:
            paid_clause = " AND start_param = ?"
            paid_params.append(param)
        cursor.execute(
            f"""
            SELECT date(last_activity) AS day, COUNT(*)
            FROM users
            WHERE status IN ('Оплатил одежду','Оплатил технику')
              AND date(last_activity) BETWEEN date(?) AND date(?)
              {paid_clause}
            GROUP BY day
            ORDER BY day
            """,
            tuple(paid_params)
        )
        paid_rows = {row[0]: row[1] for row in cursor.fetchall()}

        # Build complete range
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start_iso, "%Y-%m-%d")
        end_dt = datetime.strptime(end_iso, "%Y-%m-%d")
        days: List[Tuple[str, int, int, int]] = []
        current = start_dt
        while current <= end_dt:
            day_str = current.strftime("%Y-%m-%d")
            days.append((day_str, join_rows.get(day_str, 0), pay_rows.get(day_str, 0), paid_rows.get(day_str, 0)))
            current += timedelta(days=1)

        return days


def get_param_distribution(start_date: Optional[str] = None, end_date: Optional[str] = None, param: Optional[str] = None) -> List[Tuple[str, int]]:
    """Return (param_name, count) of users joined in date range grouped by start_param.
    Only includes users who actually joined via a param in the range.
    Optionally filter by specific start_param.
    """
    start_iso, end_iso = _normalize_date_range(start_date, end_date)

    with get_connection() as conn:
        cursor = conn.cursor()
        params: List = [start_iso, end_iso]
        param_clause = ""
        if param:
            param_clause = " AND start_param = ?"
            params.append(param)
        
        cursor.execute(
            f"""
            SELECT start_param, COUNT(*) as cnt
            FROM users
            WHERE start_param IS NOT NULL
              AND date(join_date) BETWEEN date(?) AND date(?)
              {param_clause}
            GROUP BY start_param
            ORDER BY cnt DESC
            """,
            tuple(params)
        )
        return [(row[0], row[1]) for row in cursor.fetchall()]


def get_status_distribution(start_date: Optional[str] = None, end_date: Optional[str] = None, param: Optional[str] = None) -> List[Tuple[str, int]]:
    """Return (status, count) for users filtered by last_activity window and optional start_param.
    Useful to show funnel stages distribution (Этап (с ID)).
    """
    start_iso, end_iso = _normalize_date_range(start_date, end_date)

    with get_connection() as conn:
        cursor = conn.cursor()
        params: List = [start_iso, end_iso]
        param_clause = ""
        if param:
            param_clause = " AND start_param = ?"
            params.append(param)

        cursor.execute(
            f"""
            SELECT status, COUNT(*) as cnt
            FROM users
            WHERE status IS NOT NULL
              AND date(last_activity) BETWEEN date(?) AND date(?)
              {param_clause}
            GROUP BY status
            ORDER BY cnt DESC
            """,
            tuple(params)
        )
        return [(row[0], row[1]) for row in cursor.fetchall()]
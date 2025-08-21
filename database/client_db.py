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
                INSERT INTO users (user_id, user_name, join_date, last_activity, status, start_param)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, current_time, current_time, 'active', start_param))
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
            SELECT user_id, user_name, join_date, last_activity, start_param, status
            FROM users 
            ORDER BY last_activity DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        users = cursor.fetchall()
        return users, total_users, total_pages, page, per_page
















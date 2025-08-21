import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime

os.makedirs('data', exist_ok=True)

@contextmanager
def get_connection():
    conn = sqlite3.connect('data/data.db')
    try:
        yield conn
    finally:
        conn.close()

def create_start_params_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS start_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                param_name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()

def add_start_param(param_name, description=None):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM start_params WHERE param_name = ?', (param_name,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE start_params 
                    SET description = ?, updated_at = ?
                    WHERE param_name = ?
                ''', (description, current_time, param_name))
                print(f"✅ Обновлен стартовый параметр: {param_name}")
            else:
                cursor.execute('''
                    INSERT INTO start_params (param_name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (param_name, description, current_time, current_time))
                print(f"✅ Добавлен новый стартовый параметр: {param_name}")
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при добавлении стартового параметра: {e}")
        return False

def get_start_param_config(param_name):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT param_name, description
            FROM start_params 
            WHERE param_name = ?
        ''', (param_name,))
        
        result = cursor.fetchone()
        
        if result:
            return {
                'param_name': result[0],
                'description': result[1]
            }
        return None


def delete_start_param(param_name):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM start_params WHERE param_name = ?', (param_name,))
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✅ Видалено стартовий параметр: {param_name}")
                return True
            else:
                print(f"❌ Стартовий параметр не знайдено: {param_name}")
                return False
                
    except Exception as e:
        print(f"❌ Помилка при видаленні стартового параметра: {e}")
        return False

def get_start_params_stats():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sp.param_name, COALESCE(COUNT(u.user_id), 0) as user_count
            FROM start_params sp
            LEFT JOIN users u ON sp.param_name = u.start_param
            GROUP BY sp.param_name
            ORDER BY user_count DESC
        ''')
        
        stats = cursor.fetchall()
        return stats

def get_total_start_params():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM start_params')
        count = cursor.fetchone()[0]
        
        return count

def get_users_with_start_params():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE start_param IS NOT NULL')
        count = cursor.fetchone()[0]
        
        return count


import sqlite3
import json
import os
from typing import Dict, Any
from contextlib import contextmanager
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import pytz
from werkzeug.security import check_password_hash, generate_password_hash


os.makedirs('data', exist_ok=True)

@contextmanager
def get_connection():
    conn = sqlite3.connect('data/data.db')
    try:
        yield conn
    finally:
        conn.close()


def create_settings_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        
        default_settings = {
            'start_message': 'Привет! Добро пожаловать в наш магазин!',
            'start_media_type': 'none',
            'start_media_url': '',
            'start_inline_buttons': '[]',
            'start_inline_buttons_position': 'below',
            'start_answers_button_text': '💡 Ответы',
            'start_our_chat_button_text': '🎓 Приватный урок',
            'start_shop_button_text': '💰 Тарифы',
            'our_chat_message': 'Присоединяйтесь к нашему чату!',
            'our_chat_media_type': 'none',
            'our_chat_media_url': '',
            'our_chat_subscription_button_text': '📢 Подписка',
            'our_chat_subscription_channel_url': 'https://t.me/your_channel',
            'our_chat_check_subscription_button_text': '✅ Проверить подписку',
            'shop_message': 'Добро пожаловать в наш магазин! Выберите категорию товаров.',
            'shop_media_type': 'none',
            'shop_media_url': '',
            'channel_join_message': 'Добро пожаловать в наш канал! Рады видеть вас!',
            'channel_join_media_type': 'none',
            'channel_join_media_url': '',
            'channel_leave_message': 'Жаль, что вы покинули наш канал! Надеемся увидеть вас снова!',
            'channel_leave_media_type': 'none',
            'channel_leave_media_url': '',
            'channel_leave_inline_buttons': '[]',
            'channel_leave_leave_button_text': 'Уйти',
            'channel_leave_leave_message': 'Вы уверены, что хотите уйти?',
            'channel_leave_leave_media_type': 'none',
            'channel_leave_leave_media_url': '',
            'channel_leave_leave_inline_buttons': '[]',
            'channel_leave_return_button_text': 'Возвращаюсь',
            'channel_leave_return_url': 'https://t.me/your_channel',
            'captcha_message': 'Я не робот',
            'captcha_media_type': 'none',
            'captcha_media_url': '',
            'captcha_button_text': 'Я не робот',
            'answers_message': 'Ответы на часто задаваемые вопросы',
            'answers_media_type': 'none',
            'answers_media_url': '',
            'answers_inline_buttons': '[]',
            'private_lesson_message': 'Добро пожаловать на приватный урок!',
            'private_lesson_media_type': 'none',
            'private_lesson_media_url': '',
            'private_lesson_inline_buttons': '[]',
            'tariffs_message': 'Наши тарифы и цены',
            'tariffs_media_type': 'none',
            'tariffs_media_url': '',
            'tariffs_inline_buttons': '[]'
        }
        
        for key, value in default_settings.items():
            cursor.execute('''
                INSERT OR IGNORE INTO bot_settings (setting_key, setting_value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
    
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS start_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_param TEXT UNIQUE NOT NULL,
                message_text TEXT NOT NULL,
                media_type TEXT DEFAULT 'none',
                media_url TEXT,
                inline_buttons TEXT DEFAULT '[]',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_invite_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invite_link TEXT UNIQUE NOT NULL,
                channel_name TEXT NOT NULL,
                message_text TEXT NOT NULL,
                media_type TEXT DEFAULT 'none',
                media_url TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        try:
            cursor.execute('SELECT captcha_message FROM channel_invite_links LIMIT 1')
        except:
            cursor.execute('ALTER TABLE channel_invite_links ADD COLUMN captcha_message TEXT DEFAULT "Я не робот"')
            
        try:
            cursor.execute('SELECT captcha_media_type FROM channel_invite_links LIMIT 1')
        except:
            cursor.execute('ALTER TABLE channel_invite_links ADD COLUMN captcha_media_type TEXT DEFAULT "none"')
            
        try:
            cursor.execute('SELECT captcha_media_url FROM channel_invite_links LIMIT 1')
        except:
            cursor.execute('ALTER TABLE channel_invite_links ADD COLUMN captcha_media_url TEXT DEFAULT ""')
            
        try:
            cursor.execute('SELECT captcha_button_text FROM channel_invite_links LIMIT 1')
        except:
            cursor.execute('ALTER TABLE channel_invite_links ADD COLUMN captcha_button_text TEXT DEFAULT "Я не робот"')
        
        conn.commit()
        


def update_setting(key: str, value: Any) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if key == 'start_inline_buttons':
            setting_value = value
        else:
            setting_value = str(value)
        
        cursor.execute('''
            INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, setting_value))
        
        conn.commit()


def get_all_settings() -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT setting_key, setting_value FROM bot_settings')
        results = cursor.fetchall()
        
        settings = {}
        for key, value in results:
            if key == 'start_inline_buttons' and value:
                try:
                    import json
                    parsed_value = json.loads(value)
                    settings[key] = parsed_value
                except (json.JSONDecodeError, TypeError):
                    settings[key] = []
            else:
                settings[key] = value
        
        return settings

def get_start_message_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    inline_buttons = []
    try:
        if settings.get("start_inline_buttons"):
            if isinstance(settings.get("start_inline_buttons"), str):
                inline_buttons = json.loads(settings.get("start_inline_buttons"))
            else:
                inline_buttons = settings.get("start_inline_buttons")
            
            if not isinstance(inline_buttons, list):
                inline_buttons = []
            
            filtered_buttons = []
            for button in inline_buttons:
                if isinstance(button, dict) and 'text' in button and 'url' in button:
                    text = button['text'].strip() if button['text'] else ""
                    url = button['url'].strip() if button['url'] else ""
                    
                    if text and url:
                        filtered_buttons.append({
                            'text': text,
                            'url': url
                        })
            
            inline_buttons = filtered_buttons
            
    except (json.JSONDecodeError, TypeError):
        inline_buttons = []
    
    return {
        "message": settings.get("start_message", "Привет! Добро пожаловать в наш магазин!"),
        "media_type": settings.get("start_media_type", "none"),
        "media_url": settings.get("start_media_url", ""),
        "inline_buttons": inline_buttons,
        "inline_buttons_position": settings.get("start_inline_buttons_position", "below"),
        "answers_button_text": settings.get("start_answers_button_text", "💡 Ответы"),
        "our_chat_button_text": settings.get("start_our_chat_button_text", "🎓 Приватный урок"),
        "shop_button_text": settings.get("start_shop_button_text", "💰 Тарифы")
    }


def get_channel_leave_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    inline_buttons = []
    try:
        if settings.get("channel_leave_inline_buttons"):
            if isinstance(settings.get("channel_leave_inline_buttons"), str):
                inline_buttons = json.loads(settings.get("channel_leave_inline_buttons"))
            else:
                inline_buttons = settings.get("channel_leave_inline_buttons")
            
            if not isinstance(inline_buttons, list):
                inline_buttons = []
            
            filtered_buttons = []
            for button in inline_buttons:
                if isinstance(button, dict) and 'text' in button and 'url' in button:
                    text = button['text'].strip() if button['text'] else ""
                    url = button['url'].strip() if button['url'] else ""
                    
                    if text and url:
                        filtered_buttons.append({
                            'text': text,
                            'url': url
                        })
            
            inline_buttons = filtered_buttons
            
    except (json.JSONDecodeError, TypeError):
        inline_buttons = []
    
    leave_inline_buttons = []
    try:
        if settings.get("channel_leave_leave_inline_buttons"):
            if isinstance(settings.get("channel_leave_leave_inline_buttons"), str):
                leave_inline_buttons = json.loads(settings.get("channel_leave_leave_inline_buttons"))
            else:
                leave_inline_buttons = settings.get("channel_leave_leave_inline_buttons")
            
            if not isinstance(leave_inline_buttons, list):
                leave_inline_buttons = []
            
            filtered_leave_buttons = []
            for button in leave_inline_buttons:
                if isinstance(button, dict) and 'text' in button and 'url' in button:
                    text = button['text'].strip() if button['text'] else ""
                    url = button['url'].strip() if button['url'] else ""
                    
                    if text and url:
                        filtered_leave_buttons.append({
                            'text': text,
                            'url': url
                        })
            
            leave_inline_buttons = filtered_leave_buttons
            
    except (json.JSONDecodeError, TypeError):
        leave_inline_buttons = []
    
    return {
        "message": settings.get("channel_leave_message", "Жаль, что вы покинули наш канал! Надеемся увидеть вас снова!"),
        "media_type": settings.get("channel_leave_media_type", "none"),
        "media_url": settings.get("channel_leave_media_url", ""),
        "inline_buttons": inline_buttons,
        "leave_button_text": settings.get("channel_leave_leave_button_text", "Уйти"),
        "leave_message": settings.get("channel_leave_leave_message", "Вы уверены, что хотите уйти?"),
        "leave_media_type": settings.get("channel_leave_leave_media_type", "none"),
        "leave_media_url": settings.get("channel_leave_leave_media_url", ""),
        "leave_inline_buttons": leave_inline_buttons,
        "return_button_text": settings.get("channel_leave_return_button_text", "Возвращаюсь"),
        "return_url": settings.get("channel_leave_return_url", "https://t.me/your_channel")
    }

def save_start_message_config(config: Dict[str, Any]) -> None:
    update_setting("start_message", config.get("message", ""))
    update_setting("start_media_type", config.get("media_type", "none"))
    update_setting("start_media_url", config.get("media_url", ""))
    update_setting("start_answers_button_text", config.get("answers_button_text", "💡 Ответы"))
    update_setting("start_our_chat_button_text", config.get("our_chat_button_text", "🎓 Приватный урок"))
    update_setting("start_shop_button_text", config.get("shop_button_text", "💰 Тарифы"))
    update_setting("start_inline_buttons_position", config.get("inline_buttons_position", "below"))
    
    inline_buttons = config.get("inline_buttons", [])
    if not isinstance(inline_buttons, list):
        inline_buttons = []
    
    valid_buttons = []
    for button in inline_buttons:
        if isinstance(button, dict) and 'text' in button and 'url' in button:
            text = button['text'].strip() if button['text'] else ""
            url = button['url'].strip() if button['url'] else ""
            
            if text and url:
                valid_buttons.append({
                    'text': text,
                    'url': url
                })
    
    update_setting("start_inline_buttons", json.dumps(valid_buttons))

def save_our_chat_config(config: Dict[str, Any]) -> None:
    update_setting("our_chat_message", config.get("message", ""))
    update_setting("our_chat_media_type", config.get("media_type", "none"))
    update_setting("our_chat_media_url", config.get("media_url", ""))
    update_setting("our_chat_subscription_button_text", config.get("subscription_button_text", "📢 Подписка"))
    update_setting("our_chat_subscription_channel_url", config.get("subscription_channel_url", "https://t.me/your_channel"))
    update_setting("our_chat_check_subscription_button_text", config.get("check_subscription_button_text", "✅ Проверить подписку"))


def save_channel_join_config(config: Dict[str, Any]) -> None:
    update_setting("channel_join_message", config.get("message", ""))
    update_setting("channel_join_media_type", config.get("media_type", "none"))
    update_setting("channel_join_media_url", config.get("media_url", ""))

def save_channel_leave_config(config: Dict[str, Any]) -> None:
    update_setting("channel_leave_message", config.get("message", ""))
    update_setting("channel_leave_media_type", config.get("media_type", "none"))
    update_setting("channel_leave_media_url", config.get("media_url", ""))
    
    inline_buttons = config.get("inline_buttons", [])
    if not isinstance(inline_buttons, list):
        inline_buttons = []
    
    valid_buttons = []
    for button in inline_buttons:
        if isinstance(button, dict) and 'text' in button and 'url' in button:
            text = button['text'].strip() if button['text'] else ""
            url = button['url'].strip() if button['url'] else ""
            
            if text and url:
                valid_buttons.append({
                    'text': text,
                    'url': url
                })
    
    update_setting("channel_leave_inline_buttons", json.dumps(valid_buttons))
    
    update_setting("channel_leave_leave_button_text", config.get("leave_button_text", "Уйти"))
    update_setting("channel_leave_leave_message", config.get("leave_message", ""))
    update_setting("channel_leave_leave_media_type", config.get("leave_media_type", "none"))
    update_setting("channel_leave_leave_media_url", config.get("leave_media_url", ""))
    
    leave_inline_buttons = config.get("leave_inline_buttons", [])
    if not isinstance(leave_inline_buttons, list):
        leave_inline_buttons = []
    
    valid_leave_buttons = []
    for button in leave_inline_buttons:
        if isinstance(button, dict) and 'text' in button and 'url' in button:
            text = button['text'].strip() if button['text'] else ""
            url = button['url'].strip() if button['url'] else ""
            
            if text and url:
                valid_leave_buttons.append({
                    'text': text,
                    'url': url
                })
    
    update_setting("channel_leave_leave_inline_buttons", json.dumps(valid_leave_buttons))
    
    update_setting("channel_leave_return_button_text", config.get("return_button_text", "Возвращаюсь"))
    update_setting("channel_leave_return_url", config.get("return_url", ""))


def get_channel_invite_links() -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, invite_link, channel_name, message_text, media_type, media_url, is_active
            FROM channel_invite_links 
            ORDER BY created_at DESC
        ''')
        
        links = cursor.fetchall()
        return links

def add_channel_invite_link(invite_link: str, channel_name: str, message_text: str, media_type: str = "none", media_url: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO channel_invite_links (invite_link, channel_name, message_text, media_type, media_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (invite_link, channel_name, message_text, media_type, media_url))
        
        link_id = cursor.lastrowid
        conn.commit()
        return link_id

def update_channel_invite_link(link_id: int, invite_link: str, channel_name: str, message_text: str, media_type: str, media_url: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE channel_invite_links 
            SET invite_link = ?, channel_name = ?, message_text = ?, media_type = ?, media_url = ?
            WHERE id = ?
        ''', (invite_link, channel_name, message_text, media_type, media_url, link_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        return success

def delete_channel_invite_link(link_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM channel_invite_links WHERE id = ?', (link_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        return success


def create_mailings_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mailings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                message_text TEXT NOT NULL,
                media_type TEXT DEFAULT 'none',
                media_url TEXT,
                inline_buttons TEXT,
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                users_count INTEGER DEFAULT 0,
                scheduled_at TIMESTAMP,
                is_scheduled INTEGER DEFAULT 0,
                schedule_repeat TEXT DEFAULT 'once',
                schedule_days TEXT,
                status TEXT DEFAULT 'draft',
                is_recurring INTEGER DEFAULT 0,
                recurring_days TEXT,
                recurring_time TEXT,
                next_scheduled_at TIMESTAMP
            )
        ''')
        
        try:
            cursor.execute('SELECT scheduled_at FROM mailings LIMIT 1')
        except:
            
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN scheduled_at TIMESTAMP')
            except Exception as e:
                print(f"❌ Помилка додавання scheduled_at: {e}")
                
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN is_scheduled INTEGER DEFAULT 0')
            except Exception as e:
                print(f"❌ Помилка додавання is_scheduled: {e}")
                
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN schedule_repeat TEXT DEFAULT "once"')
            except Exception as e:
                print(f"❌ Помилка додавання schedule_repeat: {e}")
                
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN schedule_days TEXT')
            except Exception as e:
                print(f"❌ Помилка додавання schedule_days: {e}")
                
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN status TEXT DEFAULT "draft"')
            except Exception as e:
                print(f"❌ Помилка додавання status: {e}")
        
        try:
            cursor.execute('SELECT is_recurring FROM mailings LIMIT 1')
        except:
            
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN is_recurring INTEGER DEFAULT 0')
            except Exception as e:
                print(f"❌ Помилка додавання is_recurring: {e}")
                
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN recurring_days TEXT')
            except Exception as e:
                print(f"❌ Помилка додавання recurring_days: {e}")
                
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN recurring_time TEXT')
            except Exception as e:
                print(f"❌ Помилка додавання recurring_time: {e}")
                
            try:
                cursor.execute('ALTER TABLE mailings ADD COLUMN next_scheduled_at TIMESTAMP')
            except Exception as e:
                print(f"❌ Помилка додавання next_scheduled_at: {e}")
        
            try:
                cursor.execute('PRAGMA table_info(mailings)')
                columns = cursor.fetchall()
            except:
                pass
        
        conn.commit()


def add_mailing(name: str, message_text: str, media_type: str = "none", 
                media_url: str = None, inline_buttons: str = None, 
                user_filter: str = "all", user_status: str = None, 
                start_param_filter: str = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Додаємо нові поля до таблиці mailings, якщо їх немає
        try:
            cursor.execute('ALTER TABLE mailings ADD COLUMN user_filter TEXT DEFAULT "all"')
        except:
            pass  # Колонка вже існує
            
        try:
            cursor.execute('ALTER TABLE mailings ADD COLUMN user_status TEXT')
        except:
            pass  # Колонка вже існує
            
        try:
            cursor.execute('ALTER TABLE mailings ADD COLUMN start_param_filter TEXT')
        except:
            pass  # Колонка вже існує
        
        try:
            cursor.execute('''
                INSERT INTO mailings (
                    name, message_text, media_type, media_url, inline_buttons, 
                    is_active, is_scheduled, status, is_recurring, 
                    recurring_days, recurring_time, next_scheduled_at,
                    user_filter, user_status, start_param_filter
                )
                VALUES (?, ?, ?, ?, ?, 0, 0, 'draft', 0, NULL, NULL, NULL, ?, ?, ?)
            ''', (name, message_text, media_type, media_url, inline_buttons, 
                  user_filter, user_status, start_param_filter))
        except Exception as e:
            cursor.execute('''
            INSERT INTO mailings (name, message_text, media_type, media_url, inline_buttons, status)
            VALUES (?, ?, ?, ?, ?, 'draft')
        ''', (name, message_text, media_type, media_url, inline_buttons))
        
        conn.commit()
        mailing_id = cursor.lastrowid
        
        cursor.execute('SELECT inline_buttons FROM mailings WHERE id = ?', (mailing_id,))
        saved_buttons = cursor.fetchone()[0]
        
        return mailing_id


def get_all_mailings() -> List[Tuple]:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT m.id, m.name, m.message_text, m.media_type, m.media_url, m.inline_buttons, 
                       m.is_active, m.created_at, m.sent_at, m.users_count, m.scheduled_at, 
                       m.is_scheduled, m.status, 
                       CASE WHEN r.mailing_id IS NOT NULL THEN 1 ELSE 0 END as is_recurring,
                       r.recurring_days, r.recurring_time, r.next_scheduled_at,
                       m.user_filter, m.user_status, m.start_param_filter
                FROM mailings m
                LEFT JOIN recurring_mailings r ON m.id = r.mailing_id AND r.is_active = 1
                ORDER BY m.created_at DESC
            ''')
            results = cursor.fetchall()
            return results
        except Exception as e:
            try:
                cursor.execute('''
                SELECT id, name, message_text, media_type, media_url, inline_buttons, 
                           is_active, created_at, sent_at, users_count, scheduled_at, 
                           is_scheduled, status, 0 as is_recurring, NULL as recurring_days, 
                           NULL as recurring_time, NULL as next_scheduled_at,
                           user_filter, user_status, start_param_filter
                FROM mailings ORDER BY created_at DESC
                ''')
                results = cursor.fetchall()
                return results
            except Exception as e2:
                return []


def get_mailing_by_id(mailing_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT m.id, m.name, m.message_text, m.media_type, m.media_url, m.inline_buttons, 
                       m.is_active, m.created_at, m.sent_at, m.users_count, m.scheduled_at, 
                       m.is_scheduled, m.status, 
                       CASE WHEN r.mailing_id IS NOT NULL THEN 1 ELSE 0 END as is_recurring,
                       r.recurring_days, r.recurring_time, r.next_scheduled_at,
                       m.user_filter, m.user_status, m.start_param_filter
                FROM mailings m
                LEFT JOIN recurring_mailings r ON m.id = r.mailing_id AND r.is_active = 1
                WHERE m.id = ?
            ''', (mailing_id,))
            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "message_text": result[2],
                    "media_type": result[3],
                    "media_url": result[4],
                    "inline_buttons": result[5],
                    "is_active": result[6],
                    "created_at": result[7],
                    "sent_at": result[8],
                    "users_count": result[9],
                    "scheduled_at": result[10],
                    "is_scheduled": result[11],
                    "status": result[12],
                    "is_recurring": result[13],
                    "recurring_days": result[14],
                    "recurring_time": result[15],
                    "next_scheduled_at": result[16],
                    "user_filter": result[17] if len(result) > 17 else "all",
                    "user_status": result[18] if len(result) > 18 else None,
                    "start_param_filter": result[19] if len(result) > 19 else None
                }
        except Exception as e:
            print(f"Помилка при отриманні розсилки з JOIN: {e}")
            # Якщо JOIN не працює, використовуємо простий запит
            cursor.execute('''
                SELECT id, name, message_text, media_type, media_url, inline_buttons, 
                       is_active, created_at, sent_at, users_count, scheduled_at, 
                       is_scheduled, status
                FROM mailings WHERE id = ?
            ''', (mailing_id,))
            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "message_text": result[2],
                    "media_type": result[3],
                    "media_url": result[4],
                    "inline_buttons": result[5],
                    "is_active": result[6],
                    "created_at": result[7],
                    "sent_at": result[8],
                    "users_count": result[9],
                    "scheduled_at": result[10],
                    "is_scheduled": result[11],
                    "status": result[12],
                    "is_recurring": 0,
                    "recurring_days": None,
                    "recurring_time": None,
                    "next_scheduled_at": None
                }
        
        return None



def get_scheduled_mailings():
    """Отримує всі заплановані розсилки, які готові до відправки"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM mailings 
            WHERE is_scheduled = 1 AND status = 'scheduled' AND scheduled_at IS NOT NULL
            ORDER BY scheduled_at ASC
        ''')
        return cursor.fetchall()


def schedule_mailing(mailing_id: int, scheduled_datetime: str) -> bool:
    """Планує розсилку на вказаний час"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE mailings 
                SET is_scheduled = 1, scheduled_at = ?, status = 'scheduled'
                WHERE id = ?
            ''', (scheduled_datetime, mailing_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Помилка при плануванні розсилки: {e}")
            return False


def update_mailing_status(mailing_id: int, status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE mailings 
            SET status = ?
            WHERE id = ?
        ''', (status, mailing_id))
        conn.commit()
        return cursor.rowcount > 0


def cancel_scheduled_mailing(mailing_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE mailings 
            SET is_scheduled = 0, scheduled_at = NULL, status = 'draft'
            WHERE id = ?
        ''', (mailing_id,))
        conn.commit()
        return cursor.rowcount > 0


def toggle_recurring_mailing(mailing_id: int, is_recurring: bool, recurring_days: str = None, recurring_time: str = None) -> bool:

    if is_recurring:
        return add_recurring_mailing(mailing_id, recurring_days, recurring_time)
    else:
        return remove_recurring_mailing(mailing_id)


def resend_mailing(mailing_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_recurring, recurring_days, recurring_time FROM mailings WHERE id = ?', (mailing_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            cursor.execute('''
                UPDATE mailings 
                SET sent_at = CURRENT_TIMESTAMP, users_count = 0, 
                    is_scheduled = 1, status = 'sent'
                WHERE id = ?
            ''', (mailing_id,))
        else:
            cursor.execute('''
                UPDATE mailings 
                SET sent_at = CURRENT_TIMESTAMP, users_count = 0
                WHERE id = ?
            ''', (mailing_id,))
        
        conn.commit()
        return cursor.rowcount > 0


def schedule_next_recurring(mailing_id: int) -> bool:

    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT recurring_days, recurring_time, next_scheduled_at 
            FROM recurring_mailings WHERE mailing_id = ? AND is_active = 1
        ''', (mailing_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"🔍 DEBUG: Не знайдено повторювану розсилку з ID {mailing_id}")
            return False
        
        recurring_days = result[0]
        recurring_time = result[1]
        current_next = result[2]
        
        if not recurring_days or not recurring_time:
            print(f"🔍 DEBUG: Відсутні дані про дні або час для розсилки {mailing_id}")
            return False
        
        from datetime import datetime, timedelta
        import pytz
        
        kyiv_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(kyiv_tz)
        
        try:
            hour, minute = map(int, recurring_time.split(':'))
        except Exception as e:
            print(f"🔍 DEBUG: Помилка парсингу часу '{recurring_time}': {e}")
            return False
        
        try:
            days = [int(d) for d in recurring_days.split(',')]
        except Exception as e:
            return False
        
        next_dates = []
        for target_day in days:
            for day_offset in range(1, 8):
                check_date = now + timedelta(days=day_offset)
                if check_date.weekday() == target_day:
                    next_date = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    next_dates.append(next_date)
                    break
        
        if next_dates:
            next_scheduled_at = min(next_dates)
            
            cursor.execute('''
                UPDATE recurring_mailings 
                SET next_scheduled_at = ?
                WHERE mailing_id = ?
            ''', (next_scheduled_at.isoformat(), mailing_id))
            
            cursor.execute('''
                UPDATE mailings 
                SET next_scheduled_at = ?, is_scheduled = 1, status = 'scheduled'
                WHERE id = ?
            ''', (next_scheduled_at.isoformat(), mailing_id))
            
            conn.commit()
            return True
        
        return False



def save_start_link_config(start_param, message_text, media_type, media_url, inline_buttons):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        import json
        buttons_json = json.dumps(inline_buttons)
        
        cursor.execute('''
            INSERT OR REPLACE INTO start_links 
            (start_param, message_text, media_type, media_url, inline_buttons, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (start_param, message_text, media_type, media_url, buttons_json))
        
        conn.commit()

def get_all_start_links():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, start_param, message_text, media_type, media_url, inline_buttons, is_active, created_at
            FROM start_links 
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
    
    links = []
    for row in rows:
        import json
        links.append({
            'id': row[0],
            'start_param': row[1],
            'message_text': row[2],
            'media_type': row[3],
            'media_url': row[4],
            'inline_buttons': json.loads(row[5]) if row[5] else [],
            'is_active': bool(row[6]),
            'created_at': row[7]
        })
    
    return links

def delete_start_link(link_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM start_links WHERE id = ?', (link_id,))
        
        conn.commit()

def toggle_start_link_status(link_id, is_active):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE start_links 
            SET is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (is_active, link_id))
        
        conn.commit()

def create_subscription_messages_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscription_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL,
                media_type TEXT DEFAULT 'none',
                media_url TEXT,
                inline_buttons TEXT DEFAULT '[]',
                inline_buttons_position TEXT DEFAULT 'below',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


def create_welcome_without_subscription_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS welcome_without_subscription (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL,
                media_type TEXT DEFAULT 'none',
                media_url TEXT,
                channel_url TEXT,
                channel_id TEXT,
                channel_button_text TEXT DEFAULT '📢 Подписаться на канал',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Перевіряємо чи існує колонка channel_button_text
        cursor.execute("PRAGMA table_info(welcome_without_subscription)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'channel_button_text' not in columns:
            cursor.execute('ALTER TABLE welcome_without_subscription ADD COLUMN channel_button_text TEXT DEFAULT "📢 Подписаться на канал"')
            # Оновлюємо існуючі записи, які мають NULL значення
            cursor.execute('UPDATE welcome_without_subscription SET channel_button_text = "📢 Подписаться на канал" WHERE channel_button_text IS NULL')
        
        # Додаємо запис за замовчуванням, якщо таблиця порожня
        cursor.execute('SELECT COUNT(*) FROM welcome_without_subscription')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO welcome_without_subscription 
                (message_text, media_type, media_url, channel_url, channel_id, channel_button_text, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'Добро пожаловать! Для доступа к боту необходимо подписаться на наш канал.',
                'none', '', 'https://t.me/your_channel', '@your_channel', '📢 Подписаться на канал', 1
            ))
        
        conn.commit()


def get_subscription_message() -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message_text, media_type, media_url, inline_buttons, inline_buttons_position, 
                   back_button_text, main_menu_button_text, show_back_button, show_main_menu_button,
                   is_active, created_at, updated_at
            FROM subscription_messages 
            WHERE is_active = 1 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        if result:
            return {
                "id": result[0],
                "message_text": result[1],
                "media_type": result[2],
                "media_url": result[3],
                "inline_buttons": json.loads(result[4]) if result[4] else [],
                "inline_buttons_position": result[5],
                "back_button_text": result[6],
                "main_menu_button_text": result[7],
                "show_back_button": bool(result[8]),
                "show_main_menu_button": bool(result[9]),
                "is_active": result[10],
                "created_at": result[11],
                "updated_at": result[12]
            }
        return None


def save_subscription_message(message_text: str, media_type: str = "none", 
                           media_url: str = None, button_text: str = None, 
                           button_url: str = None) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('UPDATE subscription_messages SET is_active = 0')
        
        # Convert button parameters to inline_buttons format
        inline_buttons = []
        if button_text and button_url:
            inline_buttons = [{"text": button_text, "url": button_url}]
        
        cursor.execute('''
            INSERT INTO subscription_messages 
            (message_text, media_type, media_url, inline_buttons, inline_buttons_position, 
             back_button_text, main_menu_button_text, show_back_button, show_main_menu_button, is_active)
            VALUES (?, ?, ?, ?, 'below', '⬅️ Вернуться назад', '🏠 Главное меню', 1, 1, 1)
        ''', (message_text, media_type, media_url, json.dumps(inline_buttons)))
        
        conn.commit()
        return cursor.rowcount > 0


def update_subscription_message(message_id: int, message_text: str, media_type: str = "none",
                              media_url: str = None, button_text: str = None, 
                              button_url: str = None) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Convert button parameters to inline_buttons format
        inline_buttons = []
        if button_text and button_url:
            inline_buttons = [{"text": button_text, "url": button_url}]
        
        cursor.execute('''
            UPDATE subscription_messages 
            SET message_text = ?, media_type = ?, media_url = ?, inline_buttons = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (message_text, media_type, media_url, json.dumps(inline_buttons), message_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_subscription_message(message_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subscription_messages WHERE id = ?', (message_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_all_subscription_messages() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message_text, media_type, media_url, inline_buttons, inline_buttons_position,
                   back_button_text, main_menu_button_text, show_back_button, show_main_menu_button,
                   is_active, created_at, updated_at
            FROM subscription_messages 
            ORDER BY created_at DESC
        ''')
        results = cursor.fetchall()
        messages = []
        for row in results:
            messages.append({
                "id": row[0],
                "message_text": row[1],
                "media_type": row[2],
                "media_url": row[3],
                "inline_buttons": json.loads(row[4]) if row[4] else [],
                "inline_buttons_position": row[5],
                "back_button_text": row[6],
                "main_menu_button_text": row[7],
                "show_back_button": bool(row[8]),
                "show_main_menu_button": bool(row[9]),
                "is_active": row[10],
                "created_at": row[11],
                "updated_at": row[12]
            })
        return messages


def create_recurring_mailings_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_mailings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mailing_id INTEGER NOT NULL,
                recurring_days TEXT NOT NULL,
                recurring_time TEXT NOT NULL,
                next_scheduled_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mailing_id) REFERENCES mailings (id) ON DELETE CASCADE
            )
        ''')
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_mailing_id ON recurring_mailings (mailing_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_next_scheduled ON recurring_mailings (next_scheduled_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recurring_active ON recurring_mailings (is_active)')
        except Exception as e:
            print(f"❌ Помилка створення індексів: {e}")
        
        conn.commit()


def add_recurring_mailing(mailing_id: int, recurring_days: str, recurring_time: str) -> bool:
    kyiv_tz = pytz.timezone('Europe/Kiev')
    now = datetime.now(kyiv_tz)
    
    try:
        hour, minute = map(int, recurring_time.split(':'))
    except Exception as e:
        return False
    
    try:
        days = [int(d) for d in recurring_days.split(',')]
    except Exception as e:
        return False
    
    next_dates = []
    for target_day in days:
        for day_offset in range(0, 8):
            check_date = now + timedelta(days=day_offset)
            if check_date.weekday() == target_day:
                if day_offset == 0 and check_date.hour > hour:
                    next_week_date = check_date + timedelta(days=7)
                    next_date = next_week_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    next_date = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                next_dates.append(next_date)
                break
    
    if not next_dates:
        return False
    
    next_scheduled_at = min(next_dates)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM recurring_mailings WHERE mailing_id = ?', (mailing_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE recurring_mailings 
                SET recurring_days = ?, recurring_time = ?, next_scheduled_at = ?, is_active = 1
                WHERE mailing_id = ?
            ''', (recurring_days, recurring_time, next_scheduled_at.isoformat(), mailing_id))
        else:
            cursor.execute('''
                INSERT INTO recurring_mailings (mailing_id, recurring_days, recurring_time, next_scheduled_at)
                VALUES (?, ?, ?, ?)
            ''', (mailing_id, recurring_days, recurring_time, next_scheduled_at.isoformat()))
        
        cursor.execute('''
            UPDATE mailings 
            SET is_recurring = 1, is_scheduled = 1, status = 'scheduled', next_scheduled_at = ?
            WHERE id = ?
        ''', (next_scheduled_at.isoformat(), mailing_id))
        
        conn.commit()
        return True


def remove_recurring_mailing(mailing_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM recurring_mailings WHERE mailing_id = ?', (mailing_id,))
        
        cursor.execute('''
            UPDATE mailings 
            SET is_recurring = 0, is_scheduled = 0, status = 'sent'
            WHERE id = ?
        ''', (mailing_id,))
        
        conn.commit()
        return True




def schedule_next_recurring(mailing_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT recurring_days, recurring_time, next_scheduled_at 
            FROM recurring_mailings WHERE mailing_id = ? AND is_active = 1
        ''', (mailing_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        recurring_days = result[0]
        recurring_time = result[1]
        current_next = result[2]
        
        if not recurring_days or not recurring_time:
            return False
        
        kyiv_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(kyiv_tz)
        
        try:
            hour, minute = map(int, recurring_time.split(':'))
        except Exception as e:
            return False

        try:
            days = [int(d) for d in recurring_days.split(',')]
        except Exception as e:
            return False
        
        next_dates = []
        for target_day in days:
            for day_offset in range(1, 8):
                check_date = now + timedelta(days=day_offset)
                if check_date.weekday() == target_day:
                    next_date = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    next_dates.append(next_date)
                    break
        
        if next_dates:
            next_scheduled_at = min(next_dates)
            
            cursor.execute('''
                UPDATE recurring_mailings 
                SET next_scheduled_at = ?
                WHERE mailing_id = ?
            ''', (next_scheduled_at.isoformat(), mailing_id))
            
            cursor.execute('''
                UPDATE mailings 
                SET next_scheduled_at = ?, is_scheduled = 1, status = 'scheduled'
                WHERE id = ?
            ''', (next_scheduled_at.isoformat(), mailing_id))
            
            conn.commit()
            return True
        
        return False

def update_admin_password(new_password_hash: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE admin_credentials 
            SET password_hash = ? 
            WHERE id = 1
        ''', (new_password_hash,))
        
        success = cursor.rowcount > 0
        conn.commit()
        return success

def check_password(password: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT password_hash FROM admin_credentials WHERE id = 1')
        result = cursor.fetchone()
        
        if result:
            stored_hash = result[0]
            return check_password_hash(stored_hash, password)
        
        return False


def create_admin_credentials_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_credentials (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('SELECT COUNT(*) FROM admin_credentials')
        count = cursor.fetchone()[0]
        
        if count == 0:
            default_password = "SamaraBoy777"
            password_hash = generate_password_hash(default_password, method='pbkdf2:sha256')
            
            cursor.execute('''
                INSERT INTO admin_credentials (id, username, password_hash)
                VALUES (1, 'Woldemar', ?)
            ''', (password_hash,))
            
        
        conn.commit()



def update_mailing_data(mailing_id: int, name: str, message_text: str, 
                       media_type: str, media_url: str, inline_buttons: str) -> bool:   
    with get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE mailings 
                SET name = ?, message_text = ?, media_type = ?, media_url = ?, inline_buttons = ?
                WHERE id = ?
            ''', (name, message_text, media_type, media_url, inline_buttons, mailing_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            return False


def get_welcome_without_subscription() -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message_text, media_type, media_url, channel_url, channel_id, channel_button_text, is_active, created_at, updated_at
            FROM welcome_without_subscription 
            WHERE is_active = 1 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        if result:
            return {
                "id": result[0],
                "message_text": result[1],
                "media_type": result[2],
                "media_url": result[3],
                "channel_url": result[4],
                "channel_id": result[5],
                "channel_button_text": result[6],
                "is_active": result[7],
                "created_at": result[8],
                "updated_at": result[9]
            }
        return None


def save_welcome_without_subscription(message_text: str, media_type: str = "none", 
                                   media_url: str = None, channel_url: str = None, 
                                   channel_id: str = None, channel_button_text: str = None) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('UPDATE welcome_without_subscription SET is_active = 0')
        
        cursor.execute('''
            INSERT INTO welcome_without_subscription 
            (message_text, media_type, media_url, channel_url, channel_id, channel_button_text, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (message_text, media_type, media_url, channel_url, channel_id, channel_button_text))
        
        conn.commit()
        return cursor.rowcount > 0


def update_welcome_without_subscription(message_id: int, message_text: str, media_type: str = "none",
                                     media_url: str = None, channel_url: str = None, 
                                     channel_id: str = None, channel_button_text: str = None) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE welcome_without_subscription 
            SET message_text = ?, media_type = ?, media_url = ?, channel_url = ?, channel_id = ?, 
                channel_button_text = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (message_text, media_type, media_url, channel_url, channel_id, channel_button_text, message_id))
        conn.commit()
        return cursor.rowcount > 0


def get_all_welcome_without_subscription() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message_text, media_type, media_url, channel_url, channel_id, channel_button_text, is_active, created_at, updated_at
            FROM welcome_without_subscription 
            ORDER BY created_at DESC
        ''')
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "id": row[0],
                "message_text": row[1],
                "media_type": row[2],
                "media_url": row[3],
                "channel_url": row[4],
                "channel_id": row[5],
                "channel_button_text": row[6],
                "is_active": row[7],
                "created_at": row[8],
                "updated_at": row[9]
            })
        return messages


def save_subscription_message_with_buttons(message_text: str, media_type: str = "none", 
                                        media_url: str = None, inline_buttons: List[Dict] = None,
                                        inline_buttons_position: str = "below", back_button_text: str = "⬅️ Вернуться назад",
                                        main_menu_button_text: str = "🏠 Главное меню", show_back_button: bool = True,
                                        show_main_menu_button: bool = True) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('UPDATE subscription_messages SET is_active = 0')
        
        cursor.execute('''
            INSERT INTO subscription_messages 
            (message_text, media_type, media_url, inline_buttons, inline_buttons_position, 
             back_button_text, main_menu_button_text, show_back_button, show_main_menu_button, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (message_text, media_type, media_url, json.dumps(inline_buttons or []), inline_buttons_position,
              back_button_text, main_menu_button_text, 1 if show_back_button else 0, 1 if show_main_menu_button else 0))
        
        conn.commit()
        return cursor.rowcount > 0


def update_subscription_message_with_buttons(message_id: int, message_text: str, media_type: str = "none",
                                          media_url: str = None, inline_buttons: List[Dict] = None,
                                          inline_buttons_position: str = "below", back_button_text: str = "⬅️ Вернуться назад",
                                          main_menu_button_text: str = "🏠 Главное меню", show_back_button: bool = True,
                                          show_main_menu_button: bool = True) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE subscription_messages 
            SET message_text = ?, media_type = ?, media_url = ?, inline_buttons = ?, 
                inline_buttons_position = ?, back_button_text = ?, main_menu_button_text = ?,
                show_back_button = ?, show_main_menu_button = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (message_text, media_type, media_url, json.dumps(inline_buttons or []), inline_buttons_position,
              back_button_text, main_menu_button_text, 1 if show_back_button else 0, 1 if show_main_menu_button else 0, message_id))
        conn.commit()
        return cursor.rowcount > 0


def save_captcha_config(link_id: int, captcha_message: str, captcha_media_type: str = "none", 
                       captcha_media_url: str = None, captcha_button_text: str = "Я не робот") -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE channel_invite_links 
            SET captcha_message = ?, captcha_media_type = ?, captcha_media_url = ?, 
                captcha_button_text = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (captcha_message, captcha_media_type, captcha_media_url, captcha_button_text, link_id))
        conn.commit()
        return cursor.rowcount > 0


def get_captcha_config(link_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT captcha_message, captcha_media_type, captcha_media_url, captcha_button_text
            FROM channel_invite_links WHERE id = ?
        ''', (link_id,))
        row = cursor.fetchone()
        if row:
            return {
                "captcha_message": row[0] or "Я не робот",
                "captcha_media_type": row[1] or "none",
                "captcha_media_url": row[2] or "",
                "captcha_button_text": row[3] or "Я не робот"
            }
        return {
            "captcha_message": "Я не робот",
            "captcha_media_type": "none",
            "captcha_media_url": "",
            "captcha_button_text": "Я не робот"
        }


def mark_captcha_verified(user_id, chat_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_captcha_states 
            SET is_verified = 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND chat_id = ?
        ''', (user_id, chat_id))
        
        conn.commit()


def get_captcha_settings() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "captcha_message": settings.get("captcha_message", "Я не робот"),
        "captcha_media_type": settings.get("captcha_media_type", "none"),
        "captcha_media_url": settings.get("captcha_media_url", ""),
        "captcha_button_text": settings.get("captcha_button_text", "Я не робот")
    }


def save_captcha_settings(captcha_message: str, captcha_media_type: str = "none", 
                         captcha_media_url: str = None, captcha_button_text: str = "Я не робот") -> bool:
    try:
        update_setting('captcha_message', captcha_message)
        update_setting('captcha_media_type', captcha_media_type)
        update_setting('captcha_media_url', captcha_media_url or '')
        update_setting('captcha_button_text', captcha_button_text)
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань капчі: {e}")
        return False


def get_answers_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "message": settings.get("answers_message", "Ответы на часто задаваемые вопросы"),
        "media_type": settings.get("answers_media_type", "none"),
        "media_url": settings.get("answers_media_url", ""),
        "inline_buttons": json.loads(settings.get("answers_inline_buttons", "[]"))
    }


def save_answers_config(message: str, media_type: str = "none", 
                       media_url: str = None, inline_buttons: List[Dict] = None) -> bool:
    try:
        update_setting('answers_message', message)
        update_setting('answers_media_type', media_type)
        update_setting('answers_media_url', media_url or '')
        update_setting('answers_inline_buttons', json.dumps(inline_buttons or []))
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань 'Ответы на вопросы': {e}")
        return False


def get_private_lesson_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "message": settings.get("private_lesson_message", "Добро пожаловать на приватный урок!"),
        "media_type": settings.get("private_lesson_media_type", "none"),
        "media_url": settings.get("private_lesson_media_url", ""),
        "inline_buttons": json.loads(settings.get("private_lesson_inline_buttons", "[]"))
    }


def save_private_lesson_config(message: str, media_type: str = "none", 
                              media_url: str = None, inline_buttons: List[Dict] = None) -> bool:
    try:
        update_setting('private_lesson_message', message)
        update_setting('private_lesson_media_type', media_type)
        update_setting('private_lesson_media_url', media_url or '')
        update_setting('private_lesson_inline_buttons', json.dumps(inline_buttons or []))
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань 'Приватный урок': {e}")
        return False


def get_tariffs_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "message": settings.get("tariffs_message", "Наши тарифы и цены"),
        "media_type": settings.get("tariffs_media_type", "none"),
        "media_url": settings.get("tariffs_media_url", ""),
        "inline_buttons": json.loads(settings.get("tariffs_inline_buttons", "[]"))
    }


def save_tariffs_config(message: str, media_type: str = "none", 
                       media_url: str = None, inline_buttons: List[Dict] = None) -> bool:
    try:
        update_setting('tariffs_message', message)
        update_setting('tariffs_message', message)
        update_setting('tariffs_media_type', media_type)
        update_setting('tariffs_media_url', media_url or '')
        update_setting('tariffs_inline_buttons', json.dumps(inline_buttons or []))
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань 'Посмотреть тарифы': {e}")
        return False


def get_clothes_tariff_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "message": settings.get("clothes_tariff_message", "👗 <b>Тариф 'Одежда'</b>\n\nОпис тарифу для категорії одягу..."),
        "media_type": settings.get("clothes_tariff_media_type", "none"),
        "media_url": settings.get("clothes_tariff_media_url", ""),
        "button_text": settings.get("clothes_tariff_button_text", "💳 Оплатить тариф")
    }


def save_clothes_tariff_config(message: str, media_type: str = "none", media_url: str = None, button_text: str = None) -> bool:
    try:
        update_setting('clothes_tariff_message', message)
        update_setting('clothes_tariff_media_type', media_type)
        update_setting('clothes_tariff_media_url', media_url or '')
        update_setting('clothes_tariff_button_text', button_text or '💳 Оплатить тариф')
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань тарифу 'Одежда': {e}")
        return False


def get_tech_tariff_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "message": settings.get("tech_tariff_message", "🔧 <b>Тариф 'Техника'</b>\n\nОпис тарифу для технічних товарів..."),
        "media_type": settings.get("tech_tariff_media_type", "none"),
        "media_url": settings.get("tech_tariff_media_url", ""),
        "button_text": settings.get("tech_tariff_button_text", "💳 Оплатить тариф")
    }


def save_tech_tariff_config(message: str, media_type: str = "none", media_url: str = None, button_text: str = None) -> bool:
    try:
        update_setting('tech_tariff_message', message)
        update_setting('tech_tariff_media_type', media_type)
        update_setting('tech_tariff_media_url', media_url or '')
        update_setting('tech_tariff_button_text', button_text or '💳 Оплатить тариф')
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань тарифу 'Техника': {e}")
        return False


def get_clothes_payment_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "message": settings.get("clothes_payment_message", "💳 <b>Оплата тарифу 'Одежда'</b>\n\nІнформація про оплату..."),
        "media_type": settings.get("clothes_payment_media_type", "none"),
        "media_url": settings.get("clothes_payment_media_url", ""),
        "back_button_text": settings.get("clothes_payment_back_button_text", "⬅️ Вернуться назад"),
        "main_menu_button_text": settings.get("clothes_payment_main_menu_button_text", "🏠 Главное меню"),
        "show_back_button": settings.get("clothes_payment_show_back_button", "1") == "1",
        "show_main_menu_button": settings.get("clothes_payment_show_main_menu_button", "1") == "1"
    }


def save_clothes_payment_config(message: str, media_type: str = "none", media_url: str = None, 
                               back_button_text: str = None, main_menu_button_text: str = None,
                               show_back_button: bool = True, show_main_menu_button: bool = True) -> bool:
    try:
        update_setting('clothes_payment_message', message)
        update_setting('clothes_payment_media_type', media_type)
        update_setting('clothes_payment_media_url', media_url or '')
        update_setting('clothes_payment_back_button_text', back_button_text or '⬅️ Вернуться назад')
        update_setting('clothes_payment_main_menu_button_text', main_menu_button_text or '🏠 Главное меню')
        update_setting('clothes_payment_show_back_button', 1 if show_back_button else 0)
        update_setting('clothes_payment_show_main_menu_button', 1 if show_main_menu_button else 0)
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань оплати 'Одежда': {e}")
        return False


def get_tech_payment_config() -> Dict[str, Any]:
    settings = get_all_settings()
    
    return {
        "message": settings.get("tech_payment_message", "💳 <b>Оплата тарифу 'Техника'</b>\n\nІнформація про оплату..."),
        "media_type": settings.get("tech_payment_media_type", "none"),
        "media_url": settings.get("tech_payment_media_url", ""),
        "back_button_text": settings.get("tech_payment_back_button_text", "⬅️ Вернуться назад"),
        "main_menu_button_text": settings.get("tech_payment_main_menu_button_text", "🏠 Главное меню"),
        "show_back_button": settings.get("tech_payment_show_back_button", "1") == "1",
        "show_main_menu_button": settings.get("tech_payment_show_main_menu_button", "1") == "1"
    }


def save_tech_payment_config(message: str, media_type: str = "none", media_url: str = None,
                            back_button_text: str = None, main_menu_button_text: str = None,
                            show_back_button: bool = True, show_main_menu_button: bool = True) -> bool:
    try:
        update_setting('tech_payment_message', message)
        update_setting('tech_payment_media_type', media_type)
        update_setting('tech_payment_media_url', media_url or '')
        update_setting('tech_payment_back_button_text', back_button_text or '⬅️ Вернуться назад')
        update_setting('tech_payment_main_menu_button_text', main_menu_button_text or '🏠 Главное меню')
        update_setting('tech_payment_show_back_button', 1 if show_back_button else 0)
        update_setting('tech_payment_show_main_menu_button', 1 if show_main_menu_button else 0)
        return True
    except Exception as e:
        print(f"❌ Помилка при збереженні налаштувань оплати 'Техника': {e}")
        return False
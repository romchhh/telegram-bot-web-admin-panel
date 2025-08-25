import asyncio
import json
from aiogram import Bot
from database.settings_db import get_mailing_by_id, update_mailing_users_count
from database.client_db import get_all_users, get_users_by_status
from keyboards.client_keyboards import create_custom_keyboard
from utils.video_cache import send_video_with_caching_for_mailing


def get_filtered_users(mailing):
    """Отримує користувачів з урахуванням фільтрів розсилки"""
    user_filter = mailing.get("user_filter", "all")
    
    if user_filter == "all":
        return get_all_users()
    elif user_filter == "status":
        user_status = mailing.get("user_status", "")
        if user_status:
            statuses = user_status.split(',')
            users = []
            for status in statuses:
                status_users = get_users_by_status(status.strip())
                users.extend(status_users)
            # Видаляємо дублікати користувачів
            unique_users = []
            seen_ids = set()
            for user in users:
                if user[0] not in seen_ids:  # user[0] - це Telegram ID
                    unique_users.append(user)
                    seen_ids.add(user[0])
            return unique_users
        return get_all_users()
    
    return get_all_users()



async def send_mailing_to_users(bot: Bot, mailing_id: int) -> bool:
    try:
        mailing = get_mailing_by_id(mailing_id)
        if not mailing:
            print(f"Mailing with ID {mailing_id} not found")
            return False
        
        # Отримуємо користувачів з урахуванням фільтрів
        users = get_filtered_users(mailing)
        if not users:
            print("❌ No users found after filtering")
            return False
        
        print(f"🔍 Отримано {len(users)} користувачів після фільтрації")
        if users:
            print(f"🔍 Приклад структури користувача: {users[0]}")
            print(f"🔍 user[0] (Telegram ID): {users[0][0]}")
            print(f"🔍 user[1] (username): {users[0][1]}")
        
        # Фільтруємо користувачів з валідними ID
        valid_users = []
        for user in users:
            if user and len(user) > 0 and user[0] is not None:
                valid_users.append(user)
            else:
                print(f"⚠️ Пропускаємо користувача з невалідними даними: {user}")
        
        if not valid_users:
            print("❌ No valid users found after ID validation")
            return False
        
        print(f"📊 Знайдено {len(valid_users)} валідних користувачів для розсилки")
        
        keyboard = None
        
        if mailing.get("inline_buttons"):  # inline_buttons
            try:
                buttons_data = json.loads(mailing["inline_buttons"])
                keyboard = create_custom_keyboard(buttons_data)
            except json.JSONDecodeError as e:
                keyboard = None
        
        success_count = 0
        error_count = 0
        
        for user in valid_users:
            user_id = user[0]  # user_id - це Telegram ID, знаходиться в позиції [0]
            
            # Пропускаємо користувачів з невалідним ID
            if not user_id or user_id is None:
                print(f"⚠️ Пропускаємо користувача з невалідним ID: {user}")
                error_count += 1
                continue
            
            try:
                if mailing.get("media_type") == "photo" and mailing.get("media_url"):
                    media_url = mailing["media_url"].strip()
                    if not media_url:
                        print(f"⚠️ Пропускаємо фото без URL/file_id для користувача {user_id}")
                        error_count += 1
                        continue
                    
                    # Перевіряємо чи це file_id або URL
                    if media_url.startswith(('http://', 'https://')):
                        # Це URL - відправляємо по посиланню
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=media_url,
                            caption=mailing["message_text"],
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        print(f"✅ Фото відправлено користувачу {user_id} по URL")
                    else:
                        # Це file_id - відправляємо по file_id
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=media_url,
                            caption=mailing["message_text"],
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        print(f"✅ Фото відправлено користувачу {user_id} по file_id")
                        
                elif mailing.get("media_type") == "video" and mailing.get("media_url"):
                    media_url = mailing["media_url"].strip()
                    if not media_url:
                        print(f"⚠️ Пропускаємо відео без URL/file_id для користувача {user_id}")
                        error_count += 1
                        continue
                    
                    cache_key = f"mailing_video_{mailing_id}"
                    success = await send_video_with_caching_for_mailing(
                        bot,
                        user_id,
                        media_url,  # media_url або file_id
                        mailing["message_text"],
                        keyboard,
                        cache_key
                    )
                    
                    if not success:
                        print(f"❌ Не вдалося відправити відео користувачу {user_id}")
                        error_count += 1
                        continue
                    else:
                        print(f"✅ Відео відправлено користувачу {user_id}")
                        
                else:
                    # Відправляємо текст без медіа
                    await bot.send_message(
                        chat_id=user_id,
                        text=mailing["message_text"],
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    print(f"✅ Текст відправлено користувачу {user_id}")
                
                success_count += 1
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Помилка відправки користувачу {user_id}: {e}")
                error_count += 1
                continue
        
        update_mailing_users_count(mailing_id, success_count)
        
        if success_count > 0 and mailing.get("is_recurring"):
            from database.settings_db import schedule_next_recurring
            try:
                next_scheduled = schedule_next_recurring(mailing_id)
                if next_scheduled:
                    print(f"✅ Наступна повторювана розсилка {mailing_id} запланована успішно")
            except Exception as e:
                print(f"❌ Помилка при плануванні наступної повторюваної розсилки {mailing_id}: {e}")
        elif success_count > 0:
            print(f"✅ Розсилка {mailing_id} завершена успішно")
        
        print(f"📊 Результати розсилки {mailing_id}:")
        print(f"   ✅ Успішно відправлено: {success_count}")
        print(f"   ❌ Помилки: {error_count}")
        print(f"   📊 Всього користувачів: {len(valid_users)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Розсилка {mailing_id}: {e}")
        return False


async def process_pending_mailings(bot: Bot) -> None:
    from database.settings_db import get_scheduled_mailings, update_mailing_status, schedule_next_recurring
    from datetime import datetime
    import pytz
    
    try:
        kyiv_tz = pytz.timezone('Europe/Kiev')
        current_time = datetime.now(kyiv_tz)
        
        scheduled_mailings = get_scheduled_mailings()
        print(f"📅 Знайдено {len(scheduled_mailings)} запланованих розсилок")
        
        for mailing in scheduled_mailings:
            mailing_id = mailing[0]
            scheduled_at_str = mailing[10]
            is_recurring = mailing[13] if len(mailing) > 13 else False
            next_scheduled_str = mailing[17] if len(mailing) > 17 else None
            
            print(f"📋 Розсилка {mailing_id}: scheduled_at={scheduled_at_str}, is_recurring={is_recurring}, next_scheduled={next_scheduled_str}")
            
            if is_recurring and next_scheduled_str:
                try:
                    if 'T' in next_scheduled_str:
                        next_scheduled = datetime.fromisoformat(next_scheduled_str.replace('Z', '+00:00'))
                        next_scheduled = pytz.utc.localize(next_scheduled).astimezone(kyiv_tz)
                    else:
                        next_scheduled = datetime.strptime(next_scheduled_str, '%Y-%m-%d %H:%M:%S')
                        next_scheduled = kyiv_tz.localize(next_scheduled)
                    
                    if current_time >= next_scheduled:
                        print(f"🔄 Запускаємо повторювану розсилку {mailing_id}")
                        success = await send_mailing_to_users(bot, mailing_id)
                        
                        if success:
                            update_mailing_status(mailing_id, 'sent')
                            print(f"✅ Повторювана розсилка {mailing_id} успішно відправлена")
                            
                            try:
                                next_scheduled = schedule_next_recurring(mailing_id)
                                if next_scheduled:
                                    print(f"✅ Наступна повторювана розсилка {mailing_id} запланована успішно")
                            except Exception as e:
                                print(f"❌ Помилка при плануванні наступної повторюваної розсилки {mailing_id}: {e}")
                        else:
                            update_mailing_status(mailing_id, 'failed')
                            print(f"❌ Повторювана розсилка {mailing_id} не вдалася")
                    
                except Exception as e:
                    print(f"❌ Помилка при обробці розсилки {mailing_id}: {e}")
                    continue
            
            elif scheduled_at_str:
                try:
                    if 'T' in scheduled_at_str:
                        scheduled_at = datetime.fromisoformat(scheduled_at_str.replace('Z', '+00:00'))
                        scheduled_at = pytz.utc.localize(scheduled_at).astimezone(kyiv_tz)
                    else:
                        scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%d %H:%M:%S')
                        scheduled_at = kyiv_tz.localize(scheduled_at)
                    
                    if current_time >= scheduled_at:
                        print(f"📅 Запускаємо заплановану розсилку {mailing_id}")
                        success = await send_mailing_to_users(bot, mailing_id)
                        
                        if success:
                            update_mailing_status(mailing_id, 'sent')
                            print(f"✅ Запланована розсилка {mailing_id} успішно відправлена")
                        else:
                            update_mailing_status(mailing_id, 'failed')
                            print(f"❌ Запланована розсилка {mailing_id} не вдалася")
                    
                except Exception as e:
                    print(f"❌ Помилка при обробці звичайної розсилки {mailing_id}: {e}")
                    continue
        
    except Exception as e:
        print(f"❌ Помилка при обробці запланованих розсилок: {e}")


async def check_and_send_scheduled_mailings(bot: Bot) -> None:
    await process_pending_mailings(bot)

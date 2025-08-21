import asyncio
import logging
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.client_db import update_user_status_by_action
from utils.video_cache import send_video_with_caching
from keyboards.client_keyboards import create_channel_keyboard, create_inline_only_keyboard
from database.settings_db import get_answers_config, get_private_lesson_config, get_tariffs_config, get_clothes_tariff_config, get_tech_tariff_config, get_clothes_payment_config, get_tech_payment_config

async def check_user_subscription(bot, user_id: int, channel_id: str) -> bool:
    try:
        if channel_id.startswith('@'):
            chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        else:
            chat_member = await bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
        
        return chat_member.status not in ['left', 'kicked']
    except Exception as e:
        print(f"Помилка при перевірці підписки: {e}")
        return False


async def send_welcome_without_subscription(message: types.Message, welcome_config):
    try:
        message_text = welcome_config["message_text"]
        media_type = welcome_config["media_type"]
        media_url = welcome_config["media_url"]
        
        channel_keyboard = create_channel_keyboard(welcome_config["channel_url"], welcome_config.get("channel_button_text", "📢 Подписаться на канал"))
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=channel_keyboard
                    )
                else:
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=channel_keyboard
                    )
            elif media_type == "video":
                if media_url.startswith(('http://', 'https://')):
                    cache_key = "welcome_without_subscription_video"
                    success = await send_video_with_caching(
                        message, 
                        media_url, 
                        message_text, 
                        channel_keyboard, 
                        cache_key
                    )
                else:
                    await message.answer_video(
                        video=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=channel_keyboard
                    )
        else:
            await message.answer(
                message_text,
                parse_mode="HTML",
                reply_markup=channel_keyboard
            )
    except Exception as e:
        print(f"Помилка при відправці повідомлення без підписки: {e}")
        await message.answer(
            "Добро пожаловать! Для использования бота необходимо подписаться на наш канал.",
            reply_markup=channel_keyboard
        )



async def send_answers_message_with_sequence(message: types.Message):
    try:
        config = get_answers_config()
        
        message_text = config["message"]
        media_type = config["media_type"]
        media_url = config["media_url"]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎓 Приватный урок", callback_data="private_lesson_sequence")]
        ])
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Це file_id
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "answers_video_sequence"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )
        else:
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        print(f"✅ Відправлено послідовне повідомлення 'Ответы на вопросы' користувачу {message.from_user.id}")
        
    except Exception as e:
        print(f"❌ Помилка при відправці послідовного повідомлення 'Ответы на вопросы': {e}")


async def send_private_lesson_message_with_sequence(message: types.Message):
    try:
        config = get_private_lesson_config()
        update_user_status_by_action(message.from_user.id, "private_lesson_viewed")
        
        message_text = config["message"]
        media_type = config["media_type"]
        media_url = config["media_url"]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Посмотреть тарифы", callback_data="tariffs_sequence")]
        ])
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                # Перевіряємо чи це file_id або URL
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Це file_id
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "private_lesson_video_sequence"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )
        else:
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        print(f"✅ Відправлено послідовне повідомлення 'Приватный урок' користувачу {message.from_user.id}")
        
    except Exception as e:
        print(f"❌ Помилка при відправці послідовного повідомлення 'Приватный урок': {e}")


async def send_tariffs_message_with_sequence(message: types.Message):
    try:
        from database.settings_db import get_tariffs_config, get_clothes_tariff_config, get_tech_tariff_config
        config = get_tariffs_config()
        clothes_config = get_clothes_tariff_config()
        tech_config = get_tech_tariff_config()
        
        message_text = config["message"]
        media_type = config["media_type"]
        media_url = config["media_url"]
        
        # Отримуємо назви кнопок з бази даних
        clothes_button_text = clothes_config.get("button_text", "👗 Одежда")
        tech_button_text = tech_config.get("button_text", "🔧 Техника")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=clothes_button_text, callback_data="clothes")],
            [InlineKeyboardButton(text=tech_button_text, callback_data="tech")]
        ])
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Це file_id
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "tariffs_video_sequence"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )
        else:
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        print(f"✅ Відправлено послідовне повідомлення 'Посмотреть тарифы' користувачу {message.from_user.id}")
        
        await update_user_status_by_action(message.from_user.id, "tariffs_viewed")
        
    except Exception as e:
        print(f"❌ Помилка при відправці послідовного повідомлення 'Посмотреть тарифы': {e}")


async def send_clothes_tariff_message(message: types.Message):
    try:
        config = get_clothes_tariff_config()
        
        update_user_status_by_action(message.from_user.id, "clothes_tariff_viewed")
        
        message_text = config.get("message", "👗 <b>Тариф 'Одежда'</b>\n\nОпис тарифу для категорії одягу...")
        media_type = config.get("media_type", "none")
        media_url = config.get("media_url", "")
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=config.get("button_text", "💳 Оплатить тариф"), callback_data="pay_clothes")]
        ])
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                # Перевіряємо чи це file_id або URL
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Це file_id
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "clothes_tariff_video"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )
        else:
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        print(f"✅ Відправлено детальну сторінку тарифу 'Одежда' користувачу {message.from_user.id}")
        
    except Exception as e:
        print(f"❌ Помилка при відправці тарифу 'Одежда': {e}")


async def send_tech_tariff_message(message: types.Message):
    try:
        config = get_tech_tariff_config()
        
        update_user_status_by_action(message.from_user.id, "tech_tariff_viewed")
        
        message_text = config.get("message", "🔧 <b>Тариф 'Техника'</b>\n\nОпис тарифу для технічних товарів...")
        media_type = config.get("media_type", "none")
        media_url = config.get("media_url", "")
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=config.get("button_text", "💳 Оплатить тариф"), callback_data="pay_tech")]
        ])
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "tech_tariff_video"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )
        else:
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        print(f"✅ Відправлено детальну сторінку тарифу 'Техника' користувачу {message.from_user.id}")
        
    except Exception as e:
        print(f"❌ Помилка при відправці тарифу 'Техника': {e}")


async def send_clothes_payment_message(message: types.Message):
    try:
        config = get_clothes_payment_config()
        
        update_user_status_by_action(message.from_user.id, "clothes_payment_clicked")
        
        message_text = config.get("message", "💳 <b>Оплата тарифу 'Одежда'</b>\n\nІнформація про оплату...")
        media_type = config.get("media_type", "none")
        media_url = config.get("media_url", "")

        keyboard_buttons = []
        
        if config.get("show_back_button", True):
            keyboard_buttons.append([InlineKeyboardButton(text=config.get("back_button_text", "⬅️ Вернуться назад"), callback_data="clothes")])
        
        if config.get("show_main_menu_button", True):
            keyboard_buttons.append([InlineKeyboardButton(text=config.get("main_menu_button_text", "🏠 Главное меню"), callback_data="back_to_start")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "clothes_payment_video"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )
        else:
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        print(f"✅ Відправлено сторінку оплати тарифу 'Одежда' користувачу {message.from_user.id}")
        
    except Exception as e:
        print(f"❌ Помилка при відправці сторінки оплати 'Одежда': {e}")


async def send_tech_payment_message(message: types.Message):
    try:
        config = get_tech_payment_config()
        
        update_user_status_by_action(message.from_user.id, "tech_payment_clicked")
        
        message_text = config.get("message", "💳 <b>Оплата тарифу 'Техника'</b>\n\nІнформація про оплату...")
        media_type = config.get("media_type", "none")
        media_url = config.get("media_url", "")
        
        keyboard_buttons = []
        
        if config.get("show_back_button", True):
            keyboard_buttons.append([InlineKeyboardButton(text=config.get("back_button_text", "⬅️ Вернуться назад"), callback_data="tech")])
        
        if config.get("show_main_menu_button", True):
            keyboard_buttons.append([InlineKeyboardButton(text=config.get("main_menu_button_text", "🏠 Главное меню"), callback_data="back_to_start")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "tech_payment_video"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )
        else:
            await message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        print(f"✅ Відправлено сторінку оплати тарифу 'Техника' користувачу {message.from_user.id}")
        
    except Exception as e:
        print(f"❌ Помилка при відправці сторінки оплати 'Техника': {e}")


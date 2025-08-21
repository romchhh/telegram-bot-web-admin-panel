import asyncio
from aiogram import Router, types, F
from main import bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database.client_db import (
    add_user, update_user_activity, create_table, 
    update_user_status_by_action
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.settings_db import (get_start_message_config, create_settings_table, get_subscription_message,
                                create_welcome_without_subscription_table, create_subscription_messages_table,
                                get_channel_leave_config, create_mailings_table, create_recurring_mailings_table, create_admin_credentials_table, get_welcome_without_subscription, get_captcha_settings, get_channel_invite_link_by_chat_id)
from keyboards.client_keyboards import get_subscription_message_keyboard, create_combined_keyboard, create_captcha_keyboard, create_inline_only_keyboard
from database.start_params_db import create_start_params_table
from utils.video_cache import send_video_with_caching
from config import CHANNEL_ID
from states.client_states import MediaStates
from utils.client_functions import check_user_subscription, send_welcome_without_subscription, send_answers_message_with_sequence, send_private_lesson_message_with_sequence, send_tariffs_message_with_sequence, send_clothes_tariff_message, send_tech_tariff_message, send_clothes_payment_message, send_tech_payment_message


router = Router()

user_states = {}

class UserStates:
    WAITING_FOR_CHANNEL_REQUEST = "waiting_for_channel_request"
    WAITING_FOR_CAPTCHA = "waiting_for_captcha"
    CAPTCHA_VERIFIED = "captcha_verified"


@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    if message.text and ' ' in message.text:
        start_param = message.text.split(' ')[1]
    else:
        start_param = None
        
    user_id = message.from_user.id
    
    add_user(user_id, message.from_user.username, start_param)
    update_user_activity(user_id)
    
    # Оновлюємо статус користувача
    update_user_status_by_action(user_id, "start")
    
    welcome_without_subscription = get_welcome_without_subscription()
    if welcome_without_subscription and welcome_without_subscription.get("channel_id"):
        channel_id = welcome_without_subscription["channel_id"]
        is_subscribed = await check_user_subscription(bot, user_id, channel_id)
        
        if not is_subscribed:
            print(f"🔍 Setting custom state to {UserStates.WAITING_FOR_CHANNEL_REQUEST}")
            # Зберігаємо стан та дані користувача
            user_states[user_id] = {
                'state': UserStates.WAITING_FOR_CHANNEL_REQUEST,
                'channel_id': channel_id,
                'user_id': user_id
            }

            await send_welcome_without_subscription(message, welcome_without_subscription)
            return
    

    config = get_start_message_config()
    
    start_message = config["message"]
    media_type = config["media_type"]
    media_url = config["media_url"]
    inline_buttons = config.get("inline_buttons", [])
    answers_button_text = config.get("answers_button_text", "💡 Ответы")
    private_lesson_button_text = config.get("private_lesson_button_text", "🎓 Приватный урок")
    tariffs_button_text = config.get("tariffs_button_text", "💰 Тарифы")
    inline_buttons_position = config.get("inline_buttons_position", "below")
    
    combined_keyboard = create_combined_keyboard(inline_buttons, answers_button_text, private_lesson_button_text, tariffs_button_text, inline_buttons_position)
    
    if media_type != "none" and media_url:
        if media_type == "photo":
            if media_url.startswith(('http://', 'https://')):
                await message.answer_photo(
                    photo=media_url,
                    caption=start_message,
                    parse_mode="HTML",
                    reply_markup=combined_keyboard
                )
            else:
                await message.answer_photo(
                    photo=media_url,
                    caption=start_message,
                    parse_mode="HTML",
                    reply_markup=combined_keyboard
                )
        elif media_type == "video":
            if media_url.startswith(('http://', 'https://')):
                cache_key = "welcome_video"
                success = await send_video_with_caching(
                    message, 
                    media_url, 
                    start_message, 
                    combined_keyboard, 
                    cache_key
                )
            else:
                await message.answer_video(
                    video=media_url,
                    caption=start_message,
                    parse_mode="HTML",
                    reply_markup=combined_keyboard
                )
    else:
        await message.answer(
            start_message,
            parse_mode="HTML",
            reply_markup=combined_keyboard
        )






@router.message(Command("get_media_id"))
async def get_media_id_start(message: types.Message, state: FSMContext):
    await message.answer("📤 Пожалуйста, скиньте медиа (фото, видео, документ, аудио), чтобы я мог получить его ID. Чтобы отменить, напишите /cancel")
    await state.set_state(MediaStates.waiting_for_media)


@router.message(MediaStates.waiting_for_media, ~Command("cancel"))
async def process_media_for_id(message: types.Message, state: FSMContext):
    try:
        # Проверяем, есть ли медиа в сообщении
        if message.photo:
            file_id = message.photo[-1].file_id
            file_size = message.photo[-1].file_size
            file_unique_id = message.photo[-1].file_unique_id
            
            try:
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                await message.answer(
                    f"📸 <b>Фото ID:</b> <code>{file_id}</code>\n"
                    f"📁 <b>File ID:</b> <code>{file_info.file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n",
                    parse_mode="HTML"
                )
            except Exception as file_error:
                # Если файл слишком большой, показываем только доступную информацию
                await message.answer(
                    f"📸 <b>Фото ID:</b> <code>{file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n", 
                    parse_mode="HTML"
                )
                
        elif message.video:
            file_id = message.video.file_id
            file_size = message.video.file_size
            file_unique_id = message.video.file_unique_id
            duration = message.video.duration
            width = message.video.width
            height = message.video.height
            
            try:
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                await message.answer(
                    f"🎥 <b>Видео ID:</b> <code>{file_id}</code>\n"
                    f"📁 <b>File ID:</b> <code>{file_info.file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n",
                    parse_mode="HTML"
                )
            except Exception as file_error:
                await message.answer(
                    f"🎥 <b>Видео ID:</b> <code>{file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n", 
                    parse_mode="HTML"
                )
                
        elif message.document:
            file_id = message.document.file_id
            file_size = message.document.file_size
            file_unique_id = message.document.file_unique_id
            file_name = message.document.file_name
            mime_type = message.document.mime_type
            
            try:
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                await message.answer(
                    f"📄 <b>Документ ID:</b> <code>{file_id}</code>\n"
                    f"📁 <b>File ID:</b> <code>{file_info.file_id}</code>\n",
                    parse_mode="HTML"
                )
            except Exception as file_error:
                await message.answer(
                    f"📄 <b>Документ ID:</b> <code>{file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n", 
                    parse_mode="HTML"
                )
                
        elif message.audio:
            file_id = message.audio.file_id
            file_size = message.audio.file_size
            file_unique_id = message.audio.file_unique_id
            duration = message.audio.duration
            title = message.audio.title or "Не указано"
            performer = message.audio.performer or "Не указано"
            
            try:
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                await message.answer(
                    f"🎵 <b>Аудио ID:</b> <code>{file_id}</code>\n"
                    f"📁 <b>File ID:</b> <code>{file_info.file_id}</code>\n",
                    parse_mode="HTML"
                )
            except Exception as file_error:
                await message.answer(
                    f"🎵 <b>Аудио ID:</b> <code>{file_id}</code>\n"
                    f"🆔 <b>Unique ID:</b> <code>{file_unique_id}</code>\n",
                    parse_mode="HTML"
                )
                
        elif message.voice:
            file_id = message.voice.file_id
            file_size = message.voice.file_size
            file_unique_id = message.voice.file_unique_id
            duration = message.voice.duration
            
            try:
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                await message.answer(
                    f"🎤 <b>Голосовое ID:</b> <code>{file_id}</code>\n"
                    f"📁 <b>File ID:</b> <code>{file_info.file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n", 
                    parse_mode="HTML"
                )
            except Exception as file_error:
                await message.answer(
                    f"🎤 <b>Голосовое ID:</b> <code>{file_id}</code>\n"
                    f"🆔 <b>Unique ID:</b> <code>{file_unique_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n"
                    f"⏱️ <b>Длительность:</b> {duration} сек\n"
                    f"⚠️ <b>Файл слишком большой для получения дополнительной информации</b>", 
                    parse_mode="HTML"
                )
                
        elif message.video_note:
            file_id = message.video_note.file_id
            file_size = message.video_note.file_size
            file_unique_id = message.video_note.file_unique_id
            duration = message.video_note.duration
            length = message.video_note.length
            
            try:
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                await message.answer(
                    f"📹 <b>Видео-сообщение ID:</b> <code>{file_id}</code>\n"
                    f"📁 <b>File ID:</b> <code>{file_info.file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n", 
                    parse_mode="HTML"
                )
            except Exception as file_error:
                await message.answer(
                    f"📹 <b>Видео-сообщение ID:</b> <code>{file_id}</code>\n"
                    f"📏 <b>Размер:</b> {file_size} байт\n", 
                    parse_mode="HTML"
                )
        else:
            await message.answer("❌ Это не медиа файл. Пожалуйста, скиньте фото, видео, документ или аудио. Чтобы отменить, напишите /cancel")
            return
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        print(f"Ошибка при получении ID медиа: {e}")
        await message.answer("❌ Ошибка при получении ID медиа. Попробуйте еще раз. Чтобы отменить, напишите /cancel")
        await state.clear()

@router.message(Command("cancel"), MediaStates.waiting_for_media)
async def cancel_media_id(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено. Вы можете использовать /get_media_id снова, если нужно.")




async def send_subscription_success_message(bot, user_id: int) -> bool:
    try:
        subscription_message = get_subscription_message()
        
        if not subscription_message:
            return False
        
        message_text = subscription_message['message_text']
        media_type = subscription_message['media_type']
        media_url = subscription_message['media_url']
        keyboard = get_subscription_message_keyboard(subscription_message)
        
        if media_type == 'photo' and media_url:
            await bot.send_photo(
                chat_id=user_id,
                photo=media_url,
                caption=message_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        elif media_type == 'video' and media_url:
            cache_key = "subscription_video"
            success = await send_video_with_caching(
                types.Message(chat=types.Chat(id=user_id), from_user=types.User(id=user_id)), 
                media_url, 
                message_text, 
                keyboard, 
                cache_key
            )

        else:
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        
        return True
        
    except Exception as e:
        print(f"Помилка при відправці повідомлення після перевірки підписки: {e}")
        return False



@router.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_activity(user_id)
    
    config = get_start_message_config()
    
    start_message = config["message"]
    media_type = config["media_type"]
    media_url = config["media_url"]
    inline_buttons = config.get("inline_buttons", [])
    answers_button_text = config.get("answers_button_text", "💡 Ответы")
    private_lesson_button_text = config.get("private_lesson_button_text", "🎓 Приватный урок")
    tariffs_button_text = config.get("tariffs_button_text", "💰 Тарифы")
    inline_buttons_position = config.get("inline_buttons_position", "below")
    
    combined_keyboard = create_combined_keyboard(inline_buttons, answers_button_text, private_lesson_button_text, tariffs_button_text, inline_buttons_position)
    
    if media_type != "none" and media_url:
        if media_type == "photo":
            # Перевіряємо чи це file_id або URL
            if media_url.startswith(('http://', 'https://')):
                await callback.message.answer_photo(
                    photo=media_url,
                    caption=start_message,
                    parse_mode="HTML",
                    reply_markup=combined_keyboard
                )
            else:
                # Це file_id
                await callback.message.answer_photo(
                    photo=media_url,
                    caption=start_message,
                    parse_mode="HTML",
                    reply_markup=combined_keyboard
                )
        elif media_type == "video":
            cache_key = "welcome_video"
            success = await send_video_with_caching(
                callback.message, 
                media_url, 
                start_message, 
                combined_keyboard, 
                cache_key
            )
    else:
        await callback.message.answer(
            start_message,
            parse_mode="HTML",
            reply_markup=combined_keyboard
        )
    
    await callback.message.delete()
    await callback.answer()



@router.message(F.text)
async def handle_captcha_text(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip() if message.text else None

    
    user_data = user_states.get(user_id, {})
    current_state = user_data.get('state')
    
    if current_state != UserStates.WAITING_FOR_CAPTCHA:
        return
    
    try:
        if not user_text:
            await message.answer("❌ Пожалуйста, нажмите кнопку на клавиатуре для прохождения капчи.", parse_mode="HTML")
            return
        
        captcha_settings = get_captcha_settings()
        captcha_button_text = captcha_settings["captcha_button_text"]
        
        if user_text == captcha_button_text:
            chat_id = user_data.get('chat_id')
            
            if chat_id:
                captcha_message_id = user_data.get('captcha_message_id')
                if captcha_message_id:
                    try:
                        await bot.delete_message(chat_id=user_id, message_id=captcha_message_id)
                    except Exception as e:
                        print(f"Не вдалося видалити повідомлення капчі: {e}")
                
                user_states[user_id]['state'] = UserStates.CAPTCHA_VERIFIED
                
                update_user_status_by_action(user_id, "captcha_passed")
                
                await send_answers_message_with_sequence(message)
                
                if user_id in user_states:
                    del user_states[user_id]
            else:
                print("❌ Error: chat_id not found in state data")
                await message.answer("❌ Произошла ошибка при проверке капчи. Попробуйте еще раз.", parse_mode="HTML")
        else:
            await message.answer("❌ Неверный текст капчи. Пожалуйста, нажмите кнопку на клавиатуре.", parse_mode="HTML")
            
    except Exception as e:
        print(f"❌ Error in handle_captcha_text: {e}")
        await message.answer("❌ Произошла ошибка при проверке капчи. Попробуйте еще раз.", parse_mode="HTML")





@router.chat_join_request()
async def handle_chat_join_request(chat_join_request: types.ChatJoinRequest):
    user_id = chat_join_request.from_user.id
    user_name = chat_join_request.from_user.username or "Пользователь без юзернейма"
    add_user(user_id, user_name)

    chat = chat_join_request.chat

    try:
        # Инициализируем состояние пользователя
        if user_id not in user_states:
            user_states[user_id] = {}
        
        # Устанавливаем состояние ожидания капчи сразу
        user_states[user_id]['state'] = UserStates.WAITING_FOR_CAPTCHA
        user_states[user_id]['chat_id'] = chat.id
        
        # Получаем настройки пригласительной ссылки для данного канала
        invite_link_config = get_channel_invite_link_by_chat_id(chat.id)
        
        # Если есть сообщение для пригласительной ссылки, отправляем его
        if invite_link_config and invite_link_config['message_text'].strip():
            message_text = invite_link_config['message_text']
            media_type = invite_link_config['media_type']
            media_url = invite_link_config['media_url']
            
            try:
                if media_type != "none" and media_url:
                    if media_type == "photo":
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=media_url,
                            caption=message_text,
                            parse_mode="HTML"
                        )
                    elif media_type == "video":
                        cache_key = f"invite_video_{invite_link_config['id']}"
                        await send_video_with_caching(
                            types.Message(chat=types.Chat(id=user_id), from_user=types.User(id=user_id)), 
                            media_url, 
                            message_text, 
                            None, 
                            cache_key
                        )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=message_text,
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"❌ Error sending invite link message: {e}")
        
        # Отправляем капчу (всегда)
        captcha_settings = get_captcha_settings()
        
        captcha_message = captcha_settings["captcha_message"]
        captcha_media_type = captcha_settings["captcha_media_type"]
        captcha_media_url = captcha_settings["captcha_media_url"]
        captcha_button_text = captcha_settings["captcha_button_text"]
        
        captcha_keyboard = create_captcha_keyboard(captcha_button_text)
        
        sent_message = None
        if captcha_media_type != "none" and captcha_media_url:
            if captcha_media_type == "photo":
                if captcha_media_url.startswith(('http://', 'https://')):
                    sent_message = await bot.send_photo(
                        chat_id=user_id,
                        photo=captcha_media_url,
                        caption=captcha_message,
                        parse_mode="HTML",
                        reply_markup=captcha_keyboard
                    )
                else:
                    sent_message = await bot.send_photo(
                        chat_id=user_id,
                        photo=captcha_media_url,
                        caption=captcha_message,
                        parse_mode="HTML",
                        reply_markup=captcha_keyboard
                    )
            elif captcha_media_type == "video":
                cache_key = "captcha_video"
                success = await send_video_with_caching(
                    types.Message(chat=types.Chat(id=user_id), from_user=types.User(id=user_id)), 
                    captcha_media_url, 
                    captcha_message, 
                    captcha_keyboard, 
                    cache_key
                )
                if success:
                    try:
                        updates = await bot.get_updates(offset=-1, limit=1)
                        if updates:
                            sent_message = updates[0].message
                    except:
                        pass
        else:
            sent_message = await bot.send_message(
                chat_id=user_id,
                text=captcha_message,
                parse_mode="HTML",
                reply_markup=captcha_keyboard
            )
        
        if sent_message:
            user_states[user_id]['captcha_message_id'] = sent_message.message_id
        
        await bot.approve_chat_join_request(
            chat_id=chat.id,
            user_id=user_id
        )
        return
            
    except Exception as e:
        print(f"❌ Error in handle_chat_join_request: {e}")
        print(f"User ID: {user_id}, Chat ID: {chat.id if chat else 'None'}")
        import traceback
        traceback.print_exc()
        return


async def send_channel_leave_message(bot, user_id: int) -> bool:
    try:
        config = get_channel_leave_config()
        message_text = config["message"]
        media_type = config["media_type"]
        media_url = config["media_url"]
        inline_buttons = config.get("inline_buttons", [])
        

        keyboard_buttons = []
        
        first_row = []
        leave_button_text = config.get("leave_button_text", "Уйти")
        first_row.append(InlineKeyboardButton(
            text=leave_button_text, 
            callback_data="channel_leave_leave"
        ))
        
        return_button_text = config.get("return_button_text", "Возвращаюсь")
        return_url = config.get("return_url", "")
        if return_url:
            first_row.append(InlineKeyboardButton(
                text=return_button_text, 
                url=return_url
            ))
        
        if first_row:
            keyboard_buttons.append(first_row)
        
        if inline_buttons and isinstance(inline_buttons, list):
            for button in inline_buttons:
                if isinstance(button, dict) and 'text' in button and 'url' in button:
                    if button['text'].strip() and button['url'].strip():
                        keyboard_buttons.append([InlineKeyboardButton(
                            text=button['text'].strip(), 
                            url=button['url'].strip()
                        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "channel_leave_message_video"
                success = await send_video_with_caching(
                    types.Message(chat=types.Chat(id=user_id), from_user=types.User(id=user_id)), 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )

        else:
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        return True
        
    except Exception as e:
        return False



@router.callback_query(lambda c: c.data == "channel_leave_leave")
async def handle_channel_leave_leave(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
        
        config = get_channel_leave_config()
        message_text = config.get("leave_message", "Вы уверены, что хотите уйти?")
        media_type = config.get("leave_media_type", "none")
        media_url = config.get("leave_media_url", "")
        inline_buttons = config.get("leave_inline_buttons", [])
        
        keyboard = create_inline_only_keyboard(inline_buttons)
        
        if media_type != "none" and media_url:
            if media_type == "photo":
                if media_url.startswith(('http://', 'https://')):
                    await callback.message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await callback.message.answer_photo(
                        photo=media_url,
                        caption=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            elif media_type == "video":
                cache_key = "channel_leave_video"
                success = await send_video_with_caching(
                    callback.message, 
                    media_url, 
                    message_text, 
                    keyboard, 
                    cache_key
                )

        else:
            await callback.message.answer(
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        await callback.answer()
        
    except Exception as e:
        await callback.answer("Произошла ошибка", show_alert=True)



@router.chat_member()
async def handle_chat_member_update(update: types.ChatMemberUpdated):
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    user = update.new_chat_member.user
    chat_id = update.chat.id
    user_id = user.id
    user_name = user.first_name or "Користувач"
    username = user.username
    

    if old_status in ["left", "kicked"] and new_status == "member":
        print(f"✅ Користувач {user_name} приєднався до каналу")

    elif old_status == "member" and new_status in ["left", "kicked"]:
        if new_status == "left":
            print(f"❌ Користувач {user_name} покинув канал")
            await send_channel_leave_message(bot, user_id)
        elif new_status == "kicked":
            print(f"🚫 Користувач {user_name} був вигнаний з каналу")   
            await send_channel_leave_message(bot, user_id)
    elif old_status == "restricted" and new_status == "member":
        print(f"✅ Заявку користувача {user_name} прійнято")

    elif old_status == "member" and new_status == "restricted":
        print(f"🔒 Користувача {user_name} обмежено")
        
    else:
        print(f"❓ Невідома зміна статусу: {old_status} -> {new_status}")
    
    print("=" * 50)



@router.callback_query(lambda c: c.data == "answers")
async def handle_answers_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "answers_viewed")
    await callback.message.delete()
    await send_answers_message_with_sequence(callback.message)


@router.callback_query(lambda c: c.data == "private_lesson")
async def handle_private_lesson_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "private_lesson_viewed")
    await callback.message.delete()
    await send_private_lesson_message_with_sequence(callback.message)


@router.callback_query(lambda c: c.data == "tariffs")
async def handle_tariffs_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "tariffs_viewed")
    await callback.message.delete()
    await send_tariffs_message_with_sequence(callback.message)


@router.callback_query(lambda c: c.data == "private_lesson_sequence")
async def handle_private_lesson_sequence_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "private_lesson_viewed")
    await callback.message.delete()
    await send_private_lesson_message_with_sequence(callback.message)


@router.callback_query(lambda c: c.data == "tariffs_sequence")
async def handle_tariffs_sequence_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "tariffs_viewed")
    await callback.message.delete()
    await send_tariffs_message_with_sequence(callback.message)


@router.callback_query(lambda c: c.data == "clothes")
async def handle_clothes_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "clothes_tariff_viewed")
    await callback.message.delete()
    await send_clothes_tariff_message(callback.message)


@router.callback_query(lambda c: c.data == "tech")
async def handle_tech_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "tech_tariff_viewed")
    await callback.message.delete()
    await send_tech_tariff_message(callback.message)


@router.callback_query(lambda c: c.data == "pay_clothes")
async def handle_pay_clothes_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "clothes_payment_clicked")
    await callback.message.delete()
    await send_clothes_payment_message(callback.message)


@router.callback_query(lambda c: c.data == "pay_tech")
async def handle_pay_tech_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    update_user_status_by_action(user_id, "tech_payment_clicked")
    await callback.message.delete()
    await send_tech_payment_message(callback.message)







async def on_startup(router):
    me = await bot.get_me()
    create_settings_table()
    create_table()

    create_mailings_table()
    create_recurring_mailings_table()

    create_admin_credentials_table()
    create_start_params_table()

    create_welcome_without_subscription_table()
    create_subscription_messages_table()


    print(f'Bot: @{me.username} запущений!')

async def on_shutdown(router):
    me = await bot.get_me()
    print(f'Bot: @{me.username} зупинений!')

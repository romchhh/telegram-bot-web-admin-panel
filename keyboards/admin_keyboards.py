from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup


def admin_keyboard():
    keyboard = [
        [KeyboardButton(text="Розсилка") ,KeyboardButton(text="Статистика")], 
        [KeyboardButton(text="Вигрузити БД")],
        [KeyboardButton(text="Головне меню")] 
    ]

    keyboard = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    return keyboard


def get_broadcast_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Зробити розсилку", callback_data="create_post")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_post(user_data, user_id, url_buttons=None):
    inline_kb_list = []
    
    if url_buttons:
        for row in url_buttons:
            inline_kb_list.append([
                InlineKeyboardButton(text=button_text, url=button_url) for button_text, button_url in row
            ])

    inline_kb_list.append([
        InlineKeyboardButton(text="Медіа", callback_data=f"media_"),
        InlineKeyboardButton(text="Додати опис", callback_data=f"add_")
    ])

    inline_kb_list.append([
        InlineKeyboardButton(text="🔔" if user_data.get(user_id, {}).get('bell', 0) == 1 else "🔕", callback_data=f"bell_"),
        InlineKeyboardButton(text="URL-кнопки", callback_data=f"url_buttons_")
    ])

    

    inline_kb_list.append([
        InlineKeyboardButton(text="← Відміна", callback_data=f"back_to"),
        InlineKeyboardButton(text="Далі →", callback_data=f"nextmailing_")
    ])

    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def publish_post(user_data, user_id):
    inline_kb_list = [
        [InlineKeyboardButton(text="💈 Опублікувати", callback_data=f"publish_")],
        [InlineKeyboardButton(text="← Назад", callback_data=f"back_to")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def confirm_mailing():
    keyboard = [
        [InlineKeyboardButton(text="✓ Так", callback_data=f"confirm_publish_")],
        [InlineKeyboardButton(text="❌ Ні", callback_data="cancel_publish")]  
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_mailing_keyboard():
    inline_kb_list = [
        [InlineKeyboardButton(text="Назад", callback_data="back_to_my_post")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

def post_keyboard(user_data, user_id, url_buttons=None):
    inline_kb_list = []
    if url_buttons:
        for row in url_buttons:
            inline_kb_list.append([InlineKeyboardButton(text=button_text, url=button_url) for button_text, button_url in row])

    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)



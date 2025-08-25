from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def create_combined_keyboard(inline_buttons, answers_text="💡 Ответы", private_lesson_text="🎓 Приватный урок", tariffs_text="💰 Тарифы", inline_position="below"):
    keyboard_buttons = []
    
    if inline_buttons and isinstance(inline_buttons, list):
        inline_buttons_list = []
        for button in inline_buttons:
            if isinstance(button, dict) and 'text' in button and 'url' in button:
                if button['text'].strip() and button['url'].strip():
                    inline_buttons_list.append([
                        InlineKeyboardButton(text=button['text'].strip(), url=button['url'].strip())
                    ])
        
        if inline_position == "above" and inline_buttons_list:
            keyboard_buttons.extend(inline_buttons_list)
    
    keyboard_buttons.extend([
        [
            InlineKeyboardButton(text=answers_text, callback_data="answers"),
        ],
        [
            InlineKeyboardButton(text=private_lesson_text, callback_data="private_lesson"),
        ],
        [
            InlineKeyboardButton(text=tariffs_text, callback_data="tariffs")
        ]
    ])
    
    if inline_position == "below" and inline_buttons and isinstance(inline_buttons, list):
        inline_buttons_list = []
        for button in inline_buttons:
            if isinstance(button, dict) and 'text' in button and 'url' in button:
                if button['text'].strip() and button['url'].strip():
                    inline_buttons_list.append([
                        InlineKeyboardButton(text=button['text'].strip(), url=button['url'].strip())
                    ])
        
        if inline_buttons_list:
            keyboard_buttons.extend(inline_buttons_list)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_inline_only_keyboard(inline_buttons):
    keyboard_buttons = []
    
    if inline_buttons and isinstance(inline_buttons, list):
        for button in inline_buttons:
            if isinstance(button, dict) and 'text' in button and 'url' in button:
                if button['text'].strip() and button['url'].strip():
                    keyboard_buttons.append([
                        InlineKeyboardButton(text=button['text'].strip(), url=button['url'].strip())
                    ])
    
    # keyboard_buttons.append([
    #     InlineKeyboardButton(
    #         text="⬅️ Назад в главное меню",
    #         callback_data="back_to_start"
    #     )
    # ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)



def create_custom_keyboard(buttons_data):
    keyboard_buttons = []
    
    if buttons_data and isinstance(buttons_data, list):
        for button in buttons_data:
            if isinstance(button, dict) and 'text' in button and 'url' in button:
                if button['text'].strip() and button['url'].strip():
                    keyboard_buttons.append([
                        InlineKeyboardButton(text=button['text'].strip(), url=button['url'].strip())
                    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)



def create_channel_keyboard(channel_url: str, button_text: str = "📢 Подписаться на канал") -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=button_text, url=channel_url)
        ]
    ])
    return keyboard


def create_captcha_keyboard(button_text: str = "Я не робот") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=button_text)]],
        resize_keyboard=True,
        one_time_keyboard=True 
    )
    return keyboard


def get_subscription_message_keyboard(subscription_message: dict = None) -> InlineKeyboardMarkup:
    if not subscription_message:
        return None
    
    keyboard_buttons = []
    
    if subscription_message.get('inline_buttons') and isinstance(subscription_message['inline_buttons'], list):
        for button in subscription_message['inline_buttons']:
            if isinstance(button, dict) and 'text' in button and 'url' in button:
                if button['text'].strip() and button['url'].strip():
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text=button['text'].strip(),
                            url=button['url'].strip()
                        )
                    ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад в главное меню",
            callback_data="back_to_start"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
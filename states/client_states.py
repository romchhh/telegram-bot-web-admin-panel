from aiogram.fsm.state import State, StatesGroup

class MediaStates(StatesGroup):
    waiting_for_media = State()


class CaptchaStates(StatesGroup):
    waiting_for_channel_request = State()
    waiting_for_captcha = State()
    captcha_sent = State()
    captcha_verified = State()

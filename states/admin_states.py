from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
    
class Mailing(StatesGroup):
    content = State()
    media = State()
    description = State()
    url_buttons = State()
    
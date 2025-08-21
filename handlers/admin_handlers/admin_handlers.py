from aiogram import Router, types
from config import administrators
from main import bot
from utils.filters import IsAdmin
from aiogram.fsm.context import FSMContext
from keyboards.admin_keyboards import admin_keyboard
from database.admin_db import get_users_count, get_all_user_ids
import pandas as pd


router = Router()


@router.message(IsAdmin(), lambda message: message.text == "Адмін панель 💻" or message.text == "/admin")
async def admin_panel(message: types.Message):
    user_id = message.from_user.id
    if user_id in administrators:
        await message.answer("Вітаю в адмін панелі. Ось ваші доступні опції.", reply_markup=admin_keyboard())
    
    

@router.message(IsAdmin(), lambda message: message.text == "Статистика")
async def statistic_handler(message: types.Message):
    total_users = get_users_count()
    response_message = (
            "<b>СТАТИСТИКА</b>\n\n"
            f"👥 Загальна кількість активних користувачів: {total_users}\n"
            f"✔️ Загальна кількість користувачів які надали дані для запису: {total_users}\n"
        )
    await message.answer(response_message, parse_mode="HTML")
  
        
@router.message(IsAdmin(), lambda message: message.text == "Вигрузити БД")
async def export_database(message: types.Message):
    response_message = (
            "<b>ВИГРУЗКА БАЗИ ДАНИХ</b>\n\n"
            f"Зачекайте поки ми сформуємо ексель файл з базою даних"
        )
    await message.answer(response_message, parse_mode="HTML")
    
    # Отримуємо дані користувачів через функцію
    from database.client_db import get_all_users
    users_data = get_all_users()
    
    # Створюємо DataFrame
    users_df = pd.DataFrame(users_data, columns=['user_id', 'user_name', 'join_date', 'last_activity'])

    with pd.ExcelWriter('database_export.xlsx', engine='openpyxl') as writer:
        users_df.to_excel(writer, sheet_name='Users', index=False)

    with open('database_export.xlsx', 'rb') as file:
        await bot.send_document(message.chat.id, file, caption="База даних користувачів")
        

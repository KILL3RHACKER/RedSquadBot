import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# Инициализация бота и диспетчера
API_TOKEN = '6787350410:AAH9tW6iOB3v93jcbJTF4uvXexaJW8frwHQ'
ADMIN_CHAT_ID = '1143388721'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определение состояний
class Form(StatesGroup):
    question1 = State()
    question2 = State()
    question3 = State()
    change_balance = State()

def is_user_approved(user_id):
    try:
        with open('True.txt', 'r') as f:
            approved_users = f.read().splitlines()
        return str(user_id) in approved_users
    except FileNotFoundError:
        return False

def is_user_rejected(user_id):
    try:
        with open('False.txt', 'r') as f:
            rejected_users = f.read().splitlines()
        return str(user_id) in rejected_users
    except FileNotFoundError:
        return False

def is_application_sent(user_id):
    try:
        with open('Applications.txt', 'r') as f:
            applied_users = f.read().splitlines()
        return str(user_id) in applied_users
    except FileNotFoundError:
        return False

def save_approval_date(user_id):
    date_approved = datetime.now().strftime("%Y-%m-%d")
    with open('Dates.txt', 'a') as f:
        f.write(f"{user_id} {date_approved}\n")

def get_days_in_team(user_id):
    try:
        with open('Dates.txt', 'r') as f:
            lines = f.readlines()
        for line in lines:
            saved_user_id, date_approved = line.strip().split()
            if int(saved_user_id) == user_id:
                date_approved = datetime.strptime(date_approved, "%Y-%m-%d")
                return (datetime.now() - date_approved).days
        return 0
    except FileNotFoundError:
        return 0

def get_balance(username):
    try:
        with open('balance.txt', 'r') as f:
            lines = f.readlines()
        for line in lines:
            saved_username, balance = line.strip().split()
            if saved_username == username:
                return balance
        return "0"
    except FileNotFoundError:
        return "0"

def update_balance(username, new_balance):
    lines = []
    try:
        with open('balance.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass

    with open('balance.txt', 'w') as f:
        found = False
        for line in lines:
            saved_username, balance = line.strip().split()
            if saved_username == username:
                f.write(f"{username} {new_balance}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{username} {new_balance}\n")

def save_user(username, user_id):
    with open('User.txt', 'a') as f:
        f.write(f"{username} {user_id}\n")

def get_username_by_id(user_id):
    try:
        with open('User.txt', 'r') as f:
            lines = f.readlines()
        for line in lines:
            saved_username, saved_user_id = line.strip().split()
            if int(saved_user_id) == user_id:
                return saved_username
        return None
    except FileNotFoundError:
        return None

# Начало диалога
@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    if is_user_approved(message.from_user.id):
        await show_menu(message)
    elif is_user_rejected(message.from_user.id):
        await message.answer("Ваша заявка была отклонена.")
    elif is_application_sent(message.from_user.id):
        await message.answer("Вы уже отправили заявку. Ожидайте решения.")
    else:
        with open('Applications.txt', 'a') as f:
            f.write(f"{message.from_user.id}\n")
        await Form.question1.set()
        await message.answer("Откуда вы о нас узнали?")

# Проверка ключевых слов для не одобренных пользователей
@dp.message_handler(lambda message: not is_user_approved(message.from_user.id) and message.text in ['👨Профиль', '💬Чаты', '✉️Поддержка'], state='*')
async def not_approved_keyword(message: types.Message):
    await message.answer("Вы не имеете прав для выполнения этой команды. Пожалуйста, отправьте заявку с помощью команды /start.")

# Первый вопрос
@dp.message_handler(state=Form.question1)
async def process_question1(message: types.Message, state: FSMContext):
    await state.update_data(question1=message.text)
    await Form.next()
    await message.answer("Есть ли у вас опыт в данной сфере?")

# Второй вопрос
@dp.message_handler(state=Form.question2)
async def process_question2(message: types.Message, state: FSMContext):
    await state.update_data(question2=message.text)
    await Form.next()
    await message.answer("Сколько времени готовы уделять работе?")

# Третий вопрос и отправка администратору
@dp.message_handler(state=Form.question3)
async def process_question3(message: types.Message, state: FSMContext):
    await state.update_data(question3=message.text)
    user_data = await state.get_data()
    
    # Формирование сообщения для администратора
    admin_message = f"Новая заявка от {message.from_user.full_name} (@{message.from_user.username}):\n\n"
    admin_message += f"1. Откуда узнали: {user_data['question1']}\n"
    admin_message += f"2. Опыт в сфере: {user_data['question2']}\n"
    admin_message += f"3. Время для работы: {user_data['question3']}\n"
    
    # Кнопки для принятия или отклонения заявки
    inline_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton('Принять✅', callback_data=f'accept_{message.from_user.id}_{message.from_user.username}'),
        InlineKeyboardButton('Отклонить❎', callback_data=f'reject_{message.from_user.id}')
    )
    
    await bot.send_message(ADMIN_CHAT_ID, admin_message, reply_markup=inline_kb)
    await message.answer("Ваша заявка отправлена на рассмотрение. Ожидайте решения.")
    await state.finish()

# Обработка ответа администратора
@dp.callback_query_handler(lambda c: c.data and c.data.startswith(('accept_', 'reject_')))
async def process_callback(callback_query: types.CallbackQuery):
    action, user_id, *username_parts = callback_query.data.split('_')
    user_id = int(user_id)
    username = '_'.join(username_parts)  # Join parts of the username in case it contains underscores
    message_id = callback_query.message.message_id
    
    if action == 'accept':
        with open('True.txt', 'a') as f:
            f.write(f"{user_id}\n")
        save_user(username, user_id)
        save_approval_date(user_id)
        await bot.send_message(user_id, "Ваша заявка принята!")
        await bot.edit_message_text("Заявка принята", chat_id=ADMIN_CHAT_ID, message_id=message_id)
    elif action == 'reject':
        with open('False.txt', 'a') as f:
            f.write(f"{user_id}\n")
        await bot.send_message(user_id, "Ваша заявка отклонена.")
        await bot.edit_message_text("Заявка отклонена", chat_id=ADMIN_CHAT_ID, message_id=message_id)
    
    await callback_query.answer("Решение принято.")

# Меню
async def show_menu(message: types.Message):
    profile_button = KeyboardButton('👨Профиль')
    chats_button = KeyboardButton('💬Чаты')
    support_button = KeyboardButton('✉️Поддержка')
    if message.from_user.id == int(ADMIN_CHAT_ID):
        admin_button = KeyboardButton('Админ')
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add(profile_button, chats_button, support_button, admin_button)
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add(profile_button, chats_button, support_button)
    await message.answer("Меню", reply_markup=markup)

@dp.message_handler(lambda message: message.text == '👨Профиль')
async def cmd_profile(message: types.Message):
    if not is_user_approved(message.from_user.id):
        await message.answer("Вы не имеете прав для выполнения этой команды. Пожалуйста, отправьте заявку с помощью команды /start.")
        return
    
    days_in_team = get_days_in_team(message.from_user.id)
    balance = get_balance(message.from_user.username)
    
    profile_info = f"Ник: {message.from_user.full_name}\nДней в Тиме: {days_in_team}\nБаланс в рублях: {balance}"
    await message.answer(profile_info)

# 💬Чаты
@dp.message_handler(lambda message: message.text == '💬Чаты')
async def cmd_chats(message: types.Message):
    if not is_user_approved(message.from_user.id):
        await message.answer("Вы не имеете прав для выполнения этой команды. Пожалуйста, отправьте заявку с помощью команды /start.")
        return
    
    inline_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton('Основной чат', url='https://t.me/+y-78W8kD2Cg3Y2Zi'),
        InlineKeyboardButton('Выплаты', url='https://t.me/profitmoneyo')
    )
    await message.answer("💬Чаты", reply_markup=inline_kb)

# ✉️Поддержка
@dp.message_handler(lambda message: message.text == '✉️Поддержка')
async def cmd_support(message: types.Message):
    if not is_user_approved(message.from_user.id):
        await message.answer("Вы не имеете прав для выполнения этой команды. Пожалуйста, отправьте заявку с помощью команды /start.")
        return
    
    await message.answer("Для поддержки свяжитесь с @OxWorldik1337")

# Админ панель
@dp.message_handler(lambda message: message.text == 'Админ' and message.from_user.id == int(ADMIN_CHAT_ID))
async def cmd_admin(message: types.Message):
    await Form.change_balance.set()
    await message.answer("Введите данные для изменения баланса в формате: username новая_сумма")

@dp.message_handler(state=Form.change_balance)
async def process_change_balance(message: types.Message, state: FSMContext):
    try:
        username, new_balance = message.text.split()
        new_balance = float(new_balance)
        
        user_id = get_user_id_by_username(username)
        if not user_id:
            await message.answer("Пользователь с таким username не найден в User.txt.")
            await state.finish()
            return
        
        update_balance(username, new_balance)
        await message.answer(f"Баланс пользователя с username {username} успешно обновлен до {new_balance} рублей.")
    except ValueError:
        await message.answer("Пожалуйста, введите данные в правильном формате: username новая_сумма")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")
    finally:
        await state.finish()

def get_user_id_by_username(username):
    try:
        with open('User.txt', 'r') as f:
            lines = f.readlines()
        for line in lines:
            saved_username, saved_user_id = line.strip().split()
            if saved_username == username:
                return int(saved_user_id)
        return None
    except FileNotFoundError:
        return None

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
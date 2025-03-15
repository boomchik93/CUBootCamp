import os
import random
import string
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import db

SUBJECTS = {
    'russian': '📚 Русский язык',
    'math': '📘 Математика',
    'informatics': '🖥 Информатика',
    'biology': '🍀 Биология',
    'geography': '🌏 География'
}

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT"))
ADMIN_CHAT_LINK = os.getenv("ADMIN_LIMK")
if not BOT_TOKEN:
    raise ValueError("Токен не найден! Проверьте .env файл.")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


class TicketCreatingStates(StatesGroup):
    waiting_for_ticket_subject = State()
    done = State()


class RegistrationStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_grade = State()
    waiting_for_subject = State()
    waiting_for_teacher_code = State()


@dp.message(Command("reregister"))
async def command_reregister(message: types.Message, state: FSMContext):
    await state.clear()

    username = message.from_user.username or str(message.from_user.id)
    user_info = db.get_user_status(username)

    if user_info:
        role = user_info['role']
        if role == 'student':
            db.delete_student(username)
        elif role == 'cooteacher':
            db.delete_cooteacher(username)
        elif role == 'teacher':
            db.delete_teacher(username)
        await message.answer("♻️ Начинаем процесс перерегистрации...")
        await send_welcome(message)
    else:
        await message.answer("‼️ Вы еще не зарегистрированы. Используйте /start.")


@dp.callback_query(RegistrationStates.waiting_for_role)
async def process_role(callback_query: types.CallbackQuery, state: FSMContext):
    role = callback_query.data
    await state.update_data(role=role)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"subject_{key}")]
        for key, name in SUBJECTS.items()
    ])

    if role in ['role_teacher', 'role_cooteacher']:
        await callback_query.message.answer("📚 Выберите ваш предмет:", reply_markup=keyboard)
        await state.set_state(RegistrationStates.waiting_for_subject)
    elif role == 'role_student':
        await callback_query.message.answer("🔢 Введите ваш класс:")
        await state.set_state(RegistrationStates.waiting_for_grade)


@dp.message(RegistrationStates.waiting_for_grade)
async def process_grade(message: types.Message, state: FSMContext):
    data = await state.get_data()
    username = data.get('username')
    if not username:
        username = message.from_user.username or str(message.from_user.id)
        await state.update_data(username=username)

    required_fields = ['first_name', 'second_name', 'phone_num']
    for field in required_fields:
        if field not in data:
            return await message.answer("❌ Ошибка регистрации. Пожалуйста, начните заново /start")

    try:
        grade = int(message.text)
        db.add_student(
            username=username,
            first_name=data['first_name'],
            second_name=data['second_name'],
            phone_num=data['phone_num'],
            grade=grade
        )
        await message.answer("✅ Регистрация завершена!", reply_markup=types.ReplyKeyboardRemove())
        await show_student_menu(message)
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат класса. Введите число, например: 9")


@dp.callback_query(RegistrationStates.waiting_for_subject)
async def process_subject(callback_query: types.CallbackQuery, state: FSMContext):
    subject_key = callback_query.data.replace('subject_', '')
    if subject_key not in SUBJECTS:
        await callback_query.message.answer("❌ Неверный предмет, попробуйте снова!")
        return

    subject_name = SUBJECTS[subject_key]
    await state.update_data(subject=subject_name)
    data = await state.get_data()

    if data['role'] == 'role_teacher':
        db.add_teacher(
            username=data['username'],
            first_name=data['first_name'],
            last_name=data.get('second_name', ''),
            phone_num=data['phone_num'],
            subject=subject_name
        )
        await callback_query.message.answer("✅ Регистрация завершена!")
        await show_teacher_menu(callback_query.message)
        await state.clear()

    elif data['role'] == 'role_cooteacher':
        cancel_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback_query.message.answer("🔢 Введите код учителя:", reply_markup=cancel_keyboard)
        await state.set_state(RegistrationStates.waiting_for_teacher_code)


@dp.callback_query(RegistrationStates.waiting_for_teacher_code)
async def cancel_teacher_code(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "cancel_code":
        await state.clear()
        await callback_query.message.answer("🚫 Ввод кодового шифра отменен.")


@dp.message(RegistrationStates.waiting_for_teacher_code)
async def process_teacher_code(message: types.Message, state: FSMContext):
    if message.text.strip() == "❌ Отмена":
        await message.answer("❌ Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        await ask_for_role(message, state)
        return

    code = message.text.strip().upper()
    code_info = db.get_teacher_code_info(code)
    data = await state.get_data()

    if not code_info:
        return await message.answer("❌ Неверный код")
    if code_info['used']:
        return await message.answer("⚠️ Код уже использован")
    if code_info['subject'] != data.get('subject'):
        return await message.answer(f"🚫 Код предназначен для предмета: {code_info['subject']}")

    try:
        db.mark_code_as_used(code)
        db.add_cooteacher(
            data['username'],
            data['first_name'],
            data['second_name'],
            data['phone_num'],
            int(data['grade']),
            data['subject']
        )
        await message.answer(f"✅ Регистрация успешна!\nСсылка для чата экспертов: {ADMIN_CHAT_LINK}",
                             reply_markup=types.ReplyKeyboardRemove())
        await show_cooteacher_menu(message)
    except Exception as e:
        await message.answer("❌ Ошибка регистрации")
    finally:
        await state.clear()


def generate_unique_code():
    characters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(characters) for _ in range(5))
    return code


@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="☎️ Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("👋 Привет! Для начала работы поделись своим контактом.", reply_markup=keyboard)


@dp.message(lambda message: message.contact is not None)
async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    user_data = {
        'username': message.from_user.username or str(message.contact.user_id),
        'first_name': contact.first_name,
        'second_name': contact.last_name or "",
        'phone_num': contact.phone_number
    }

    await state.update_data(**user_data)

    user_info = db.get_user_status(user_data['username'])
    if user_info:
        await show_profile_by_role(message, user_info)
    else:
        await ask_for_role(message, state)


async def show_profile_by_role(message: types.Message, user_info: dict):
    role = user_info['role']
    data = user_info['data']

    if role == 'student':
        await show_student_profile(message, data)
    elif role == 'cooteacher':
        await show_cooteacher_profile(message, data)
    elif role == 'teacher':
        await show_teacher_profile(message, data)
    else:
        await message.answer("❌ Неизвестный тип пользователя")


async def ask_for_role(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧑🎓 Я ученик", callback_data="role_student")],
        [InlineKeyboardButton(text="🧑🔬 Я помощник учителя", callback_data="role_cooteacher")],
        [InlineKeyboardButton(text="🧑🏫 Я учитель", callback_data="role_teacher")]
    ])
    await message.answer("🦺 Выберите вашу роль:", reply_markup=keyboard)
    await state.set_state(RegistrationStates.waiting_for_role)


@dp.message(Command("reregister"))
async def command_reregister(message: types.Message, state: FSMContext):
    username = message.from_user.username or str(message.from_user.id)
    user_info = db.get_user_status(username)

    if user_info:
        role = user_info['role']
        if role == 'student':
            db.delete_student(username)
        elif role == 'cooteacher':
            db.delete_cooteacher(username)
        elif role == 'teacher':
            db.delete_teacher(username)
        await message.answer("♻️ Начинаем процесс перерегистрации...")
        await send_welcome(message)
    else:
        await message.answer("‼️ Вы еще не зарегистрированы. Используйте /start.")


async def show_student_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨🦰 Аккаунт"), KeyboardButton(text="✍️ Оставить запрос")]
        ],
        resize_keyboard=True
    )
    await message.answer("📋 Меню ученика:", reply_markup=keyboard)


async def show_cooteacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Список активных запросов"), KeyboardButton(text="👨🦰 Аккаунт")]
        ],
        resize_keyboard=True
    )
    await message.answer("🧑🔬 Меню помощника учителя:", reply_markup=keyboard)


async def show_teacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔢 Создать уникальный код"), KeyboardButton(text="👨🦰 Аккаунт")]
        ],
        resize_keyboard=True
    )
    await message.answer("🧑🏫 Меню учителя:", reply_markup=keyboard)


@dp.message(lambda message: message.text == "👨🦰 Аккаунт")
async def handle_account(message: types.Message):
    username = message.from_user.username or str(message.from_user.id)
    user_info = db.get_user_status(username)

    if not user_info:
        return await message.answer("❌ Пользователь не найден!")

    role_translation = {
        'student': 'Ученик',
        'teacher': 'Учитель',
        'cooteacher': 'Помощник учителя'
    }

    data = user_info['data']
    role = role_translation.get(user_info['role'], 'Неизвестная роль')

    response = "👤 <b>Ваш профиль:</b>\n"
    response += f"▫️ <b>Роль:</b> {role}\n"
    response += f"▫️ <b>Имя:</b> {data.get('first_name', 'не указано')}\n"
    response += f"▫️ <b>Фамилия:</b> {data.get('second_name', data.get('last_name', 'не указана'))}\n"
    response += f"▫️ <b>Телефон:</b> {data.get('phone_num', 'не указан')}\n"

    if user_info['role'] in ['student', 'cooteacher']:
        response += f"▫️ <b>Класс:</b> {data.get('grade', 'не указан')}\n"

    if user_info['role'] in ['teacher', 'cooteacher']:
        response += f"▫️ <b>Предмет:</b> {data.get('subject', 'не указан')}"

    await message.answer(response, parse_mode=ParseMode.HTML)


async def show_student_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨🦰 Аккаунт"), KeyboardButton(text="✍️ Оставить запрос")],
        ],
        resize_keyboard=True
    )
    await message.answer("📋 Меню ученика:", reply_markup=keyboard)


async def show_cooteacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Список активных запросов"), KeyboardButton(text="👨🦰 Аккаунт")],
        ],
        resize_keyboard=True
    )
    await message.answer("🧑🔬 Меню помощника учителя:", reply_markup=keyboard)


async def show_teacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔢 Создать уникальный код"), KeyboardButton(text="👨🦰 Аккаунт")],
        ],
        resize_keyboard=True
    )
    await message.answer("🧑🏫 Меню учителя:", reply_markup=keyboard)


@dp.message(lambda message: message.text == "🔢 Создать уникальный код")
async def handle_generate_code(message: types.Message):
    username = message.from_user.username or str(message.from_user.id)
    teacher_info = db.get_user_status(username)

    if not teacher_info or teacher_info['role'] != 'teacher':
        await message.answer("‼️ Только учителя могут создавать коды!")
        return

    code = generate_unique_code()
    db.add_teacher_code(
        teacher_id=teacher_info['data']['id'],
        code=code,
        subject=teacher_info['data']['subject']
    )
    await message.answer(f"✅ Новый код для предмета {teacher_info['data']['subject']}:\n<code>{code}</code>")


@dp.message(lambda message: message.text == "✍️ Оставить запрос")
async def handle_ticket(message: types.Message, state: FSMContext):
    await state.set_state(TicketCreatingStates.waiting_for_ticket_subject)
    await message.answer("✍️ Напишите свой вопрос:")


@dp.message(TicketCreatingStates.waiting_for_ticket_subject)
async def process_ticket_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    data = await state.get_data()
    ticket = f"""
    ❓ Вопрос от пользователя: {message.from_user.id}
    Сообщение: {data["subject"]}
    """
    await bot.send_message(ADMIN_CHAT_ID, ticket)
    await state.clear()
    await message.answer("✅ Ваш запрос отправлен экспертам!")


@dp.message(lambda message: message.chat.id == ADMIN_CHAT_ID)
async def handle_admin_group(message: types.Message):
    if message.reply_to_message:
        try:
            original_message = message.reply_to_message.text
            ticket_id = int(original_message.split("пользователя: ")[1].split("\n")[0].strip())

            await bot.send_message(
                chat_id=ticket_id,
                text=f"📨 Ответ от эксперта:\n{message.text}"
            )
            await message.answer("✅ Ответ успешно отправлен!")
        except Exception as e:
            print(f"Error processing admin reply: {e}")


async def show_student_profile(message: types.Message, data):
    await show_student_menu(message)


async def show_cooteacher_profile(message: types.Message, data):
    await show_cooteacher_menu(message)


async def show_teacher_profile(message: types.Message, data):
    await show_teacher_menu(message)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        db.init_db()
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен!')

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
    'russian': 'Русский язык',
    'math': 'Математика',
    'informatics': 'Информатика',
    'biology': 'Биология',
    'geography': 'География'
}

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT")
ADMIN_CHAT_LINK = os.getenv("ADMIN_LIMK")
if not BOT_TOKEN:
    raise ValueError("Токен не найден! Проверьте .env файл.")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


class RegistrationStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_grade = State()
    waiting_for_subject = State()


class TicketCreatingStates(StatesGroup):
    waiting_for_ticket_subject = State()
    done = State()


class RegistrationStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_grade = State()
    waiting_for_subject = State()
    waiting_for_teacher_code = State()


@dp.callback_query(RegistrationStates.waiting_for_role)
@dp.callback_query(RegistrationStates.waiting_for_role)
async def process_role(callback_query: types.CallbackQuery, state: FSMContext):
    role = callback_query.data
    await state.update_data(role=role)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"subject_{key}")]
        for key, name in SUBJECTS.items()
    ])

    if role in ['role_teacher', 'role_cooteacher']:
        await callback_query.message.answer("Выберите ваш предмет:", reply_markup=keyboard)
        await state.set_state(RegistrationStates.waiting_for_subject)
    elif role == 'role_student':
        await callback_query.message.answer("Введите ваш класс:")
        await state.set_state(RegistrationStates.waiting_for_grade)


@dp.message(RegistrationStates.waiting_for_grade)
async def process_grade(message: types.Message, state: FSMContext):
    await state.update_data(grade=int(message.text))
    data = await state.get_data()
    if data['role'] == 'role_student':
        db.add_student(data['username'], data['first_name'], data['second_name'], data['phone_num'], data['grade'])
        await message.answer("Регистрация завершена!")
        await show_student_menu(message)
        await state.clear()
    elif data['role'] == 'role_cooteacher':
        await message.answer("Введите ваш предмет:")
        await state.set_state(RegistrationStates.waiting_for_subject)


@dp.message(RegistrationStates.waiting_for_subject)
@dp.callback_query(RegistrationStates.waiting_for_subject)
async def process_subject(callback_query: types.CallbackQuery, state: FSMContext):
    subject_key = callback_query.data.replace('subject_', '')
    if subject_key not in SUBJECTS:
        await callback_query.message.answer("Неверный предмет, попробуйте снова!")
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
        await callback_query.message.answer("Регистрация завершена!")
        await show_teacher_menu(callback_query.message)
        await state.clear()

    elif data['role'] == 'role_cooteacher':
        await callback_query.message.answer("Введите код учителя:")
        await state.set_state(RegistrationStates.waiting_for_teacher_code)


@dp.message(RegistrationStates.waiting_for_teacher_code)
async def process_teacher_code(message: types.Message, state: FSMContext):
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
        await message.answer(f"✅ Регистрация успешна!\nСсылка для чата экспертов: {ADMIN_CHAT_LINK}")
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
            [KeyboardButton(text="Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Привет! Для начала работы поделись своим контактом.", reply_markup=keyboard)


@dp.message(lambda message: message.contact is not None)
async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    username = message.from_user.username if message.from_user.username else contact.phone_number
    first_name = contact.first_name
    user_info = db.get_user_status(username)
    second_name = contact.last_name if contact.last_name else ""
    if user_info:
        role = user_info['role']
        if role == 'student':
            await show_student_profile(message, user_info['data'])
        elif role == 'cooteacher':
            await show_cooteacher_profile(message, user_info['data'])
        elif role == 'teacher':
            await show_teacher_profile(message, user_info['data'])
    else:
        await state.update_data(
            username=username,
            first_name=first_name,
            second_name=second_name,
            phone_num=contact.phone_number
        )

    user_info = db.get_user_status(username)
    if user_info:
        role = user_info['role']
        if role == 'student':
            await show_student_profile(message, user_info['data'])
        elif role == 'cooteacher':
            await show_cooteacher_profile(message, user_info['data'])
        elif role == 'teacher':
            await show_teacher_profile(message, user_info['data'])
    else:
        await message.answer("Вы не зарегистрированы в системе. Давайте зарегистрируем вас!")
        await ask_for_role(message, state)


async def ask_for_role(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я ученик", callback_data="role_student")],
        [InlineKeyboardButton(text="Я помощник учителя", callback_data="role_cooteacher")],
        [InlineKeyboardButton(text="Я учитель", callback_data="role_teacher")]
    ])
    await message.answer("Выберите вашу роль:", reply_markup=keyboard)
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
        await message.answer("Начинаем процесс перерегистрации...")
        await ask_for_role(message, state)
    else:
        await message.answer("Вы еще не зарегистрированы. Используйте /start.")


async def show_student_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Аккаунт"), KeyboardButton(text="Сменить роль")],
            [KeyboardButton(text="Оставить запрос")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню ученика:", reply_markup=keyboard)


async def show_cooteacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список активных запросов"), KeyboardButton(text="Сменить роль")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню помощника учителя:", reply_markup=keyboard)


async def show_teacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать уникальный код"), KeyboardButton(text="Сменить роль")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню учителя:", reply_markup=keyboard)


@dp.message(lambda message: message.text == "Сменить роль")
async def handle_change_role(message: types.Message, state: FSMContext):
    await command_reregister(message, state)


@dp.callback_query(RegistrationStates.waiting_for_role)
async def process_role(callback_query: types.CallbackQuery, state: FSMContext):
    role = callback_query.data
    await state.update_data(role=role)
    data = await state.get_data()

    if role == 'role_student':
        await callback_query.message.answer("Введите ваш класс:")
        await state.set_state(RegistrationStates.waiting_for_grade)
    elif role == 'role_cooteacher':
        await callback_query.message.answer("Введите ваш класс:")
        await state.set_state(RegistrationStates.waiting_for_grade)
    elif role == 'role_teacher':
        await callback_query.message.answer("Введите ваш предмет:")
        await state.set_state(RegistrationStates.waiting_for_subject)


@dp.message(RegistrationStates.waiting_for_teacher_code)
async def process_teacher_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    code_info = db.get_teacher_code_info(code)
    data = await state.get_data()

    if not code_info:
        await message.answer("Неверный код. Попробуйте снова.")
        return

    if code_info['used']:
        await message.answer("Этот код уже использован. Попробуйте снова.")
        return

    if code_info['subject'] != data['subject']:
        await message.answer("Код не соответствует выбранному предмету. Попробуйте снова.")
        return

    db.add_cooteacher(
        data['username'], data['first_name'], data['second_name'], data['phone_num'], data['grade'], data['subject']
    )
    db.mark_code_as_used(code)
    await message.answer("Регистрация завершена!")
    await show_cooteacher_menu(message)
    await state.clear()


@dp.message(RegistrationStates.waiting_for_grade)
async def process_grade(message: types.Message, state: FSMContext):
    await state.update_data(grade=int(message.text))
    data = await state.get_data()
    if data['role'] == 'role_student':
        db.add_student(data['username'], data['first_name'], data['second_name'], data['phone_num'], data['grade'])
        await message.answer("Регистрация завершена!")
        await show_student_menu(message)
        await state.clear()
    elif data['role'] == 'role_cooteacher':
        await message.answer("Введите ваш предмет:")
        await state.set_state(RegistrationStates.waiting_for_subject)


@dp.message(RegistrationStates.waiting_for_subject)
async def process_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    data = await state.get_data()
    if data['role'] == 'role_cooteacher':
        db.add_cooteacher(data['username'], data['first_name'], data['second_name'], data['phone_num'], data['grade'],
                          data['subject'])
        await message.answer("Регистрация завершена!")
        await show_cooteacher_menu(message)
        await state.clear()
    elif data['role'] == 'role_teacher':
        db.add_teacher(data['username'], data['first_name'], data['second_name'], data['phone_num'], data['subject'])
        await message.answer("Регистрация завершена!")
        await show_teacher_menu(message)
        await state.clear()


async def show_student_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Аккаунт")],
            [KeyboardButton(text="Оставить запрос")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню ученика:", reply_markup=keyboard)


async def show_cooteacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Список активных запросов")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню помощника учителя:", reply_markup=keyboard)


async def show_teacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать уникальный код")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню учителя:", reply_markup=keyboard)


@dp.message(lambda message: message.text == "Создать уникальный код")
@dp.message(lambda message: message.text == "Создать уникальный код")
async def handle_generate_code(message: types.Message):
    username = message.from_user.username or str(message.from_user.id)
    teacher_info = db.get_user_status(username)

    if not teacher_info or teacher_info['role'] != 'teacher':
        await message.answer("Только учителя могут создавать коды!")
        return

    code = generate_unique_code()
    db.add_teacher_code(
        teacher_id=teacher_info['data']['id'],
        code=code,
        subject=teacher_info['data']['subject']
    )
    await message.answer(f"✅ Новый код для предмета {teacher_info['data']['subject']}:\n<code>{code}</code>")


@dp.message(lambda message: message.text == "Оставить запрос")
async def handle_ticket(message: types.Message, state: FSMContext):
    await state.set_state(TicketCreatingStates.waiting_for_ticket_subject)
    await message.answer(f"Напишите свой вопрос:")


@dp.message(TicketCreatingStates.waiting_for_ticket_subject)
async def process_ticket_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    data = await state.get_data()
    ticket = f"""
Тикет: {message.from_user.id}
Сообщение: {data["subject"]}
    """
    await state.set_state(TicketCreatingStates.done)
    await bot.send_message(ADMIN_CHAT_ID, ticket)


@dp.message(lambda message: message.chat.id == ADMIN_CHAT_ID)
async def handle_admin_group(message: types.Message):
    m = message.reply_to_message.text
    try:
        ticket_id = int(m.split("\n")[0][len("Тикет:") + 1:])
        await bot.send_message(ticket_id, message.text)
    except:
        pass


@dp.message(lambda message: message.text.isupper() and len(message.text) == 5)
async def handle_code_usage(message: types.Message):
    try:
        code = message.text.strip().upper()
        code_info = db.get_teacher_code_info(code)

        if not code_info:
            return await message.answer("❌ Неверный код")

        if code_info['used']:
            return await message.answer("⚠️ Этот код уже использован")

        user_info = db.get_user_status(message.from_user.username)
        if code_info['subject'] != user_info['data']['subject']:
            return await message.answer(f"🚫 Код предназначен для другого предмета")

        db.mark_code_as_used(code)
        await message.answer("✅ Код успешно активирован!")

    except Exception as e:
        print(f"Ошибка при активации кода: {e}")
        await message.answer("🚫 Произошла ошибка при обработке кода")


async def show_student_profile(message: types.Message, data):
    response = f"Имя: {data['first_name']} {data['second_name']}\nТелефон: {data['phone_num']}\nКласс: {data['grade']}"
    await message.answer(response)
    await show_student_menu(message)


async def show_cooteacher_profile(message: types.Message, data):
    response = f"Имя: {data['first_name']} {data['second_name']}\nТелефон: {data['phone_num']}\nКласс: {data['grade']}\nПредмет: {data['subject']}"
    await message.answer(response)
    await show_cooteacher_menu(message)


async def show_teacher_profile(message: types.Message, data):
    response = f"Имя: {data['first_name']} {data['last_name']}\nТелефон: {data['phone_num']}\nПредмет: {data['subject']}"
    await message.answer(response)
    await show_teacher_menu(message)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        db.init_db()
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен!')

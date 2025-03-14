import os
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
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


from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_grade = State()
    waiting_for_subject = State()
    waiting_for_teacher_code = State()


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
        await message.answer("Введите код учителя по этому предмету:")
        await state.set_state(RegistrationStates.waiting_for_teacher_code)
    elif data['role'] == 'role_teacher':
        db.add_teacher(data['username'], data['first_name'], data['second_name'], data['phone_num'], data['subject'])
        await message.answer("Регистрация завершена!")
        await show_teacher_menu(message)
        await state.clear()


@dp.message(RegistrationStates.waiting_for_teacher_code)
async def process_teacher_code(message: types.Message, state: FSMContext):
    code = message.text
    code_info = db.get_teacher_code_info(code)
    data = await state.get_data()

    if code_info and code_info['subject'] == data['subject'] and not code_info['used']:
        db.add_cooteacher(data['username'], data['first_name'], data['second_name'], data['phone_num'], data['grade'],
                          data['subject'])
        db.mark_code_as_used(code)
        await message.answer("Регистрация завершена!")
        await show_cooteacher_menu(message)
        await state.clear()
    else:
        await message.answer("Неверный код или код уже использован. Попробуйте снова.")


def generate_unique_code():
    characters = string.ascii_uppercase + string.digits  # A-Z и 0-9
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
    second_name = contact.last_name if contact.last_name else ""
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
async def handle_generate_code(message: types.Message):
    code = generate_unique_code()
    db.add_teacher_code(message.from_user.id, code)
    await message.answer(f"Ваш уникальный код: {code}")


@dp.message(lambda message: message.text.isupper() and len(message.text) == 5)
async def handle_code_usage(message: types.Message):
    code = message.text
    code_info = db.get_code_info(code)
    if code_info:
        if code_info['used']:
            await message.answer("Этот код уже использован.")
        else:
            db.mark_code_as_used(code)
            await message.answer("Код успешно активирован!")
    else:
        await message.answer("Неверный код.")


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
    import asyncio

    db.init_db()
    asyncio.run(main())

import os
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
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
    waiting_for_description = State()


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


async def show_student_profile(message: types.Message, data):
    response = f"Имя: {data['first_name']} {data['second_name']}\nТелефон: {data['phone_num']}\nКласс: {data['grade']}"
    await message.answer(response)
    await show_student_menu(message)


@dp.message(lambda message: message.text == "Аккаунт")
async def handle_student_account(message: types.Message):
    user_info = db.get_student_info(message.from_user.username)
    if user_info:
        await show_student_profile(message, user_info)
    else:
        await message.answer("Информация о вас не найдена.")


@dp.message(lambda message: message.text == "Оставить запрос")
async def handle_create_request(message: types.Message, state: FSMContext):
    await message.answer("Введите предмет, по которому вам нужна помощь:")
    await state.set_state(RegistrationStates.waiting_for_subject)


@dp.message(StateFilter(RegistrationStates.waiting_for_subject))
async def process_subject_for_request(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await message.answer("Опишите ваш запрос:")
    await state.set_state(RegistrationStates.waiting_for_description)


@dp.message(StateFilter(RegistrationStates.waiting_for_description))
async def process_description_for_request(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.create_request(message.from_user.username, data['subject'], message.text)
    await message.answer("Ваш запрос успешно создан!")
    await state.clear()


async def show_teacher_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать уникальный код")]
        ],
        resize_keyboard=True
    )
    await message.answer("Меню учителя:", reply_markup=keyboard)


async def show_cooteacher_profile(message: types.Message, data):
    response = f"Имя: {data['first_name']} {data['second_name']}\nТелефон: {data['phone_num']}\nКласс: {data['grade']}\nПредмет: {data['subject']}"
    await message.answer(response)
    await show_cooteacher_menu(message)


async def show_teacher_profile(message: types.Message, data):
    response = f"Имя: {data['first_name']} {data['last_name']}\nТелефон: {data['phone_num']}\nПредмет: {data['subject']}"
    await message.answer(response)
    await show_teacher_menu(message)


# @dp.message(lambda message: message.text == "Список активных запросов")
# async def handle_show_requests(message: types.Message):
#     requests = db.get_open_requests()
#     if requests:
#         for request in requests:
#             response = f"Запрос #{request['id']}\nПредмет: {request['subject']}\nОписание: {request['description']}"
#             keyboard = InlineKeyboardMarkup(inline_keyboard=[
#                 [InlineKeyboardButton(text="Откликнуться", callback_data=f"respond_{request['id']}")]
#             ])
#             await message.answer(response, reply_markup=keyboard)
#     else:
#         await message.answer("Нет активных запросов.")
#
#
# @dp.callback_query(lambda c: c.data.startswith("respond_"))
# async def handle_respond_to_request(callback_query: types.CallbackQuery):
#     request_id = int(callback_query.data.split("_")[1])
#     db.create_response(request_id, callback_query.from_user.username)
#     db.close_request(request_id)
#     student_username = db.get_student_username_by_request_id(request_id)
#     await callback_query.message.answer(
#         f"Вы откликнулись на запрос #{request_id}. Username ученика: {student_username}")
#     await bot.send_message(chat_id=student_username,
#                            text=f"На ваш запрос откликнулся эксперт: {callback_query.from_user.username}")


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio

    db.init_db()
    asyncio.run(main())
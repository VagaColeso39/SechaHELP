from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, KeyboardButton
import sqlite3
import asyncio

TOKEN = '7263956610:AAEObiOp2c0bo0KmbrFZRznjMKzRG66Yn5o'
bot = Bot(TOKEN)
dp = Dispatcher()

DEFAULT_STATE = 0
SEARCH_STATE = 1
INTERACTION_STATE = 2
RUS = 0
ENG = 1


class LangCb(CallbackData, prefix='langChange'):
    value: int

texts = {'new_user': {RUS: "Мы рады видеть вас в нашем боте / We are grateful to see you in our bot",
                      ENG: "Мы рады видеть вас в нашем боте / We are grateful to see you in our bot"},
         'start': {RUS: 'Для поиска лекарства введите /search\nдля проверки взаимолействия введите /interaction',
                   ENG: "To search for drug type /search\nto check for drugs interaction type /interaction"},
         'language_choose': {RUS: 'Выберите ваш язык / Choose your language',
                             ENG: 'Выберите ваш язык / Choose your language'},
         'language_changed': {RUS: "Язык успешно изменен",
                              ENG: "Language successfully changed"},
         'search_start': {RUS: 'Введите название или часть названия препарата, бот вернет вам список результатов',
                          ENG: 'Send drug title or part of the title, bot will return you list of results'},
         'search_result': {RUS: 'Результат поиска:\n',
                           ENG: 'Search result:\n'}
         }

keyboards = {
    'start': {
        RUS: ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='/search'), KeyboardButton(text='/interaction')]],
                                 resize_keyboard=True),
        ENG: ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='/search'), KeyboardButton(text='/interaction')]],
                                 resize_keyboard=True)},
    'language_choose': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
             [InlineKeyboardButton(text='Русский', callback_data=LangCb(value=RUS).pack()),
              InlineKeyboardButton(text='English', callback_data=LangCb(value=ENG).pack())]]),
        ENG: InlineKeyboardMarkup(inline_keyboard=[
             [InlineKeyboardButton(text='Русский', callback_data=LangCb(value=RUS).pack()),
              InlineKeyboardButton(text='English', callback_data=LangCb(value=ENG).pack())]])}}

conn = sqlite3.connect('main.db')
conn.isolation_level = None
cursor = sqlite3.Cursor(conn)


class User:
    def __init__(self, tg_id: int, state: int = DEFAULT_STATE, language: int = RUS):
        self.id = tg_id
        self.__state = state
        self.__language = language

    def set_state(self, state: int):
        self.__state = state

    def get_state(self):
        return self.__state

    def set_language(self, language: int):
        self.__language = language

    def get_language(self):
        return self.__language


class Users:
    def __init__(self):
        self.ids = []
        self.users = {}

    def check_existence(self, tg_id: int):
        if tg_id in self.ids:
            return True
        return False

    def add_user(self, user: User):
        self.ids.append(user.id)
        self.users[user.id] = user

    def get_user(self, tg_id: int) -> User:
        return self.users[tg_id]


users = Users()


async def send_message(message: Message, code: str, lang: int, markup=None):
    if markup is not None:
        await message.answer(text=texts[code][lang], reply_markup=markup)

    elif code in keyboards.keys():
        await message.answer(text=texts[code][lang], reply_markup=keyboards[code][lang])
    else:
        await message.answer(text=texts[code][lang])


@dp.callback_query(LangCb.filter())
async def change_language(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    lang = callback_data.value
    user = users.get_user(tg_id)
    user.set_language(lang)
    await send_message(callback.message, 'language_changed', lang)
    await send_message(callback.message, 'start', lang)


@dp.message(lambda x: not users.check_existence(x.chat.id))
async def new_user(message: Message):
    tg_id = message.chat.id
    user = User(tg_id)
    users.add_user(user)
    await send_message(message, 'language_choose', RUS)


@dp.message(lambda x: x.text == '/start')
async def start_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    await send_message(message, 'start', language)


@dp.message(lambda x: x.text == '/language')
async def start_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    await send_message(message, 'language_choose', language)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

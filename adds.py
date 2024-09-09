from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, KeyboardButton
import sqlite3
import asyncio

GET_QUESTIONS = 'SELECT ROWID, ru_text, en_text, ru_answer, en_answer FROM questions'
DEFAULT_STATE = 0
SEARCH_STATE = 1
INTERACTION_STATE = 2
RUS = 0
ENG = 1


class LangCb(CallbackData, prefix='langChange'):
    value: int


class FaqCb(CallbackData, prefix='faqCb'):
    num_button: int


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
                           ENG: 'Search result:\n'},
         'faq_list': {RUS: 'Частые вопросы:\n{questions}',
                      ENG: 'Frequently asked questions:\n{questions}'}
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


class Question:
    def __init__(self, q_id, ru_text, en_text, ru_answer, en_answer):
        self.id = q_id
        self.ru_text = ru_text
        self.en_text = en_text
        self.ru_answer = ru_answer
        self.en_answer = en_answer


async def faq_kb_gen(length:int, go_back: bool = False):
    kb = InlineKeyboardBuilder()
    for i in range(length):
        kb.button(text=f'{i + 1}', callback_data=FaqCb(num_button=i+1))
    if go_back:
        kb.button(text='⬅️', callback_data=FaqCb(num_button=-1))
    kb.adjust(*(4, 4, 4))
    return kb.as_markup()
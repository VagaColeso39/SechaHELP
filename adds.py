from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, KeyboardButton
import sqlite3
import asyncio

GET_QUESTIONS = 'SELECT ROWID, ru_text, en_text, ru_answer, en_answer FROM questions'
GET_DORMS = 'SELECT ROWID, ru_name, eng_name, ru_description, en_description FROM dorms'
GET_FEEDBACK = 'SELECT ROWID, id_dorm, ru_text, eng_text, grade FROM feedback'
DEFAULT_STATE = 0
SEARCH_STATE = 1
INTERACTION_STATE = 2
RUS = 0
ENG = 1
DEFAULT_NUMBER_FEEDBACK = 1
FEEDBACK_SORT_TIME_RIGHT = 0
FEEDBACK_SORT_GRADE_RIGHT = 1
FEEDBACK_SORT_TIME_REVERSE = 2
FEEDBACK_SORT_GRADE_REVERSE = 3


class LangCb(CallbackData, prefix='langChange'):
    value: int

class FaqCb(CallbackData, prefix='faqCb'):
    num_button: int

class DormCb(CallbackData, prefix='dormCb'):
    dorms_num: int

class DormInfoCb(CallbackData, prefix='infoCb'):
    command: str

class ReviewsSortCb(CallbackData, prefix='reviewsSortCb'):
    command: str
    command: str

class ReviewsCb(CallbackData, prefix='reviewsCb'):
    command: str

texts = {'new_user': {RUS: "Мы рады видеть вас в нашем боте / We are grateful to see you in our bot",
                      ENG: "Мы рады видеть вас в нашем боте / We are grateful to see you in our bot"},
         'start': {RUS: 'Чтобы открыть список частых вопросов введите /faq\nдля получения информации по общежитиям введите /dorms',
                   ENG: "To open frequently asked questions list type in /faq\nto get the info about the dorms type in /dorms"},
         'language_choose': {RUS: 'Выберите ваш язык / Choose your language',
                             ENG: 'Выберите ваш язык / Choose your language'},
         'language_changed': {RUS: "Язык успешно изменен",
                              ENG: "Language successfully changed"},
         'faq_list': {RUS: 'Частые вопросы:\n{questions}',
                      ENG: 'Frequently asked questions:\n{questions}'},
         'dorms_list': {RUS: 'Список общежитий:\n{dorms}',
                        ENG: 'List of dorms:\n{dorms}'},
         'sent_feedback': {RUS: 'Напишите свой отзыв и после него добавьте оценку следующих пунктов:\n'
                                '◆ транспортная доступность(близость метро, остановок, близость до корпусов) 1/10\n'
                                '◆ работа персонала(охранники, уборщицы и др) 1/10\n'
                                '◆ удобство комнат(ремонт, мебель, просторность и тд) 1/10\n'
                                '◆ удобство общих зон(кухня, коворкинг, туалет и ванная) 1/10\n'
                                '◆ инфраструктура(магазины, пункты выдачи и тд) 1/10',
                            ENG: ''},
         'dorm_reviews_sort': {RUS: 'Выберите сортировку отзывов',
                      ENG: ''},
         'dorm_reviews': {RUS: '{review}',
                        ENG: '{review}'}
         }

keyboards = {
    'start': {
        RUS: ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='/dorms'), KeyboardButton(text='/faq')]],
                                 resize_keyboard=True),
        ENG: ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='/dorms'), KeyboardButton(text='/faq')]],
                                 resize_keyboard=True)},
    'language_choose': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Русский', callback_data=LangCb(value=RUS).pack()),
             InlineKeyboardButton(text='English', callback_data=LangCb(value=ENG).pack())]]),
        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Русский', callback_data=LangCb(value=RUS).pack()),
             InlineKeyboardButton(text='English', callback_data=LangCb(value=ENG).pack())]])},

    'dorms_list': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='1 общежитие', callback_data=DormCb(dorms_num=1).pack()),
             InlineKeyboardButton(text='2 общежитие', callback_data=DormCb(dorms_num=2).pack()),
             InlineKeyboardButton(text='3 общежитие', callback_data=DormCb(dorms_num=3).pack())],
            [InlineKeyboardButton(text='4 общежитие', callback_data=DormCb(dorms_num=4).pack()),
             InlineKeyboardButton(text='5 общежитие', callback_data=DormCb(dorms_num=5).pack()),
             InlineKeyboardButton(text='6 общежитие', callback_data=DormCb(dorms_num=6).pack())]
        ]),
        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='1 dorm', callback_data=DormCb(dorms_num=1).pack()),
             InlineKeyboardButton(text='2 dorm', callback_data=DormCb(dorms_num=2).pack()),
             InlineKeyboardButton(text='3 dorm', callback_data=DormCb(dorms_num=3).pack())],
            [InlineKeyboardButton(text='4 dorm', callback_data=DormCb(dorms_num=4).pack()),
             InlineKeyboardButton(text='5 dorm', callback_data=DormCb(dorms_num=5).pack()),
             InlineKeyboardButton(text='6 dorm', callback_data=DormCb(dorms_num=6).pack())
             ]])},

    'dorm_info': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='отзывы на общежитие', callback_data=DormInfoCb(command="review").pack()),
             InlineKeyboardButton(text='оставить отзыв', callback_data=DormInfoCb(command="send_review").pack()),
             InlineKeyboardButton(text='⬅️', callback_data=DormInfoCb(command="back").pack())]
        ]),
        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='dorm reviews', callback_data=DormInfoCb(command="review").pack()),
             InlineKeyboardButton(text='leave review', callback_data=DormInfoCb(command="send_review").pack()),
             InlineKeyboardButton(text='⬅️', callback_data=DormInfoCb(command="back").pack())]
        ])
    },

    'dorm_reviews_sort': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='сначала новые', callback_data=ReviewsSortCb(command="new").pack())],
             [InlineKeyboardButton(text='сначала старые', callback_data=ReviewsSortCb(command="old").pack())],
             [InlineKeyboardButton(text='сначала положительные', callback_data=ReviewsSortCb(command="positive").pack())],
             [InlineKeyboardButton(text='сначала отрицательные', callback_data=ReviewsSortCb(command="negative").pack())],
             [InlineKeyboardButton(text='⬅️', callback_data=ReviewsSortCb(command="back").pack())]
        ]),
        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='new ones first', callback_data=ReviewsSortCb(command="new").pack())],
             [InlineKeyboardButton(text='old ones first', callback_data=ReviewsSortCb(command="old").pack())],
             [InlineKeyboardButton(text='positive ones first', callback_data=ReviewsSortCb(command="positive").pack())],
             [InlineKeyboardButton(text='negative ones first', callback_data=ReviewsSortCb(command="negative").pack())],
             [InlineKeyboardButton(text='⬅️', callback_data=ReviewsSortCb(command="back").pack())]
        ])
    },

    'dorm_reviews': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='следующий отзыв', callback_data=ReviewsCb(command="next").pack()),
             InlineKeyboardButton(text='предыдущий отзыв', callback_data=ReviewsCb(command="last").pack()),
             InlineKeyboardButton(text='⬅️', callback_data=ReviewsCb(command="back").pack())]
        ]),
        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='next review', callback_data=ReviewsCb(command="next").pack()),
             InlineKeyboardButton(text='previous review', callback_data=ReviewsCb(command="last").pack()),
             InlineKeyboardButton(text='⬅️', callback_data=ReviewsCb(command="back").pack())]
        ])
    }
}


class User:
    def __init__(self, tg_id: int, state: int = DEFAULT_STATE, language: int = RUS, feedback_number: int = DEFAULT_NUMBER_FEEDBACK, type_sort_feedback: int = FEEDBACK_SORT_TIME_RIGHT):
        self.id = tg_id
        self.__state = state
        self.__language = language
        self.__feedback_number = feedback_number
        self.__type_sort_feedback = type_sort_feedback

    def set_state(self, state: int):
        self.__state = state

    def get_state(self):
        return self.__state

    def get_feedback_number(self):
        return self.__feedback_number

    def set_feedback_number(self, number: int):
        self.__feedback_number = number

    def get_sorter_parameter(self):
        return self.__type_sort_feedback

    def set_sorter_parameter(self, number: int):
        self.__type_sort_feedback = number

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

    def set_feedback_number(self, tg_id, param):
        pass


class Question:
    def __init__(self, q_id, ru_text, en_text, ru_answer, en_answer):
        self.id = q_id
        self.ru_text = ru_text
        self.en_text = en_text
        self.ru_answer = ru_answer
        self.en_answer = en_answer


class Dorm:
    def __init__(self, id, ru_name, eng_name, ru_description, en_description):
        self.id = id
        self.ru_name = ru_name
        self.eng_name = eng_name
        self.ru_description = ru_description
        self.en_description = en_description


class Feedback:
    def __init__(self, id, id_dorm, ru_text, eng_text, grade):
        self.id = id
        self.id_dorm = id_dorm
        self.ru_text = ru_text
        self.eng_text = eng_text
        self.grade = grade


async def faq_kb_gen(length: int, go_back: bool = False):
    kb = InlineKeyboardBuilder()
    for i in range(length):
        kb.button(text=f'{i + 1}', callback_data=FaqCb(num_button=i + 1))
    if go_back:
        kb.button(text='⬅️', callback_data=FaqCb(num_button=-1))
    kb.adjust(*(4, 4, 4))
    return kb.as_markup()

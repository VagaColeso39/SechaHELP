from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, KeyboardButton
import requests
import sqlite3
import asyncio

conn = sqlite3.connect('main.db')
conn.isolation_level = None
cursor = sqlite3.Cursor(conn)

TRANSLATE_LINK_RU_EN = 'https://ftapi.pythonanywhere.com/translate?&dl=en&text='
TRANSLATE_LINK_EN_RU = 'https://ftapi.pythonanywhere.com/translate?&dl=ru&text='

GET_QUESTIONS = 'SELECT ROWID, ru_text, en_text, ru_answer, en_answer FROM questions'
GET_USERS = "SELECT tg_id, language, verified FROM users"
GET_DORMS = 'SELECT ROWID, ru_name, eng_name, ru_description, en_description FROM dorms'
GET_REQUESTS = "SELECT ROWID, requester_id, feedback_id FROM requests WHERE author_id=?"
GET_REQUEST_ID = "SELECT ROWID FROM requests WHERE requester_id=? AND feedback_id=?"
GET_REQUESTER_ID = "SELECT requester_id FROM requests WHERE ROWID=?"
GET_FEEDBACKS = 'SELECT ROWID, id_dorm, ru_text, grade_avg, language, en_text, grade_staff, grade_private, grade_infrastructure, grade_public, grade_transport, accepted, verified, creator_id FROM feedbacks'
AUTHOR_ID_BY_ID = "SELECT creator_id FROM feedbacks WHERE ROWID=?"
CHECK_REQUEST_COMPLETED = "SELECT answered FROM requests WHERE requester_id=? AND feedback_id=?"
CREATE_FEEDBACK = 'INSERT INTO feedbacks (id_dorm, ru_text, grade_avg, language, en_text, grade_staff, grade_private, grade_infrastructure, grade_public, grade_transport, accepted, verified, creator_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
CREATE_USER = "INSERT INTO users (tg_id, language) VALUES (?, ?)"
CREATE_REQUEST = "INSERT INTO requests (requester_id, feedback_id, author_id, request_text) VALUES (?, ?, ?, ?)"
UPDATE_LANGUAGE = "UPDATE users SET language=? WHERE tg_id=?"
MARK_REQUEST = "UPDATE requests SET marked=1 WHERE ROWID=?"
COMPLETE_REQUEST = "UPDATE requests SET answered=1 WHERE ROWID=?"

DEFAULT_STATE = 0
SEARCH_STATE = 1
INTERACTION_STATE = 2
FEEDBACK_WRITING_STATE = 3
AUTHOR_ASK_STATE = 4
REQUEST_REPLY_STATE = 5
RUS = 0
ENG = 1
DEFAULT_NUMBER_FEEDBACK = 1
FEEDBACK_SORT_TIME_RIGHT = 0
FEEDBACK_SORT_GRADE_RIGHT = 1
FEEDBACK_SORT_TIME_REVERSE = 2
FEEDBACK_SORT_GRADE_REVERSE = 3
RATE_TRANSPORT = 0
RATE_STAFF = 1
RATE_PRIVATE = 2
RATE_PUBLIC = 3
RATE_INFRASTRUCTURE = 4
RATE_AVG = 5


class AlreadyVerified(Exception):
    pass


class LangCb(CallbackData, prefix='langChange'):
    value: int


class NotifyCb(CallbackData, prefix='notifyCb'):
    action: str
    request_id: int


class FaqCb(CallbackData, prefix='faqCb'):
    num_button: int


class RateCb(CallbackData, prefix='rateCb'):
    current_param: int
    rate: int


class DormCb(CallbackData, prefix='dormCb'):
    dorms_num: int


class DormInfoCb(CallbackData, prefix='infoCb'):
    command: str


class FeedbacksSortCb(CallbackData, prefix='feedbacksSortCb'):
    command: str


class FeedbacksCb(CallbackData, prefix='feedbacksCb'):
    command: str


class FeedbackFinishCb(CallbackData, prefix='fbFinishCb'):
    command: str


class AskAuthorCb(CallbackData, prefix='askAuthorCb'):
    command: str


texts = {
    'new_user': {RUS: "Мы рады видеть вас в нашем боте / We are grateful to see you in our bot",
                 ENG: "Мы рады видеть вас в нашем боте / We are grateful to see you in our bot"},
    'start': {
        RUS: 'Чтобы открыть список частых вопросов введите /faq\nдля получения информации по общежитиям введите /dorms\n для смены языка введите /language',
        ENG: "To open frequently asked questions list type in /faq\nto get the info about the dorms type in /dorms\n to change language type in /language"},
    'language_choose': {RUS: 'Выберите ваш язык / Choose your language',
                        ENG: 'Выберите ваш язык / Choose your language'},
    'language_changed': {RUS: "Язык успешно изменен",
                         ENG: "Language successfully changed"},
    'faq_list': {RUS: 'Частые вопросы:\n{questions}',
                 ENG: 'Frequently asked questions:\n{questions}'},
    'dorms_list': {RUS: 'Список общежитий:\n{dorms}',
                   ENG: 'List of dorms:\n{dorms}'},
    'sent_feedback': {RUS: 'Оцените общежитие по следующим пяти пунктам, от одного до десяти:\n\n'
                           '◆ Транспортная доступность (близость метро, остановок, близость до корпусов)\n'
                           '◆ Персонал (охранники, уборщицы и др.)\n'
                           '◆ Личные комнаты (ремонт, мебель, просторность и т.д.)\n'
                           '◆ Общие зоны (кухня, коворкинг, туалет и ванная)\n'
                           '◆ Инфраструктура (магазины, пункты выдачи и т.д.)\n\n'
                           'После оценки напишите текстовый отзыв (помните, что отзывы модерируются, пожалуйста пишите осмысленный отзыв, не нарушающий законов РФ, без нецензурной лексики, оскорблений и т.п.)',
                      ENG: 'Rate the dorm by the next five parameters, from one to ten:\n\n'
                           '◆ Public transport accessibility (path time to the metro, bus/tram/trolley stops, nearness of university buildings)\n'
                           '◆ Dorm personal  (security, cleaners. etc.)\n'
                           '◆ Private rooms (renovation, furniture, spaciousness, etc.)\n'
                           '◆ Public rooms comfort (kiktchen, co-workings, bathrooms)\n'
                           '◆ infrastructure (shops, delivery posts, etc.)\n\n'
                           'After raiting write a text feedback (remember, that all feedbacks are going through moderation, so please write politely, without insults and/or breaking the Russian Federation law)'},
    'dorm_feedbacks_sort': {RUS: 'Выберите сортировку отзывов',
                          ENG: 'Choose feedbacks sorting'},
    RATE_TRANSPORT: {RUS: '◆ Транспортная доступность (близость метро, остановок, близость до корпусов)',
                     ENG: '◆ Public transport accessibility (path time to the metro, bus/tram/trolley stops, nearness of university buildings)'},
    RATE_STAFF: {RUS: '◆ Персонал (охранники, уборщицы и др.)',
                 ENG: '◆ Dorm personal (security, cleaners. etc.)'},
    RATE_PRIVATE: {RUS: '◆ Личные комнаты (ремонт, мебель, просторность и т.д.)',
                   ENG: '◆ Private rooms (renovation, furniture, spaciousness, etc.)'},
    RATE_PUBLIC: {RUS: '◆ Общие зоны (кухня, коворкинг, туалет и ванная)',
                  ENG: '◆ Public rooms comfort (kiktchen, co-workings, bathrooms)'},
    RATE_INFRASTRUCTURE: {RUS: '◆ Инфраструктура (магазины, пункты выдачи и т.д.)',
                          ENG: '◆ infrastructure (shops, delivery posts, etc.)'},
    'rate_write_text': {
        RUS: 'Ваши оценки:\n\n транспорт - {r1}/10\n персонал - {r2}/10\n комнаты - {r3}/10\n общие пространства - {r4}/10\n инфраструктура - {r5}/10\n средняя - {avg}/10\n\n'
             'Теперь, пожалуйста, напишите текстовый отзыв',
        ENG: 'Your rates:\n\n transport - {r1}/10\n staff - {r2}/10\n private rooms - {r3}/10\n public rooms - {r4}/10\n infrastructure - {r5}/10\n average - {avg}/10\n\n'
             'Now, please, leave a text feedback'},
    'confirm_feedback': {RUS: "Подтвердить отправку отзыва на модерацию?",
                         ENG: "Confirm sending feedback for moderation?"},
    'feedback_confirmed': {
        RUS: "Ваш отзыв отправлен на модерацию,в течение 1-3 рабочих дней ожидайте сообщение от этого бота с дальнейшей информацией по отзыву",
        ENG: "Your feedback have been sent to moderation, wait for the message with additional information from this bot in 1-3 business days"},
    'dorm_feedbacks': {
        RUS: '◆ Транспортная доступность: {transport}/10\n◆ Персонал: {staff}/10\n◆ Личные комнаты: {private}/10\n◆ Общие зоны: {public}/10\n◆ Инфраструктура: {infrastructure}/10\n◆ Среднее: {average}/10\n\n{feedback}',
        ENG: '◆ Transport accessibility: {transport}/10\n◆ Staff: {staff}/10\n◆ Private rooms: {private}/10\n◆ Public rooms: {public}/10\n◆ Infrastructure: {infrastructure}/10\n◆ Average: {average}/10\n\n{feedback}'},

    'ask_author': {RUS: 'Напишите вопрос автору отзыва, после модерации текста он получит возможность ответить вам',
                   ENG: "Write question to the feedback author, after text moderation he will be able to answer you"},
    'ask_author_sending': {RUS: 'Подтвердите отправку',
                           ENG: 'Confirm sending'},
    'ask_notification_public': {RUS: 'На ваш отзыв на общежитие пришел вопрос со следующим текстом:\n\n{text}\n\nПользователь оставил свой телеграмм: @{username}, вы можете ответить ему в личных сообщениях, или анонимно, через бота. Если сообщение от пользователя содержит оскорбления, нецензурную лексику и т.п. нажмите на кнопку "Пожаловаться"',
                                ENG: 'There is a new question from user for your feedback with the next text: \n\n{text}\n\nUser left his telegram for you: @{username}, you can answer him by private message or anonymously by our bot. If you think that message contains insults, obscene language, etc. press the button "Report"'},
    'ask_notification_private': {RUS: 'На ваш отзыв на общежитие пришел вопрос со следующим текстом:\n\n{text}\n\nвы можете анонимно ответить ему через нашего бота. Если сообщение от пользователя содержит оскорбления, нецензурную лексику и т.п. нажмите на кнопку "Пожаловаться"',
                                 ENG: 'There is a new question from user for your feedback with the next text: \n\n{text}\n\nyou can anonymously answer it by our bot. If you think that this message contains insults, obscene language, etc. press the button "Report"'},
    'question_reply': {RUS: 'Автор отзыва отправил ответ на ваш вопрос:\n\n{text}\n\nЕсли ответ содержит оскорбления, нецензурную лексику и т.п. нажмите на кнопку "Пожаловаться"',
                       ENG: 'Author of the feedback sent you answer for your question: \n\n{text}\n\nIf you think that this message contains insults, obscene language, etc. press the button "Report"'},
    'question_replied': {RUS: "Ваш ответ успешно отправлен, благодарим вас за обратную связь",
                         ENG: "Your answer was successfully sent, we are grateful for your replies"},
    'answering_request': {RUS: "Напишите ответ на вопрос пользователя",
                          ENG: "Write answer to the user's question"},
    'request_reported': {RUS: 'Вы пожаловались на сообщение, оно пройдет модерацию',
                         ENG: "You have reported a message, it will be moderated"},
    'already_asked': {RUS: "Вы уже задали вопрос по этому отзыву, дождитесь ответа автора",
                      ENG: "You have already sent a question for this feedback, wait for the author's answer"},
    'feedback_already_sent': {RUS: "Вы уже отправили отзыв по этому общежитию, дождитесь модерации",
                              ENG: "You have already sent feedback for this dorm, wait for the moderation"}
}

keyboards = {
    'start': {
        RUS: ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='/dorms'), KeyboardButton(text='/faq'), KeyboardButton(text='/language')]],
            resize_keyboard=True),
        ENG: ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='/dorms'), KeyboardButton(text='/faq'), KeyboardButton(text='/language')]],
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
            [InlineKeyboardButton(text='отзывы на общежитие', callback_data=DormInfoCb(command="feedback").pack()),
             InlineKeyboardButton(text='оставить отзыв', callback_data=DormInfoCb(command="send_feedback").pack()),
             InlineKeyboardButton(text='⬅️', callback_data=DormInfoCb(command="back").pack())]]),

        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='dorm feedbacks', callback_data=DormInfoCb(command="feedback").pack()),
             InlineKeyboardButton(text='leave feedback', callback_data=DormInfoCb(command="send_feedback").pack()),
             InlineKeyboardButton(text='⬅️', callback_data=DormInfoCb(command="back").pack())]])
    },

    'dorm_feedbacks_sort': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='сначала новые', callback_data=FeedbacksSortCb(command="new").pack())],
            [InlineKeyboardButton(text='сначала старые', callback_data=FeedbacksSortCb(command="old").pack())],
            [InlineKeyboardButton(text='сначала положительные',
                                  callback_data=FeedbacksSortCb(command="positive").pack())],
            [InlineKeyboardButton(text='сначала отрицательные',
                                  callback_data=FeedbacksSortCb(command="negative").pack())],
            [InlineKeyboardButton(text='⬅️', callback_data=FeedbacksSortCb(command="back").pack())]]),

        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='new ones first', callback_data=FeedbacksSortCb(command="new").pack())],
            [InlineKeyboardButton(text='old ones first', callback_data=FeedbacksSortCb(command="old").pack())],
            [InlineKeyboardButton(text='positive ones first', callback_data=FeedbacksSortCb(command="positive").pack())],
            [InlineKeyboardButton(text='negative ones first', callback_data=FeedbacksSortCb(command="negative").pack())],
            [InlineKeyboardButton(text='⬅️', callback_data=FeedbacksSortCb(command="back").pack())]])
    },

    'dorm_feedbacks': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='следующий отзыв', callback_data=FeedbacksCb(command="next").pack()),
             InlineKeyboardButton(text='предыдущий отзыв', callback_data=FeedbacksCb(command="last").pack())],
             [InlineKeyboardButton(text='обратная связь', callback_data=FeedbacksCb(command='ask').pack())],
             [InlineKeyboardButton(text='⬅️', callback_data=FeedbacksCb(command="back").pack())]]),

        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='next feedback', callback_data=FeedbacksCb(command="next").pack()),
             InlineKeyboardButton(text='previous feedback', callback_data=FeedbacksCb(command="last").pack())],
             [InlineKeyboardButton(text='contact author', callback_data=FeedbacksCb(command='ask').pack())],
             [InlineKeyboardButton(text='⬅️', callback_data=FeedbacksCb(command="back").pack())]])
    },
    'confirm_feedback': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Подтвердить отправку',
                                  callback_data=FeedbackFinishCb(command="confirm").pack()),
             InlineKeyboardButton(text='Изменить оценки', callback_data=FeedbackFinishCb(command="rate").pack()),
             InlineKeyboardButton(text='Изменить текст', callback_data=FeedbackFinishCb(command="text").pack()),
             InlineKeyboardButton(text='Отменить отправку', callback_data=FeedbackFinishCb(command="cancel").pack())]]),

        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Confirm sending', callback_data=FeedbackFinishCb(command="confirm").pack()),
             InlineKeyboardButton(text='Change rates', callback_data=FeedbackFinishCb(command="rate").pack()),
             InlineKeyboardButton(text='Change text', callback_data=FeedbackFinishCb(command="text").pack()),
             InlineKeyboardButton(text='Cancel sending', callback_data=FeedbackFinishCb(command="cancel").pack())]])

    },
    'ask_author_sending': {
        RUS: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Прикрепить свой ник', callback_data=AskAuthorCb(command="public").pack()),
             InlineKeyboardButton(text='Отправить анонимно', callback_data=AskAuthorCb(command="anonym").pack()),
             InlineKeyboardButton(text='Изменить текст', callback_data=AskAuthorCb(command="text").pack()),
             InlineKeyboardButton(text='Отменить отправку', callback_data=AskAuthorCb(command="cancel").pack())]]),
        ENG: InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Send with your nickname', callback_data=AskAuthorCb(command="public").pack()),
             InlineKeyboardButton(text='Send anonymously', callback_data=AskAuthorCb(command="anonym").pack()),
             InlineKeyboardButton(text='Change text', callback_data=AskAuthorCb(command="text").pack()),
             InlineKeyboardButton(text='Cancel sending', callback_data=AskAuthorCb(command="cancel").pack())]]),

    }
}

class User:
    def __init__(self, tg_id: int, language: int = RUS, verified: bool = False, state: int = DEFAULT_STATE,
                 feedback_number: int = DEFAULT_NUMBER_FEEDBACK,
                 type_sort_feedback: int = FEEDBACK_SORT_TIME_RIGHT,
                 selected_dorm: int = 1):
        self.id = tg_id
        self.__state = state
        self.__language = language
        self.__feedback_number = feedback_number
        self.__type_sort_feedback = type_sort_feedback
        self.__selected_dorm = selected_dorm
        self.__tmp_dorm_rate = {}
        self.__text = ''
        self.__verified = verified
        self.__requests = {}
        self.__request_id = 0
        for writing in cursor.execute(GET_REQUESTS, (self.id,)).fetchall():
            self.__requests[writing[0]] = (writing[1], writing[2])

    def is_verified(self):
        return self.__verified

    def verify(self):
        if self.__verified:
            raise AlreadyVerified
        self.__verified = True

    def set_reply_request(self, request_id):
        self.__request_id = request_id

    def get_reply_request(self):
        return self.__request_id


    def add_request(self, requester_id, feedback_id, request_text):
        cursor.execute(CREATE_REQUEST, (requester_id, feedback_id, self.id, request_text))
        request_id = cursor.execute(GET_REQUEST_ID, (requester_id, feedback_id)).fetchone()[0]
        self.__requests[request_id] = (requester_id, feedback_id)
        return request_id

    def get_requests(self):
        return self.__requests

    def set_rate(self, rate: float, param: int):
        self.__tmp_dorm_rate[param] = rate

    def get_rate(self):
        return self.__tmp_dorm_rate

    def set_state(self, state: int):
        self.__state = state

    def get_state(self):
        return self.__state

    def set_text(self, text: str):
        self.__text = text

    def get_text(self):
        return self.__text

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

    def set_dorm_number(self, selected_dorm: int):
        self.__selected_dorm = selected_dorm

    def get_dorm_number(self):
        return self.__selected_dorm


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
    def __init__(self, feedback_id, id_dorm, ru_text, grade_avg, language, en_text, grade_staff, grade_private,
                 grade_infrastructure, grade_public, grade_transport, accepted, verified, creator_id):
        self.id = feedback_id
        self.id_dorm = id_dorm
        self.ru_text = ru_text
        self.grade_avg = grade_avg
        self.language = language
        self.en_text = en_text
        self.grade_staff = grade_staff
        self.grade_private = grade_private
        self.grade_infrastructure = grade_infrastructure
        self.grade_public = grade_public
        self.grade_transport = grade_transport
        self.accepted = accepted
        self.verified = verified
        self.creator_id = creator_id


async def faq_kb_gen(length: int, go_back: bool = False):
    kb = InlineKeyboardBuilder()
    for i in range(length):
        kb.button(text=f'{i + 1}', callback_data=FaqCb(num_button=i + 1))
    if go_back:
        kb.button(text='⬅️', callback_data=FaqCb(num_button=-1))
    kb.adjust(*(4, 4, 4))
    return kb.as_markup()


async def notification_kb_gen(language, request_id):
    kb = InlineKeyboardBuilder()
    if language == RUS:
        kb.button(text='Ответить на сообщение', callback_data=NotifyCb(action="Reply", request_id=request_id))
        kb.button(text='Удалить уведомление', callback_data=NotifyCb(action='Delete', request_id=request_id))
        kb.button(text='Пожаловаться', callback_data=NotifyCb(action='Report', request_id=request_id))
    elif language == ENG:
        kb.button(text='Reply to message', callback_data=NotifyCb(action="Reply", request_id=request_id))
        kb.button(text='Delete notification', callback_data=NotifyCb(action='Delete', request_id=request_id))
        kb.button(text='Report', callback_data=NotifyCb(action='Report', request_id=request_id))
    kb.adjust(*(3, 3))
    return kb.as_markup()


async def reply_kb_gen(language, request_id):
    kb = InlineKeyboardBuilder()
    if language == RUS:
        kb.button(text='Удалить уведомление', callback_data=NotifyCb(action='Delete', request_id=request_id))
        kb.button(text='Пожаловаться', callback_data=NotifyCb(action='Report', request_id=request_id))
    elif language == ENG:
        kb.button(text='Delete notification', callback_data=NotifyCb(action='Delete', request_id=request_id))
        kb.button(text='Report', callback_data=NotifyCb(action='Report', request_id=request_id))
    kb.adjust(*(2, 2))
    return kb.as_markup()


async def feedback_write_kb_gen(current_param: int):
    kb = InlineKeyboardBuilder()
    for i in range(1, 11):
        kb.button(text=f'{i}', callback_data=RateCb(current_param=current_param, rate=i))
    kb.adjust(*(5, 5))
    return kb.as_markup()

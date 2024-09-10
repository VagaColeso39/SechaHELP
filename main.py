from adds import *

TOKEN = '7263956610:AAEObiOp2c0bo0KmbrFZRznjMKzRG66Yn5o'
bot = Bot(TOKEN)
dp = Dispatcher()

questions = {}
users = Users()

conn = sqlite3.connect('main.db')
conn.isolation_level = None
cursor = sqlite3.Cursor(conn)


def load_questions():
    for question in cursor.execute(GET_QUESTIONS).fetchall():
        questions[question[0]] = Question(*question)
    ru_text = '\n'.join(map(lambda question: f'{question.id}: {question.ru_text}', questions.values()))
    en_text = '\n'.join(map(lambda question: f'{question.id}: {question.en_text}', questions.values()))
    texts['faq_list'][RUS] = texts['faq_list'][RUS].format(questions=ru_text)
    texts['faq_list'][ENG] = texts['faq_list'][ENG].format(questions=en_text)

dorms = {}

def load_dorms():
    for dorm in cursor.execute(GET_DORMS).fetchall():
        dorms[dorm[0]] = Dorm(*dorm)
    ru_text = '\n'.join(map(lambda dorm: f'{dorm.ru_name}', dorms.values()))
    en_text = '\n'.join(map(lambda dorm: f'{dorm.eng_name}', dorms.values()))
    texts['dorm_list'][RUS] = texts['dorm_list'][RUS].format(dorms=ru_text)
    texts['dorm_list'][ENG] = texts['dorm_list'][ENG].format(dorms=en_text)


async def send_message(message: Message, code: str, lang: int, keyboard=None):
    if keyboard is not None:
        await message.answer(text=texts[code][lang], reply_markup=keyboard)
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


@dp.callback_query(DormCb.filter())
async def change_language(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    dorm = callback_data.value
    await send_message(callback.message, 'language_changed', dorm)


@dp.callback_query(FaqCb.filter())
async def faq_choose(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    user = users.get_user(tg_id)

    question_id = callback_data.num_button
    language = user.get_language()
    if question_id == -1:
        kb = await faq_kb_gen(len(questions), False)
        await callback.message.edit_text(text=texts['faq_list'][language], reply_markup=kb)
        return
    kb = await faq_kb_gen(len(questions), True)
    if language == RUS:
        await callback.message.edit_text(text=questions[question_id].ru_answer, reply_markup=kb)
    else:
        await callback.message.edit_text(text=questions[question_id].en_answer, reply_markup=kb)


@dp.message(lambda message: not users.check_existence(message.chat.id))
async def new_user(message: Message):
    tg_id = message.chat.id
    user = User(tg_id)
    users.add_user(user)
    await send_message(message, 'language_choose', RUS)


@dp.message(lambda message: message.text == '/start')
async def start_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    await send_message(message, 'start', language)


@dp.message(lambda x: x.text == '/language')
async def language_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    await send_message(message, 'language_choose', language)


@dp.message(lambda x: x.text == '/faq')
async def faq_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    kb = await faq_kb_gen(len(questions))
    await send_message(message, 'faq_list', language, kb)

@dp.message(lambda x: x.text == '/dorm')
async def dorm_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    await send_message(message, 'dorm_list', language)

async def main():
    load_questions()
    load_dorms()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

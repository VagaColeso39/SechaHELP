from adds import *

TOKEN = '7318423417:AAHlLQ2Tnns1s02jHGs2eSFwPKAArBogZuI'
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
    texts['dorms_list'][RUS] = texts['dorms_list'][RUS].format(dorms=ru_text)
    texts['dorms_list'][ENG] = texts['dorms_list'][ENG].format(dorms=en_text)


feedbacks_by_time = {}
feedbacks_by_rate = {}
reviews = []
res = []

def load_feedbacks():
    global res, feedbacks_by_rate, feedbacks_by_time
    for review in cursor.execute(GET_FEEDBACK).fetchall():
        feedbacks_by_time[review[0]] = Feedback(*review)
    feedbacks_by_rate = list(feedbacks_by_time.values())
    feedbacks_by_rate.sort(key=lambda feedback: feedback.grade)
    feedbacks_by_rate = dict(zip(range(1, len(feedbacks_by_rate)+1), feedbacks_by_rate))
    res = [feedbacks_by_time, feedbacks_by_rate]


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
async def change_dorm(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    dorm_id = callback_data.dorms_num
    language = users.get_user(tg_id).get_language()


    if dorm_id == -1:
        kb = keyboards['dorms_list'][language]
        await callback.message.edit_text(text=texts['dorms_list'][language], reply_markup=kb)
        return
    kb = keyboards['dorm_info'][language]
    users.get_user(tg_id).set_dorm_number(dorm_id)
    if language == RUS:
        await callback.message.edit_text(text=dorms[dorm_id].ru_description, reply_markup=kb)
    else:
        await callback.message.edit_text(text=dorms[dorm_id].en_description, reply_markup=kb)


@dp.callback_query(DormInfoCb.filter())
async def choose_dorm_command(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    command  = callback_data.command
    language = users.get_user(tg_id).get_language()

    if command == "review":
        kb = keyboards['dorm_reviews_sort'][language]
        await callback.message.edit_text(text=texts['dorm_reviews_sort'][language], reply_markup=kb)

    if command == "send_review":
        kb = keyboards['dorm_reviews_sort'][language]
        await callback.message.edit_text(text=texts['sent_feedback'][language], reply_markup=kb)

    if command == "back":
        kb = keyboards['dorms_list'][language]
        await callback.message.edit_text(text=texts['dorms_list'][language], reply_markup=kb)


@dp.callback_query(ReviewsSortCb.filter())
async def change_filter(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    command  = callback_data.command
    language = users.get_user(tg_id).get_language()
    dorm_number = users.get_user(tg_id).get_dorm_number()

    if command == "new":
        users.get_user(tg_id).set_feedback_number(len(feedbacks_by_time))
        users.get_user(tg_id).set_sorter_parameter(2)
        sorter_parameter = 2
        feedback_number = len(feedbacks_by_time)
        kb = keyboards['dorm_reviews'][language]
        await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter-2][feedback_number].ru_text), reply_markup=kb)

    if command == "old":
        users.get_user(tg_id).set_feedback_number(1)
        users.get_user(tg_id).set_sorter_parameter(0)
        sorter_parameter = 0
        feedback_number = 1
        kb = keyboards['dorm_reviews'][language]
        await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter][feedback_number].ru_text),
                                         reply_markup=kb)

    if command == "negative":
        users.get_user(tg_id).set_feedback_number(1)
        users.get_user(tg_id).set_sorter_parameter(1)
        sorter_parameter = 1
        feedback_number = 1
        kb = keyboards['dorm_reviews'][language]
        await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter][feedback_number].ru_text),
                                         reply_markup=kb)

    if command == "positive":
        users.get_user(tg_id).set_feedback_number(len(feedbacks_by_time))
        users.get_user(tg_id).set_sorter_parameter(3)
        sorter_parameter = 3
        feedback_number = len(feedbacks_by_time)
        kb = keyboards['dorm_reviews'][language]
        await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter - 2][feedback_number].ru_text),
                                         reply_markup=kb)

    if command == "back":
        kb = keyboards['dorm_info'][language]
        if language == RUS:
            await callback.message.edit_text(text=dorms[dorm_number].ru_description, reply_markup=kb)
        else:
            await callback.message.edit_text(text=dorms[dorm_number].en_description, reply_markup=kb)


@dp.callback_query(ReviewsCb.filter())
async def scrolling_reviews(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    command  = callback_data.command
    language = users.get_user(tg_id).get_language()
    sorter_parameter = users.get_user(tg_id).get_sorter_parameter()
    feedback_number = users.get_user(tg_id).get_feedback_number()
    user = users.get_user(tg_id)

    if sorter_parameter in [0, 1]:
        if command == "next":
            if feedback_number == len(feedbacks_by_rate):
                user.set_feedback_number(1)
                feedback_number = 1
            else:
                feedback_number += 1
                user.set_feedback_number(feedback_number)
            kb = keyboards['dorm_reviews'][language]
            await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter][feedback_number].ru_text),
                                             reply_markup=kb)

        elif command == "last":
            if feedback_number == 1:
                user.set_feedback_number(len(feedbacks_by_rate))
                feedback_number = len(feedbacks_by_rate)
            else:
                feedback_number -= 1
                user.set_feedback_number(feedback_number)
            kb = keyboards['dorm_reviews'][language]
            await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter][feedback_number].ru_text),
                                             reply_markup=kb)
    else:
        if command == "last":
            if feedback_number == len(feedbacks_by_rate):
                user.set_feedback_number(1)
                feedback_number = 1
            else:
                feedback_number += 1
                user.set_feedback_number(feedback_number)
            kb = keyboards['dorm_reviews'][language]
            await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter-2][feedback_number].ru_text),
                                             reply_markup=kb)

        elif command == "next":
            if feedback_number == 1:
                user.set_feedback_number(len(feedbacks_by_rate))
                feedback_number = len(feedbacks_by_rate)
            else:
                feedback_number -= 1
                user.set_feedback_number(feedback_number)
            kb = keyboards['dorm_reviews'][language]
            await callback.message.edit_text(text=texts['dorm_reviews'][RUS].format(review=res[sorter_parameter-2][feedback_number].ru_text),
                                             reply_markup=kb)

    if command == "back":
        kb = keyboards['dorm_reviews_sort'][language]
        await callback.message.edit_text(text=texts['dorm_reviews_sort'][language], reply_markup=kb)

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

@dp.message(lambda x: x.text == '/dorms')
async def dorm_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    await send_message(message, 'dorms_list', language)

async def main():
    load_questions()
    load_dorms()
    load_feedbacks()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

from adds import *

TOKEN = ''
bot = ''
dp = Dispatcher()

questions = {}
users = Users()
dorms = {}

conn = sqlite3.connect('main.db')
conn.isolation_level = None
cursor = sqlite3.Cursor(conn)


def load_token():
    global TOKEN, bot
    with open('TOKEN.txt', 'r') as f:
        TOKEN = f.readline().replace('\n', '')
        bot = Bot(TOKEN)


def load_users():
    for user in cursor.execute(GET_USERS).fetchall():
        users.add_user(User(*user))


def load_questions():
    for question in cursor.execute(GET_QUESTIONS).fetchall():
        questions[question[0]] = Question(*question)
    ru_text = '\n'.join(map(lambda question: f'{question.id}: {question.ru_text}', questions.values()))
    en_text = '\n'.join(map(lambda question: f'{question.id}: {question.en_text}', questions.values()))
    texts['faq_list'][RUS] = texts['faq_list'][RUS].format(questions=ru_text)
    texts['faq_list'][ENG] = texts['faq_list'][ENG].format(questions=en_text)


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
    feedbacks_by_rate.sort(key=lambda feedback: feedback.grade_avg)
    feedbacks_by_rate = dict(zip(range(1, len(feedbacks_by_rate) + 1), feedbacks_by_rate))
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
    cursor.execute(UPDATE_LANGUAGE, (lang, tg_id))
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
    command = callback_data.command
    language = users.get_user(tg_id).get_language()

    if command == "review":
        kb = keyboards['dorm_reviews_sort'][language]
        await callback.message.edit_text(text=texts['dorm_reviews_sort'][language], reply_markup=kb)

    if command == "send_review":
        await callback.message.edit_text(text=texts['sent_feedback'][language])
        kb = await feedback_write_kb_gen(RATE_TRANSPORT)
        await callback.message.answer(text=texts[RATE_TRANSPORT][language], reply_markup=kb)

    if command == "back":
        kb = keyboards['dorms_list'][language]
        await callback.message.edit_text(text=texts['dorms_list'][language], reply_markup=kb)


@dp.callback_query(RateCb.filter())
async def rate_filter(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    current_param = callback_data.current_param
    rate = callback_data.rate
    user = users.get_user(tg_id)
    language = user.get_language()
    user.set_rate(rate, current_param)
    if current_param != RATE_INFRASTRUCTURE:
        kb = await feedback_write_kb_gen(current_param + 1)
        await callback.message.edit_text(texts[current_param + 1][language], reply_markup=kb)
    else:
        rates = user.get_rate()
        avg = sum(rates.values()) / len(rates.values())
        user.set_rate(avg, RATE_AVG)
        await callback.message.edit_text(
            texts['rate_write_text'][language].format(r1=rates[RATE_TRANSPORT], r2=rates[RATE_STAFF],
                                                      r3=rates[RATE_PRIVATE], r4=rates[RATE_PUBLIC],
                                                      r5=rates[RATE_INFRASTRUCTURE], avg=avg))
        user.set_state(FEEDBACK_WRITING_STATE)


@dp.callback_query(ReviewsSortCb.filter())
async def change_filter(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    command = callback_data.command
    language = users.get_user(tg_id).get_language()
    dorm_number = users.get_user(tg_id).get_dorm_number()
    user = users.get_user(tg_id)
    kb = keyboards['dorm_reviews'][language]
    feedback_number = -1
    sorter_parameter = -1

    if command in ('new', 'positive'):
        feedback_number = len(feedbacks_by_time)
    elif command in ('old', 'negative'):
        feedback_number = 1
    user.set_feedback_number(feedback_number)

    if command in ('negative', 'positive'):
        sorter_parameter = 1
    elif command == 'new':
        sorter_parameter = 2
    elif command == 'old':
        sorter_parameter = 0
    user.set_sorter_parameter(sorter_parameter)

    if command == 'new':
        sorter_parameter -= 2
    feedback = res[sorter_parameter][feedback_number]

    if language == RUS:
        if language != feedback.language:
            await callback.message.edit_text(
                text=texts['dorm_reviews'][language].format(review=feedback.ru_text, transport=feedback.grade_transport,
                                                            staff=feedback.grade_staff, private=feedback.grade_private,
                                                            public=feedback.grade_public,
                                                            infrastructure=feedback.grade_infrastructure,
                                                            average=feedback.grade_avg) + "\n (Отзыв переведен автоматически и может содержать ошибки)",
                reply_markup=kb)
        else:
            await callback.message.edit_text(
                text=texts['dorm_reviews'][language].format(review=feedback.ru_text, transport=feedback.grade_transport,
                                                            staff=feedback.grade_staff, private=feedback.grade_private,
                                                            public=feedback.grade_public,
                                                            infrastructure=feedback.grade_infrastructure,
                                                            average=feedback.grade_avg), reply_markup=kb)
    else:
        if language != feedback.language:
            await callback.message.edit_text(
                text=texts['dorm_reviews'][language].format(review=feedback.en_text, transport=feedback.grade_transport,
                                                            staff=feedback.grade_staff, private=feedback.grade_private,
                                                            public=feedback.grade_public,
                                                            infrastructure=feedback.grade_infrastructure,
                                                            average=feedback.grade_avg) + "\n (Feeadback was automatically translated and may contain mistakes)",
                reply_markup=kb)
        else:
            await callback.message.edit_text(
                text=texts['dorm_reviews'][language].format(review=feedback.en_text, transport=feedback.grade_transport,
                                                            staff=feedback.grade_staff, private=feedback.grade_private,
                                                            public=feedback.grade_public,
                                                            infrastructure=feedback.grade_infrastructure,
                                                            average=feedback.grade_avg), reply_markup=kb)

    if command == "back":
        kb = keyboards['dorm_info'][language]
        if language == RUS:
            await callback.message.edit_text(text=dorms[dorm_number].ru_description, reply_markup=kb)
        else:
            await callback.message.edit_text(text=dorms[dorm_number].en_description, reply_markup=kb)


@dp.callback_query(ReviewsCb.filter())
async def scrolling_reviews(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    command = callback_data.command
    language = users.get_user(tg_id).get_language()
    sorter_parameter = users.get_user(tg_id).get_sorter_parameter()
    feedback_number = users.get_user(tg_id).get_feedback_number()
    user = users.get_user(tg_id)

    if sorter_parameter in (FEEDBACK_SORT_TIME_RIGHT, FEEDBACK_SORT_GRADE_RIGHT):
        if command == "next":
            if feedback_number == len(feedbacks_by_rate):
                feedback_number = 1
            else:
                feedback_number += 1

        elif command == "last":
            if feedback_number == 1:
                feedback_number = len(feedbacks_by_rate)
            else:
                feedback_number -= 1

        feedback = res[sorter_parameter][feedback_number]

    else:
        if command == "last":
            if feedback_number == len(feedbacks_by_rate):
                feedback_number = 1
            else:
                feedback_number += 1

        elif command == "next":
            if feedback_number == 1:
                feedback_number = len(feedbacks_by_rate)
            else:
                feedback_number -= 1

        feedback = res[sorter_parameter - 2][feedback_number]

    user.set_feedback_number(feedback_number)
    kb = keyboards['dorm_reviews'][language]

    if command in ('last', 'next'):
        if language == RUS:
            await callback.message.edit_text(
                text=texts['dorm_reviews'][language].format(review=feedback.ru_text, transport=feedback.grade_transport,
                                                            staff=feedback.grade_staff, private=feedback.grade_private,
                                                            public=feedback.grade_public,
                                                            infrastructure=feedback.grade_infrastructure,
                                                            average=feedback.grade_avg), reply_markup=kb)
        else:
            await callback.message.edit_text(
                text=texts['dorm_reviews'][language].format(review=feedback.en_text, transport=feedback.grade_transport,
                                                            staff=feedback.grade_staff, private=feedback.grade_private,
                                                            public=feedback.grade_public,
                                                            infrastructure=feedback.grade_infrastructure,
                                                            average=feedback.grade_avg), reply_markup=kb)
    elif command == "back":
        kb = keyboards['dorm_reviews_sort'][language]
        await callback.message.edit_text(text=texts['dorm_reviews_sort'][language], reply_markup=kb)
    elif command == 'ask':
        await callback.message.edit_text(text=texts['ask_author'][language])
        user.set_state(AUTHOR_ASK_STATE)


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


@dp.callback_query(FeedbackFinishCb.filter())
async def feedback_finish(callback: CallbackQuery, callback_data: CallbackData):
    tg_id = callback.message.chat.id
    user = users.get_user(tg_id)
    language = user.get_language()
    command = callback_data.command
    if command == 'text':
        await callback.message.edit_text(texts['edit_text'][language])
    elif command == 'rate':
        kb = await feedback_write_kb_gen(RATE_TRANSPORT)
        await callback.message.answer(text=texts[RATE_TRANSPORT][language], reply_markup=kb)
    elif command == 'cancel':
        kb = keyboards['dorms_list'][language]
        await callback.message.edit_text(text=texts['dorms_list'][language], reply_markup=kb)
    elif command == 'confirm':
        rates = user.get_rate()
        text = user.get_text()
        for_translate = text.replace(' ', '%20')
        dorm_id = user.get_dorm_number()
        data = requests.get(TRANSLATE_LINK_EN_RU + for_translate).json()
        ru_text = data['destination-text']
        if data['source-language'] == 'en':
            text_lang = ENG
            en_text = text
        else:
            text_lang = RUS
            await asyncio.sleep(0.2)
            en_text = requests.get(TRANSLATE_LINK_RU_EN + for_translate).json()['destination-text']

        cursor.execute(CREATE_FEEDBACK, (
            dorm_id, ru_text, rates[RATE_AVG], text_lang, en_text, rates[RATE_STAFF], rates[RATE_PRIVATE],
            rates[RATE_INFRASTRUCTURE], rates[RATE_PUBLIC], rates[RATE_TRANSPORT], 0, user.is_verified(), user.id))
        await callback.message.edit_text(text=texts['feedback_confirmed'][language])
        user.set_state(DEFAULT_STATE)


@dp.message(lambda message: not users.check_existence(message.chat.id))
async def new_user(message: Message):
    tg_id = message.chat.id
    user = User(tg_id)
    users.add_user(user)
    cursor.execute(CREATE_USER, (tg_id, RUS))
    await send_message(message, 'language_choose', RUS)


@dp.message(lambda message: users.get_user(message.chat.id).get_state() == FEEDBACK_WRITING_STATE)
async def feedback_text_handler(message: Message):
    user = users.get_user(message.chat.id)
    language = user.get_language()
    feedback_text = message.text
    kb = keyboards['confirm_feedback'][language]
    user.set_text(feedback_text)
    await message.answer(texts['confirm_feedback'][language], reply_markup=kb)


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
    load_users()
    load_token()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

from bot.config import CreditPack
from bot.copy import Copy

COPY = Copy(
    locale="ru",
    brand_name="Моя примерка",
    tagline="Увидь себя в этом",
    welcome_new=(
        "Хочешь увидеть, как этот образ смотрится на *тебе*?\n\n"
        "Давай соберём твою личную примерочную ✨\n"
        "Загрузи своё фото — или сначала открой 📸 Гайд по фото."
    ),
    welcome_back=(
        "С возвращением в Мою примерку! У тебя {balance} кредит(ов).\n"
        "Отправь фото одежды или выбери действие в меню."
    ),
    demo_caption=(
        "Примерь любой образ на себе — до покупки ✨\n"
        "Слева: твоё фото + одежда. Справа: результат."
    ),
    photo_ready=(
        "Твоя примерочная готова 🎉\n"
        "У тебя *{free_credits} бесплатные примерки*. Отправь фото одежды!"
    ),
    generating="Примеряем образ… ~15 секунд ✨",
    result_caption="Вот как *ты* выглядишь в этом образе.",
    paywall=(
        "Бесплатные примерки закончились — но последний образ того стоил 🔥\n"
        "Хочешь примерить ещё перед покупкой?"
    ),
    deficit="Кредиты закончились! *5 примерок за 50⭐* — займёт 5 секунд.",
    privacy_note=(
        "🔒 Фото хранятся безопасно и используются только для примерки. "
        "Удалить можно командой /delete_my_data"
    ),
    drip_opt_out="Отключить напоминания",
    guide_caption=(
        "*Гайд по фото для лучшего результата*\n\n"
        "✅ *В полный рост* • *Хороший свет* • *Нейтральный фон* • *Одежда отдельно*\n\n"
        "⚠️ Одежда на модели тоже подойдёт, но результат будет менее точным."
    ),
    guide_text_fallback=(
        "📸 *Гайд по фото*\n\n"
        "👤 *Твоё фото — ДА:* в полный рост, лицом к камере, руки видны, "
        "хороший свет, нейтральный фон.\n\n"
        "👤 *НЕТ:* обрезанное, размытое, тёмное или сбоку.\n\n"
        "👗 *Одежда — ДА:* вещь отдельно на нейтральном фоне, чётко и хорошо освещена.\n\n"
        "👗 *НЕТ:* пёстрый фон или несколько вещей. "
        "На модели тоже можно, но лучше — отдельно."
    ),
    guide_next_person="Отлично — теперь отправь сюда своё фото в полный рост 📷",
    guide_next_garment="Готово! Теперь отправь фото одежды, чтобы увидеть её на себе 👗",
    try_another="Примерить ещё? 👗",
    low_balance="⚠️ Осталось {count} примерок",
    invite_text=(
        "Приглашай друзей — получи +1 кредит, когда друг завершит первую примерку."
    ),
    share_inline_query="Смотри, как на мне! Примерь сам →",
    btn_try_on="Примерить одежду",
    btn_balance="Мой баланс",
    btn_buy="Купить кредиты",
    btn_my_photos="📷 My photos",
    btn_see_on_me="✨ See it on me",
    btn_add_item="➕ Add another item",
    btn_clear_look="🗑 Clear look",
    btn_help="Помощь",
    btn_photo_guide="📸 Гайд по фото",
    btn_upload_person="📷 Загрузить моё фото",
    btn_choose_outfit="👗 Выбрать образ",
    btn_try_another="👗 Примерить ещё",
    btn_invite="💫 Пригласить друзей",
    btn_share="📤 Поделиться с друзьями",
    btn_buy_credits="⭐ Купить кредиты",
    btn_style_guide="✨ What to pair with this",
    style_guide_offer=(
        "Love this look? 🔥 Get a style board for this piece — "
        "what to pair, colors & accessories. *1 try-on.*"
    ),
    style_guide_generating="Putting your style board together… about 20 sec ✨",
    style_guide_caption="Your style board — pairings, colors & accessories for this look 👗",
    style_guide_already="You've already got a style board for this look 👇",
    style_guide_failed=(
        "That one didn't come through — and I've refunded your try-on. "
        "Mind giving it another go?"
    ),
    style_guide_not_found=(
        "I can't find that try-on anymore. Send a clothing photo and let's style something new 👗"
    ),
    shop_most_chosen="Популярный выбор",
    help_text=(
        "Как работает Моя примерка:\n"
        "1. Загрузи одно фото себя в полный рост.\n"
        "2. Отправь фото одежды — увидишь образ на себе.\n"
        "3. Каждый образ — 1 примерка.\n\n"
        "*После примерки*\n"
        "Нажми ✨ What to pair with this — стиль-борд: с чем носить, цвета и аксессуары (1 примерка).\n\n"
        "Советы для лучшего результата:\n"
        "• Стоя прямо, руки видны, хорошее освещение.\n"
        "• Нейтральный фон на фото.\n"
        "• Фото одежды — вещь чётко на однотонном фоне.\n\n"
        "Команды:\n"
        "/start — начать заново\n"
        "/guide — гайд по фото\n"
        "/balance — проверить баланс\n"
        "/shop — купить кредиты за Telegram Stars\n"
        "/photos — загрузить фото заново"
    ),
    balance_text="Баланс: {balance} кредит(ов).\n1 кредит = 1 примерка.",
    balance_line="1 кредит = 1 примерка.",
    try_on_hint="Отправь фото одежды. Стоимость: 1 кредит. Баланс: {balance}.",
    circuit_open=(
        "Сервис примерки временно недоступен. Попробуй через несколько минут."
    ),
    concurrent="Примерка уже идёт. Подожди, пока текущая завершится.",
    not_enough_credits="Недостаточно кредитов.",
    generation_failed="Не удалось примерить. Кредит возвращён.\n{error}",
    photo_too_small="Hmm, that photo's a little small to work with. Send a clearer one (at least 256px wide) and we're good 📷",
    photo_bad_format="I couldn't open that image. Send it as a JPG or PNG photo and I'll take it from there 📷",
    garment_too_small="That item photo's a bit small. Send a clearer product shot and I'll style it on you 👗",
    send_start_first="Сначала отправь /start.",
    upload_photos_first="Сначала загрузи фото. Отправь /start для онбординга.",
    no_saved_photos="Сохранённых фото нет. Отправь /photos для загрузки.",
    photo_limit_reached=(
        "Лимит фото ({limit}). Для примерки используется последнее сохранённое фото."
    ),
    photo_saved_send_garment="Фото сохранено. Отправь фото одежды для примерки.",
    photo_progress_optional=(
        "Фото обновлено ({count}/{limit}). "
        "Отправь фото одежды или загрузи ещё одно."
    ),
    reupload_prompt=(
        "Отправь новые фото (до {limit} шт.). "
        "Последнее фото станет основным для примерки."
    ),
    delete_confirmation="Все твои фото и данные удалены.",
    stop_reminders="Напоминания отключены. Больше не будем писать.",
    stop_reminders_done="Больше не будем присылать напоминания.",
    shop_header="Купи кредиты за Telegram Stars:",
    shop_credit_line="1 кредит = 1 примерка.",
    invoice_description="Кредиты на виртуальную примерку в Моей примерке.",
    invoice_credits_title="{credits} кредитов на примерку",
    payment_success=(
        "Оплата прошла! +{credits} кредитов.\nНовый баланс: {balance}."
    ),
    payment_duplicate="Оплата уже обработана. Баланс: {balance} кредит(ов).",
    credit_packs=(
        CreditPack(id="single", credits=1, stars=20, label="Разовая — 1 примерка"),
        CreditPack(id="starter", credits=5, stars=50, label="Старт — 5 примерок"),
        CreditPack(
            id="popular",
            credits=15,
            stars=120,
            label="Популярная — 15 примерок",
            highlight=True,
        ),
        CreditPack(id="best", credits=40, stars=250, label="Выгодная — 40 примерок"),
    ),
    drip_messages={
        "T1": (
            "Ещё думаешь об том образе? Отправь следующую вещь — "
            "осталось {balance} бесплатных примерок 👗"
        ),
        "T2": (
            "Образ отлично смотрелся на тебе. Примерь ещё 3 перед покупкой — "
            "пакет Популярная 120⭐"
        ),
        "T3": "Твоя примерочная ждёт — посмотри, как сядет следующий образ 👗",
        "T4": (
            "Покупатели любят примерять до покупки. Пакет Старт — 5 примерок за 50⭐"
        ),
        "T5": "Кредиты закончились! *5 примерок за 50⭐* — займёт 5 секунд.",
        "T6": (
            "Кредиты на исходе — осталось {balance} примерок. "
            "Пополни баланс перед следующим образом 👗"
        ),
        "T7": (
            "Мы скучаем! Возвращайся и примерь что-нибудь новое — "
            "разовая примерка за 10⭐ сегодня"
        ),
        "post_purchase_upsell": (
            "Нравится примерять? Перейди на *Популярная — 15 примерок* "
            "всего за +70⭐ к Старту!"
        ),
    },
    referral_returning="С возвращением! У тебя {balance} кредит(ов).\nОтправь фото одежды или выбери действие в меню.",
    look_item_added=(
        "Got it — {count} item(s) in your look 👗\n"
        "Using Photo {active_slot} ✓ · 1 try-on when you're ready"
    ),
    look_one_item_hint="Add more for a full look, or see it on you now.",
    look_full="Look full — 5 items 🔥",
    look_cleared="Look cleared — send clothing photos when you're ready 👗",
    look_generating_one="Putting it on you… about 15 sec ✨",
    look_generating_many="Putting your look on you… about 20 sec ✨",
    photo_switched="Photo {slot} is now your active photo 👍",
    gallery_header=(
        "*My photos* ({count}/5)\nActive for try-ons: Photo {active_slot} ✓"
    ),
    try_on_hint_v2=(
        "Send clothing photos — one or several 👗\n"
        "Using Photo {active_slot} ✓ · add items, then See it on me · 1 try-on"
    ),
    person_photo_in_tryon="Looks like a photo of you — add it to My photos?",
    welcome_back_draft_look="Welcome back 👋\nYou have a look waiting — {count} items.",
)

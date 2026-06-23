import random
from datetime import time, datetime, timezone, date

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes

from config import OWNER_USERNAME, ACTIVITY_CHAT_INVITE, ACTIVITY_CHAT_ID, ADMIN_IDS
from database import (
    track_message, get_top_users, get_total_messages,
    get_random_gift, log_giveaway, is_giveaway_done, set_giveaway_done,
    get_or_create_user,
)

GIFT_CAPTIONS = {
    "Мишка": [
        "🧸 {name} получает {gift} за актив в чате!",
        "🧸 {name} — твой {gift} уже ждет тебя!",
        "🧸 {name} забирает {gift}! Так держать!",
        "🧸 {name} выиграл {gift} за активность!",
    ],
    "Сердечко": [
        "❤️ {name} получает {gift} за актив в чате!",
        "❤️ {name} — твое {gift} уже ждет!",
        "❤️ {name} забирает {gift}! Спасибо за актив!",
        "❤️ {name} выиграл {gift}! Ты в сердечке!",
    ],
    "Роза": [
        "🌹 {name} срывает {gift} за {stars} звезд! Шикарно!",
        "🌹 {name} получает {gift} за {stars} звезд!",
        "🌹 {name} — твой {gift}! Красота!",
        "🌹 {name} выиграл {gift} за актив!",
    ],
    "Подарок": [
        "🎁 {name} открывает {gift} за {stars} звезд!",
        "🎁 {name} — твой {gift} уже тут!",
        "🎁 {name} получает {gift} за актив! Интрига!",
        "🎁 {name} выиграл {gift}! Что внутри?",
    ],
    "Ракета": [
        "🚀 {name} улетает в космос с {gift} за {stars} звезд!",
        "🚀 Поздравляем {name} с выигрышем {gift}! Космос ждет!",
        "🚀 {name} — твоя ракета {gift} отправляется к звездам!",
    ],
    "Торт": [
        "🎂 {name} получает сладкий {gift} за {stars} звезд!",
        "🎂 {name} — твой {gift} уже в пути! Сладкого настроения!",
        "🎂 Сладкий приз {gift} улетает к {name}!",
    ],
    "Букет": [
        "💐 {name} выиграл шикарный {gift} за {stars} звезд!",
        "💐 Цветы для {name}! {gift} за актив в чате!",
        "💐 {name} — твой {gift} уже забирай!",
    ],
    "Кольцо": [
        "💍 {name} срывает джекпот — {gift} за {stars} звезд!",
        "💍 {name} — бриллиант среди активных! {gift} твой!",
        "💍 {name} получает {gift} за {stars} звезд! Шикарно!",
    ],
    "Кубок": [
        "🏆 {name} — чемпион дня! {gift} за {stars} звезд!",
        "🏆 {name} забирает {gift}! Ты лучший в чате!",
        "🏆 Победитель {name} получает {gift}!",
    ],
    "Алмаз": [
        "💎 {name} нашел {gift} за {stars} звезд! Настоящий бриллиант!",
        "💎 {name} — {gift} твой! Сияй ярче всех!",
        "💎 Драгоценный приз {gift} уходит к {name}!",
    ],
}

JACKPOT_CHANCE = 0.1
GOOD_DROP_CHANCE = 0.4
X2_EVENT_CHANCE = 0.05

JACKPOT_CAPTIONS = [
    "🎉 ДЖЕКПОООТ!",
    "🎉 ДЖЕКПОТ! СУПЕР ПРИЗ!",
    "🎉 ГЛАВНЫЙ ПРИЗ! ДЖЕКПОТ!",
    "🎉 ДЖЕКПОООТ СЕГОДНЯ!",
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username or "", user.first_name or "")
    text = (
        f"Владелец: {OWNER_USERNAME}\n"
        f"Чат где раздают подарки за актив: {ACTIVITY_CHAT_INVITE}"
    )
    await update.message.reply_text(text, disable_web_page_preview=True)


async def track_chat_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ACTIVITY_CHAT_ID:
        return
    if update.effective_user.is_bot:
        return
    user = update.effective_user
    track_message(user.id, update.effective_chat.id, user.username or "", user.first_name or "")


async def daily_giveaway(context: ContextTypes.DEFAULT_TYPE):
    chat_id = ACTIVITY_CHAT_ID
    if not chat_id or chat_id <= 0:
        return

    if is_giveaway_done(chat_id):
        return

    top = get_top_users(chat_id, limit=25)
    total = get_total_messages(chat_id)

    today_str = date.today().strftime("%d.%m.%Y")
    lines = [f"📊 Стата день | {today_str}\n"]
    for i, u in enumerate(top, 1):
        name = f"@{u['username']}" if u["username"] else u["first_name"]
        lines.append(f"{i}. {name} — {u['message_count']} сообщений")
    lines.append(f"\nВсего сообщений: {total}")
    lines.append(f"Всего мест: 25")

    stats_text = "\n".join(lines)
    await context.bot.send_message(chat_id=chat_id, text=stats_text)

    if len(top) < 1:
        return

    is_x2 = random.random() < X2_EVENT_CHANCE
    if is_x2:
        x2_text = "🔥 Х2 ИВЕНТ! 🔥\nСегодня дарим в 2 раза больше подарков!\n"
        await context.bot.send_message(chat_id=chat_id, text=x2_text)

    top_10 = top[:10]
    winner_data = random.choice(top_10)
    winner_id = winner_data["user_id"]
    winner_name = f"@{winner_data['username']}" if winner_data["username"] else winner_data["first_name"]

    gift_count = 2 if is_x2 else 1
    announcements = []

    for _ in range(gift_count):
        roll = random.random()
        if roll < JACKPOT_CHANCE:
            gift = get_random_gift(min_stars=50)
            tier = "jackpot"
        elif roll < JACKPOT_CHANCE + GOOD_DROP_CHANCE:
            gift = get_random_gift(min_stars=25, max_stars=25)
            tier = "good"
        else:
            gift = get_random_gift(max_stars=15)
            tier = "regular"
        if not gift:
            continue

        log_giveaway(winner_id, gift["gift_id"], chat_id)

        emoji = gift["emoji"]
        gname = gift["name"]
        stars = gift["star_cost"]

        captions = GIFT_CAPTIONS.get(gname, ["🎁 {name} выиграл {gift}!"])
        caption = random.choice(captions).format(name=winner_name, gift=gname, stars=stars, emoji=emoji)

        if tier == "jackpot":
            jackpot_line = random.choice(JACKPOT_CAPTIONS)
            msg = (
                f"{jackpot_line}\n"
                f"{caption}\n"
                f"от {OWNER_USERNAME}\n"
                f"✅ Подарок отправлен."
            )
        else:
            msg = caption

        announcements.append(msg)

    set_giveaway_done(chat_id)

    for msg in announcements:
        await context.bot.send_message(chat_id=chat_id, text=msg)

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"👤 {winner_name} (ID:{winner_id}) выиграл {gift_count} подарок(а) за актив!\n"
                     f"Сообщений: {winner_data['message_count']}\n"
                     f"{'🔥 Х2 ИВЕНТ!' if is_x2 else ''}\n"
                     f"Отправь ему подарок!",
            )
        except Exception:
            pass


def get_handlers():
    return [
        CommandHandler("start", start),
        MessageHandler(filters.TEXT & ~filters.COMMAND, track_chat_messages),
    ]


def schedule_jobs(app):
    jq = app.job_queue
    if jq:
        jq.run_daily(
            daily_giveaway,
            time=time(hour=20, minute=59, second=0, tzinfo=timezone.utc),
            name="daily_giveaway",
        )

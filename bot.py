import telebot
import random
import string
import json
from pathlib import Path

TOKEN = "8250941489:AAEUlIUmBVMF2yr6uq-b9qmrpmnmLw0gUcg"
bot = telebot.TeleBot(TOKEN)

GAME_URL = "https://shiny-axolotl-474a61.netlify.app"
STATS_FILE = Path("stats.json")


def load_stats():
    if STATS_FILE.exists():
        try:
            data = json.loads(STATS_FILE.read_text())
            data.setdefault("started_users", [])
            data.setdefault("play_users", [])
            data.setdefault("codes", 0)
            data.setdefault("play_clicks", 0)
            data.setdefault("paid_users", [])
            data.setdefault("payments", 0)
            data.setdefault("paid_amount", 0)
            data.setdefault("paid_currency", None)
            return data
        except Exception:
            pass

    return {
        "started_users": [],
        "play_users": [],
        "codes": 0,
        "play_clicks": 0,
        "paid_users": [],
        "payments": 0,
        "paid_amount": 0,
        "paid_currency": None,
    }


def save_stats():
    try:
        STATS_FILE.write_text(json.dumps(stats))
    except Exception:
        pass


def track_started(user_id: int):
    if user_id not in stats["started_users"]:
        stats["started_users"].append(user_id)
        save_stats()


def track_play(user_id: int):
    stats["play_clicks"] += 1
    stats["codes"] += 1

    if user_id not in stats["play_users"]:
        stats["play_users"].append(user_id)

    save_stats()


def track_paid(user_id: int, amount: int = None, currency: str = None):
    stats.setdefault("payments", 0)
    stats.setdefault("paid_users", [])
    stats.setdefault("paid_amount", 0)

    stats["payments"] += 1

    if amount is not None:
        try:
            stats["paid_amount"] += int(amount)
        except Exception:
            pass

    if currency is not None:
        stats["paid_currency"] = currency

    if user_id not in stats["paid_users"]:
        stats["paid_users"].append(user_id)

    save_stats()


def generate_code():
    return "LS-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )


stats = load_stats()


@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    text = (
        "📊 Статистика:\n"
        f"👤 /start: {len(set(stats['started_users']))}\n"
        f"🎮 Play: {len(set(stats['play_users']))}\n"
        f"💰 Payments: {stats.get('payments', 0)}\n"
        f"💸 Paid users: {len(set(stats.get('paid_users', [])))}\n"
        f"💵 Paid amount: {stats.get('paid_amount', 0)} {stats.get('paid_currency', '')}\n"
        f"🎟 Codes: {stats['codes']}\n"
        f"⬇️ Play clicks: {stats['play_clicks']}"
    )

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["start"])
def start(message):
    track_started(message.from_user.id)

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Play — 50 Stars")

    bot.send_message(
        message.chat.id,
        "🎰 Welcome to Last Spin\nPress Play",
        reply_markup=markup,
    )


@bot.message_handler(func=lambda m: m.text and "play" in m.text.lower())
def play(message):
    track_play(message.from_user.id)

    code = generate_code()
    url = f"{GAME_URL}/?code={code}"

    bot.send_message(
        message.chat.id,
        f"🎟 Code:\n{code}\n\n👉{url}",
    )


@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def successful_payment(message):
    p = message.successful_payment
    amount = getattr(p, "total_amount", None)
    currency = getattr(p, "currency", None)

    track_paid(message.from_user.id, amount=amount, currency=currency)

    bot.send_message(
        message.chat.id,
        "✅ Платеж получен. Теперь нажмите Play.",
    )


bot.remove_webhook()

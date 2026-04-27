import os
import time
import random
import string
import telebot
from telebot.types import LabeledPrice

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")

bot = telebot.TeleBot(TOKEN)

users = {}

GAME_LINK = "https://shiny-axolotl-474a61.netlify.app/"


def generate_code():
    return "LS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


@bot.message_handler(commands=["start"])
def start(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🎰 1 Hour — 50 Stars")
    keyboard.add("⏱ 24 Hours — 150 Stars")
    keyboard.add("🔥 7 Days — 300 Stars")
    keyboard.add("📌 My Access")

    bot.send_message(
        message.chat.id,
        "🎰 Welcome to Ancient Roulette\n\n"
        "Choose your access:\n\n"
        "• 1 Hour — 50 Stars\n"
        "• 24 Hours — 150 Stars\n"
        "• 7 Days — 300 Stars\n\n"
        "Training simulator only.\n"
        "No real money gambling.\n"
        "No cash prizes.\n"
        "No withdrawals.",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda m: m.text in [
    "🎰 1 Hour — 50 Stars",
    "⏱ 24 Hours — 150 Stars",
    "🔥 7 Days — 300 Stars"
])
def buy_access(message):
    if message.text == "🎰 1 Hour — 50 Stars":
        stars = 50
        payload = "access_1h"
        title = "1 Hour Access"

    elif message.text == "⏱ 24 Hours — 150 Stars":
        stars = 150
        payload = "access_24h"
        title = "24 Hours Access"

    else:
        stars = 300
        payload = "access_7d"
        title = "7 Days Access"

    prices = [LabeledPrice(label=title, amount=stars)]

    bot.send_invoice(
        chat_id=message.chat.id,
        title="Ancient Roulette Access",
        description=title,
        invoice_payload=payload,
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="ancient_roulette"
    )


@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def payment_success(message):
    user_id = message.chat.id
    payload = message.successful_payment.invoice_payload

    if payload == "access_1h":
        duration = 3600
        access_name = "1 hour"

    elif payload == "access_24h":
        duration = 86400
        access_name = "24 hours"

    elif payload == "access_7d":
        duration = 604800
        access_name = "7 days"

    else:
        bot.send_message(user_id, "Payment received, but access type is unknown.")
        return

    code = generate_code()
    expires_at = time.time() + duration

    users[user_id] = {
        "code": code,
        "expires_at": expires_at
    }

    bot.send_message(
        user_id,
        "✅ Payment successful!\n\n"
        f"Access activated for {access_name}.\n\n"
        f"Your access code:\n{code}\n\n"
        f"Open game:\n{GAME_LINK}"
    )


@bot.message_handler(commands=["status"])
@bot.message_handler(func=lambda m: m.text == "📌 My Access")
def my_access(message):
    user_id = message.chat.id
    data = users.get(user_id)

    if not data:
        bot.send_message(
            user_id,
            "❌ You do not have active access.\n\n"
            "Please buy access from the menu."
        )
        return

    if time.time() > data["expires_at"]:
        bot.send_message(
            user_id,
            "❌ Your access has expired.\n\n"
            "Please buy access again."
        )
        return

    minutes_left = int((data["expires_at"] - time.time()) / 60)

    bot.send_message(
        user_id,
        "✅ Your access is active.\n\n"
        f"Code: {data['code']}\n"
        f"Time left: {minutes_left} minutes\n\n"
        f"Game link:\n{GAME_LINK}"
    )


@bot.message_handler(func=lambda message: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "Please choose an option from the menu or type /start."
    )


bot.infinity_polling()

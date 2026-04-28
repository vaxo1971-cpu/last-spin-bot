import telebot
import random
import string
import requests

TOKEN = "8250941489:AAEYE7VT3F4MAPY52d2xR1F8QmLRbmxOw7o"
API_URL = "https://last-spin-api.onrender.com"

bot = telebot.TeleBot(TOKEN)

def generate_code():
    return "LS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Play — 50 Stars")

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
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "Play — 50 Stars")
def play(message):
    code = generate_code()

    try:
        requests.post(
            f"{API_URL}/add-code",
            json={"code": code},
            timeout=10
        )
    except Exception:
        pass

    bot.send_message(
        message.chat.id,
        f"✅ Your access code:\n\n{code}\n\n"
        "Open the game and enter this code:\n"
        "https://radiant-khapse-1ccf0a.netlify.app/"
    )

bot.infinity_polling()

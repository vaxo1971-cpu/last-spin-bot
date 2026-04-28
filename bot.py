import os
import random
import string
import telebot
from flask import Flask, request

TOKEN = "8250941489:AAEUlIUmBVMF2yr6uq-b9qmrpmnmLw0gUcg"
WEBHOOK_URL = "https://last-spin-bot.onrender.com"

GAME_URL = "https://shiny-axolotl-474a61.netlify.app"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


def generate_code():
    return "LS-" + ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )


@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Play — 50 Stars")

    bot.send_message(
        message.chat.id,
        "🎰 Welcome to Last Spin\nPress Play",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text and "play" in m.text.lower())
def play(message):
    code = generate_code()
    url = f"{GAME_URL}/?code={code}"

    bot.send_message(
        message.chat.id,
        f"🎟 Code:\n{code}\n\n👉 {url}"
    )


@app.route("/", methods=["GET"])
def home():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


bot.remove_webhook()
bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

import os
import telebot
from telebot import types
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is not set")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

GAME_URL = "https://shiny-axolotl-474a61.netlify.app/"


@bot.message_handler(commands=["start"])
def start(message):
    keyboard = types.InlineKeyboardMarkup()

    button = types.InlineKeyboardButton(
        text="🎰 Open Ancient Roulette",
        web_app=types.WebAppInfo(url=GAME_URL)
    )

    keyboard.add(button)

    bot.send_message(
        message.chat.id,
        "🎰 Welcome to Last Spin — Ancient Roulette\n\n"
        "Training simulator only:\n"
        "• No real money gambling\n"
        "• No cash prizes\n"
        "• No withdrawals\n"
        "• Virtual balance only\n\n"
        "Press the button below to open the game.",
        reply_markup=keyboard
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

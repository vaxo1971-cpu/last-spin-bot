import telebot
import random
import string

TOKEN = "8250941489:AAEUlIUmBVMF2yr6uq-b9qmrpmnmLw0gUcg"

bot = telebot.TeleBot(TOKEN)

GAME_URL = "https://shiny-axolotl-474a61.netlify.app"

def generate_code():
    return "LS-" + ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )

@bot.message_handler(commands=['start'])
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

bot.remove_webhook()
bot.infinity_polling()

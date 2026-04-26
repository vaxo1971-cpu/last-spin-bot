import telebot
import random
import string

TOKEN = "8250941489:AAG9wLq71wpbcwh3CTkS57DehPG8YIWdoZs"

bot = telebot.TeleBot(TOKEN)

def generate_code():
    return "LS-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Play — 50 Stars")
    bot.send_message(message.chat.id, "🎰 Welcome to Last Spin\nPress Play", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Play — 50 Stars")
def play(message):
    code = generate_code()
    bot.send_message(message.chat.id, f"Your code:\n{code}")

bot.infinity_polling()

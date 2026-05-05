import os
import json
import time
import threading
from pathlib import Path

import telebot
from telebot import types
from flask import Flask, request, jsonify

# ================== НАСТРОЙКИ ==================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
GAME_URL = os.getenv(
    "WEBAPP_URL",
    "https://aquamarine-strudel-14e0ed.netlify.app"
).strip().rstrip("/")

# Твой Telegram ID — администратор
ADMIN_IDS = {5274220765}

# Обычные игроки играют 5 минут бесплатно на сайте.
# После этого сайт покажет оплату.
TRIAL_TIME = 300

DATA_FILE = Path("users_access.json")

PRICES = {
    "1h": {
        "title": "1 Hour Access",
        "stars": 50,
        "seconds": 60 * 60,
        "text": "⏱ 1 час / 1 hour / 1 საათი — 50⭐",
    },
    "24h": {
        "title": "24 Hours Access",
        "stars": 150,
        "seconds": 24 * 60 * 60,
        "text": "📅 24 часа / 24 hours / 24 საათი — 150⭐",
    },
    "48h": {
        "title": "48 Hours Access",
        "stars": 300,
        "seconds": 48 * 60 * 60,
        "text": "🔥 48 часов / 48 hours / 48 საათი — 300⭐",
    },
}

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add BOT_TOKEN in Render Environment.")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)


# ================== ХРАНЕНИЕ ==================

def load_data():
    if not DATA_FILE.exists():
        return {"users": {}, "paid": {}}
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if "users" not in data:
            data["users"] = {}
        if "paid" not in data:
            data["paid"] = {}
        return data
    except Exception:
        return {"users": {}, "paid": {}}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_admin(user_id):
    return int(user_id) in ADMIN_IDS


def ensure_user(user_id):
    data = load_data()
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "trial_started": int(time.time())
        }
        save_data(data)

    return data["users"][uid]


def get_paid_until(user_id):
    data = load_data()
    return int(data["paid"].get(str(user_id), 0))


def set_paid_until(user_id, until):
    data = load_data()
    data["paid"][str(user_id)] = int(until)
    save_data(data)


def add_paid_access(user_id, seconds):
    now = int(time.time())
    current_until = get_paid_until(user_id)
    base = max(now, current_until)
    until = base + int(seconds)
    set_paid_until(user_id, until)
    return until


def trial_left(user_id):
    if is_admin(user_id):
        return 999999999

    user = ensure_user(user_id)
    started = int(user.get("trial_started", int(time.time())))
    left = TRIAL_TIME - (int(time.time()) - started)
    return max(0, left)


def has_paid_access(user_id):
    return get_paid_until(user_id) > int(time.time())


def has_site_access(user_id):
    # Для API сайта:
    # admin — всегда true
    # paid — true
    # trial сайт считает сам локально, поэтому бот не обязан выдавать access=true для trial
    if is_admin(user_id):
        return True
    return has_paid_access(user_id)


def fmt_until(until):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(until)))


def access_text(user_id):
    if is_admin(user_id):
        return "👑 У тебя админ-доступ без ограничения.\n👑 Admin unlimited access.\n👑 ადმინისტრატორის ულიმიტო წვდომა."

    paid_until = get_paid_until(user_id)
    if paid_until > int(time.time()):
        return (
            "✅ PRO-доступ активен до:\n"
            f"<code>{fmt_until(paid_until)}</code>\n\n"
            "✅ PRO access active until.\n"
            "✅ PRO წვდომა აქტიურია."
        )

    left = trial_left(user_id)
    if left > 0:
        return (
            f"🎁 Бесплатно осталось: {left // 60} мин. {left % 60} сек.\n"
            f"🎁 Free left: {left // 60} min. {left % 60} sec.\n"
            f"🎁 უფასოდ დარჩა: {left // 60} წთ. {left % 60} წმ."
        )

    return (
        "⛔ Бесплатные 5 минут закончились.\n"
        "⛔ Free 5 minutes ended.\n"
        "⛔ უფასო 5 წუთი დასრულდა."
    )


# ================== КНОПКИ ==================

def game_url_for_user(user_id):
    if is_admin(user_id):
        return f"{GAME_URL}/?admin=vaxo1971"
    return f"{GAME_URL}/?user={user_id}"


def main_menu(user_id):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🎮 Играть / Play / თამაში", url=game_url_for_user(user_id)))
    kb.add(types.InlineKeyboardButton("⏳ Мой доступ / My access / წვდომა", callback_data="access"))

    if not is_admin(user_id):
        kb.add(types.InlineKeyboardButton("💳 Купить доступ / Buy access / ყიდვა", callback_data="buy_menu"))

    return kb


def buy_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(PRICES["1h"]["text"], callback_data="buy_1h"))
    kb.add(types.InlineKeyboardButton(PRICES["24h"]["text"], callback_data="buy_24h"))
    kb.add(types.InlineKeyboardButton(PRICES["48h"]["text"], callback_data="buy_48h"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад / Back / უკან", callback_data="back"))
    return kb


def start_text(user_id):
    admin_line = ""
    if is_admin(user_id):
        admin_line = "\n👑 <b>Admin:</b> unlimited access / без ограничений / ულიმიტო\n"

    return (
        "🏛 <b>Ancient Card Games</b>\n\n"
        "🇷🇺 Добро пожаловать в мир древних карточных игр.\n"
        "🇬🇧 Welcome to the world of ancient card games.\n"
        "🇬🇪 კეთილი იყოს თქვენი მობრძანება უძველესი კარტის თამაშების სამყაროში.\n\n"
        "🎴 Poker\n"
        "⚔️ Emperor’s 21\n"
        "🃏 Joker Duel\n\n"
        "🎁 Бесплатно: 5 минут trial\n"
        "🎁 Free: 5 minutes trial\n"
        "🎁 უფასოდ: 5 წუთი trial\n\n"
        "💰 Доступ / Access / წვდომა:\n"
        "⏱ 1 час / 1 hour / 1 საათი — 50⭐\n"
        "📅 24 часа / 24 hours / 24 საათი — 150⭐\n"
        "🔥 48 часов / 48 hours / 48 საათი — 300⭐\n"
        f"{admin_line}\n"
        f"{access_text(user_id)}\n\n"
        "👇 Выберите действие / Choose action / აირჩიეთ მოქმედება:"
    )


# ================== КОМАНДЫ ==================

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    ensure_user(user_id)

    parts = message.text.split(maxsplit=1)
    start_param = parts[1] if len(parts) > 1 else ""

    if start_param.startswith("pay_") and not is_admin(user_id):
        plan_id = start_param.replace("pay_", "").split("_")[0]
        if plan_id in PRICES:
            send_invoice(user_id, plan_id)
            return

    bot.send_message(user_id, start_text(user_id), reply_markup=main_menu(user_id))


@bot.message_handler(commands=["id"])
def get_id(message):
    bot.send_message(message.chat.id, f"Твой Telegram ID:\n<code>{message.chat.id}</code>")


@bot.message_handler(commands=["status"])
def status(message):
    user_id = message.chat.id
    ensure_user(user_id)
    bot.send_message(user_id, access_text(user_id), reply_markup=main_menu(user_id))


# ================== CALLBACK-КНОПКИ ==================

@bot.callback_query_handler(func=lambda call: call.data == "access")
def access_callback(call):
    user_id = call.message.chat.id
    ensure_user(user_id)
    bot.answer_callback_query(call.id)
    bot.send_message(user_id, access_text(user_id), reply_markup=main_menu(user_id))


@bot.callback_query_handler(func=lambda call: call.data == "buy_menu")
def buy_menu_callback(call):
    user_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    if is_admin(user_id):
        bot.send_message(user_id, "👑 Администратору оплата не нужна.", reply_markup=main_menu(user_id))
        return

    bot.send_message(
        user_id,
        "💳 Выберите срок доступа:\n💳 Choose access period:\n💳 აირჩიეთ წვდომის ვადა:",
        reply_markup=buy_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data == "back")
def back_callback(call):
    user_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.send_message(user_id, start_text(user_id), reply_markup=main_menu(user_id))


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_callback(call):
    user_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    if is_admin(user_id):
        bot.send_message(user_id, "👑 Администратору оплата не нужна.", reply_markup=main_menu(user_id))
        return

    plan_id = call.data.replace("buy_", "", 1)
    if plan_id not in PRICES:
        bot.send_message(user_id, "Ошибка тарифа / Unknown plan")
        return

    send_invoice(user_id, plan_id)


# ================== TELEGRAM STARS PAYMENT ==================

def send_invoice(user_id, plan_id):
    plan = PRICES[plan_id]
    payload = f"access:{plan_id}:{user_id}"

    bot.send_invoice(
        chat_id=user_id,
        title=plan["title"],
        description=f"Ancient Card Games access: {plan['title']}",
        invoice_payload=payload,
        provider_token="",  # Для Telegram Stars должно быть пустым
        currency="XTR",
        prices=[types.LabeledPrice(label=plan["title"], amount=plan["stars"])],
        start_parameter=f"pay_{plan_id}",
    )


@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def successful_payment(message):
    user_id = message.chat.id
    payload = message.successful_payment.invoice_payload or ""

    try:
        _, plan_id, payload_user_id = payload.split(":")
    except ValueError:
        bot.send_message(user_id, "Payment received, but payload is invalid. Contact admin.")
        return

    if str(user_id) != str(payload_user_id):
        bot.send_message(user_id, "Payment user mismatch. Contact admin.")
        return

    if plan_id not in PRICES:
        bot.send_message(user_id, "Payment received, but plan is unknown. Contact admin.")
        return

    until = add_paid_access(user_id, PRICES[plan_id]["seconds"])

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🎮 Continue Game / Продолжить / გაგრძელება", url=game_url_for_user(user_id)))
    kb.add(types.InlineKeyboardButton("⏳ My access", callback_data="access"))

    bot.send_message(
        user_id,
        "✅ Оплата прошла успешно!\n"
        "✅ Payment successful!\n"
        "✅ გადახდა წარმატებით შესრულდა!\n\n"
        f"PRO active until:\n<code>{fmt_until(until)}</code>",
        reply_markup=kb
    )


# ================== API ДЛЯ САЙТА ==================

@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "Ancient Card Games Bot API",
        "message": "Bot and payment API are running"
    })


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/check_access")
def check_access_api():
    user_id = request.args.get("user", "").strip()

    if not user_id:
        return jsonify({
            "access": False,
            "admin": False,
            "until": 0,
            "trial_left": 0
        })

    try:
        uid = int(user_id)
    except ValueError:
        return jsonify({
            "access": False,
            "admin": False,
            "until": 0,
            "trial_left": 0
        })

    ensure_user(uid)

    if is_admin(uid):
        return jsonify({
            "access": True,
            "admin": True,
            "until": int(time.time()) + 10 * 365 * 24 * 60 * 60,
            "trial_left": 999999999
        })

    paid_until = get_paid_until(uid)
    left = trial_left(uid)

    return jsonify({
        "access": paid_until > int(time.time()),
        "admin": False,
        "until": paid_until,
        "trial_left": left
    })


# ================== ЗАПУСК BOT + FLASK ==================

def run_bot():
    bot.remove_webhook()
    time.sleep(1)

    while True:
        try:
            print("Bot polling started...")
            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)


if __name__ == "__main__":
    print("Starting Ancient Card Games bot + payment API...")
    threading.Thread(target=run_bot, daemon=True).start()

    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)


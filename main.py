import asyncio
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = [8079396037, 5156716017]
CHANNEL = "@higanchick"
BOT_USERNAME = "BoostSkoopiBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== БАЗА =====
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invited INTEGER DEFAULT 0,
    bought INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT
)
""")

conn.commit()

waiting_variant = {}

# ===== ГОРОДА =====
CITIES = [
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург",
    "Казань","Татарстан","Нижний Новгород","Челябинск",
    "Самара","Омск","Ростов-на-Дону","Уфа",
    "Красноярск","Воронеж","Пермь","Волгоград","Краснодар"
]

SUBJECTS = [
    "Математика","Русский","География","Информатика",
    "Физика","Химия","Обществознание",
    "Литература","Английский","Биология","История"
]

# ===== БАЗА =====
def add_user(user_id, ref=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        if ref and ref != user_id:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?", (ref,))
            conn.commit()

def get_user(user_id):
    cursor.execute("SELECT invited, bought FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row if row else (0, 0)

def add_purchase(user_id, text):
    cursor.execute("INSERT INTO purchases (user_id, text) VALUES (?, ?)", (user_id, text))
    conn.commit()

def get_purchases(user_id):
    cursor.execute("SELECT text FROM purchases WHERE user_id=?", (user_id,))
    return cursor.fetchall()

# ===== РЕФЕРАЛКА =====
def get_discount_price(user_id):
    invited, _ = get_user(user_id)
    price = 300 - invited * 20
    return max(price, 200)

def is_vip(user_id):
    invited, _ = get_user(user_id)
    return invited >= 5

# ===== ПОДПИСКА =====
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== МЕНЮ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="mypurchases")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="admin")]
    ])

def back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    add_user(message.from_user.id, ref)

    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/higanchick")],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await message.answer("❗ Подпишись на канал", reply_markup=kb)
        return

    await message.answer(
        "🚀 BoostSkoopiBot\n\n"
        "📚 ОГЭ варианты по всем городам\n"
        "⚡ Быстро и удобно\n"
        "💰 Оплата через Telegram ⭐\n\n"
        "👇 Выбери действие",
        reply_markup=main_menu()
    )

# ===== РАССЫЛКА =====
@dp.message(lambda m: m.text and m.text.startswith("/send"))
async def send_all(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    text = message.text.replace("/send ", "")

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], text)
        except:
            pass

@dp.message(lambda m: m.photo)
async def send_photo_all(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    caption = message.caption or ""

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for u in users:
        try:
            await bot.send_photo(u[0], message.photo[-1].file_id, caption=caption)
        except:
            pass

# ===== АНТИ-СЛИВ =====
@dp.message()
async def any_text(message: types.Message):
    user_id = message.from_user.id

    if message.forward_from or message.forward_from_chat:
        await message.answer("🚫 Пересылка запрещена")
        return

    if user_id in waiting_variant:
        if not message.text.isdigit():
            await message.answer("❌ Введи число 1-30")
            return

        data = waiting_variant[user_id]
        del waiting_variant[user_id]

        city, subject = data.split("|")[1:3]

        add_purchase(user_id, f"{city} | {subject} | вариант {message.text}")

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка",
            description=f"Вариант {message.text}",
            payload=data,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=100)]
        )
        return

    await message.answer("🏠 Главное меню", reply_markup=main_menu())

# ===== CALLBACK =====
@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "back":
        await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu())

    elif callback.data == "about":
        await callback.message.edit_text(
            "📘 BoostSkoopiBot\n\n"
            "🔥 Удобный бот для покупки вариантов ОГЭ\n"
            "⚡ Быстро, просто и понятно\n"
            "💰 Оплата через Telegram ⭐",
            reply_markup=back_btn()
        )

    elif callback.data == "mypurchases":
        purchases = get_purchases(user_id)

        if not purchases:
            text = "📦 У тебя нет покупок"
        else:
            text = "📦 Твои покупки:\n\n"
            for p in purchases:
                text += f"— {p[0]}\n"

        await callback.message.edit_text(text, reply_markup=back_btn())

    elif callback.data == "ref":
        invited, bought = get_user(user_id)
        price_now = get_discount_price(user_id)
        to_vip = max(5 - invited, 0)

        vip = "👑 VIP АКТИВЕН" if is_vip(user_id) else "❌ Нет VIP"

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Что даёт VIP", callback_data="vip")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ])

        text = (
            "👥 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
            f"👥 Приглашено: {invited}\n"
            f"💰 Покупок: {bought}\n\n"
            f"🔥 Цена: {price_now} ⭐\n\n"
            "📉 Система скидок:\n"
            "— каждый друг: -20 ⭐\n"
            "— максимум: -100 ⭐\n\n"
            f"{vip}\n"
            f"📊 До VIP: {to_vip}\n\n"
            f"🔗 {link}"
        )

        await callback.message.edit_text(text, reply_markup=kb)

    elif callback.data == "vip":
        await callback.message.edit_text(
            "👑 VIP СТАТУС\n\n"
            "VIP — статус активного пользователя\n\n"
            "🎯 Получается за 5 приглашённых\n\n"
            "💎 Даёт:\n"
            "— приоритет\n"
            "— статус\n"
            "— уважение\n",
            reply_markup=back_btn()
        )

    elif callback.data == "buy":
        kb = [[InlineKeyboardButton(text=c, callback_data=f"city|{c}")] for c in CITIES]
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
        await callback.message.edit_text("🌍 Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city|"):
        city = callback.data.split("|")[1]

        subs = SUBJECTS.copy()
        if city in ["Татарстан","Казань"]:
            subs.append("Татарский язык")

        kb = [[InlineKeyboardButton(text="🔥 Полный доступ — 1500 ⭐", callback_data=f"tfull|{city}|all")]]

        for s in subs:
            kb.append([InlineKeyboardButton(text=s, callback_data=f"sub|{city}|{s}")])

        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="buy")])

        await callback.message.edit_text(f"{city}\n\nВыбери предмет:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("sub|"):
        _, city, subject = callback.data.split("|")

        price30 = get_discount_price(user_id)

        kb = [
            [InlineKeyboardButton(text="📄 1 вариант — 100 ⭐", callback_data=f"t1|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30} ⭐", callback_data=f"t30|{city}|{subject}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city|{city}")]
        ]

        await callback.message.edit_text(f"{city} | {subject}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("t1|"):
        waiting_variant[user_id] = callback.data
        await callback.message.answer("✏️ Введи номер варианта (1-30)")

    elif callback.data.startswith("t30|") or callback.data.startswith("tfull|"):
        price = get_discount_price(user_id) if "t30" in callback.data else 1500

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка",
            description=f"Цена: {price} ⭐",
            payload=callback.data,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=price)]
        )

    elif callback.data == "admin":
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]

        await callback.message.edit_text(f"👑 Админка\n👥 {users}", reply_markup=back_btn())

# ===== WEB =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

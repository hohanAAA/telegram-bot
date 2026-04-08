import asyncio
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 8079396037
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
    invited INTEGER DEFAULT 0
)
""")
conn.commit()

waiting_variant = {}

# ===== ГОРОДА =====
CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург",
    "Казань", "Татарстан", "Нижний Новгород", "Челябинск",
    "Самара", "Омск", "Ростов-на-Дону", "Уфа",
    "Красноярск", "Воронеж", "Пермь", "Волгоград", "Краснодар"
]

SUBJECTS = [
    "Математика","Русский","География","Информатика",
    "Физика","Химия","Обществознание",
    "Литература","Английский","Биология","История"
]

# ===== РЕФЕРАЛКА =====
def get_user(user_id):
    cursor.execute("SELECT invited FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0], user_id
    cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    return 0, user_id

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
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="admin")]
    ])

def back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id

    if not await check_sub(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/higanchick")],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await message.answer("❗ Подпишись на канал", reply_markup=kb)
        return

    get_user(user_id)
    await message.answer("🚀 BoostSkoopiBot", reply_markup=main_menu())

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

    elif callback.data == "check_sub":
        if await check_sub(user_id):
            await callback.message.edit_text("✅ Подписка подтверждена", reply_markup=main_menu())
        else:
            await callback.answer("❌ Не подписан", show_alert=True)

    elif callback.data == "buy":
        kb = [[InlineKeyboardButton(text=c, callback_data=f"city|{c}")] for c in CITIES]
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
        await callback.message.edit_text("🌍 Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city|"):
        city = callback.data.split("|")[1]

        subs = SUBJECTS.copy()
        if city in ["Татарстан", "Казань"]:
            subs.append("Татарский язык")

        kb = [[InlineKeyboardButton(text="🔥 Полный доступ — 1500 ⭐️", callback_data=f"tfull|{city}|all")]]

        for s in subs:
            kb.append([InlineKeyboardButton(text=s, callback_data=f"sub|{city}|{s}")])

        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="buy")])

        await callback.message.edit_text(f"{city}\n\nВыбери предмет:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("sub|"):
        _, city, subject = callback.data.split("|")

        price30 = get_discount_price(user_id)

        kb = [
            [InlineKeyboardButton(text="📄 1 вариант — 100 ⭐️", callback_data=f"t1|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30} ⭐️", callback_data=f"t30|{city}|{subject}")],
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
            description=f"Цена: {price} ⭐️",
            payload=callback.data,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=price)]
        )

    elif callback.data == "ref":
        invited, _ = get_user(user_id)
        price_now = get_discount_price(user_id)
        to_vip = max(5 - invited, 0)

        vip = "👑 VIP АКТИВЕН" if is_vip(user_id) else "❌ Нет VIP"

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        text = (
            "👥 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
            "💸 Каждый друг снижает цену на 20 ⭐️\n"
            "📉 Минимум: 200 ⭐️\n\n"
            f"🔥 Текущая цена: {price_now} ⭐️\n\n"
            f"{vip}\n\n"
            "👑 VIP даёт:\n"
            "— быстрый ответ\n"
            "— приоритет\n\n"
            f"📊 До VIP: {to_vip}\n\n"
            f"🔗 {link}"
        )

        await callback.message.edit_text(text, reply_markup=back_btn())

    elif callback.data == "admin":
        if user_id != ADMIN_ID:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]

        await callback.message.edit_text(
            f"👑 Админ панель\n👥 {users} пользователей",
            reply_markup=back_btn()
        )

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success_payment(message: types.Message):
    await message.answer("✅ Оплата прошла!")

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

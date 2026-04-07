import asyncio
import os
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 123456789
BOT_USERNAME = "your_bot_username"

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

# ===== ДАННЫЕ =====
CITIES = ["Самара", "Татарстан", "Москва", "Питер"]

SUBJECTS = [
    "Математика", "Русский", "География", "Информатика",
    "Физика", "Химия", "Обществознание",
    "Литература", "Английский", "Биология", "История"
]

# ===== ФУНКЦИИ =====
def add_user(user_id, ref_id=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        if ref_id and ref_id != user_id:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?", (ref_id,))
            conn.commit()

def get_invited(user_id):
    cursor.execute("SELECT invited FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def get_prices(user_id):
    invited = get_invited(user_id)

    price1 = 250
    price30 = 700
    pricefull = 2450

    discount = min(max(invited - 1, 0) * 200, 1000)
    pricefull -= discount

    if invited >= 1:
        price30 -= 100

    extra = max(invited - 6, 0)

    if extra >= 10:
        price1 = int(price1 * 0.9)
        price30 = int(price30 * 0.9)
        pricefull = int(pricefull * 0.9)

    return price1, price30, pricefull

# ===== МЕНЮ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")]
    ])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    add_user(message.from_user.id, ref)

    await message.answer("📘 Магазин ОГЭ", reply_markup=main_menu())

# ===== CALLBACK =====
@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # ===== КУПИТЬ =====
    if callback.data == "buy":
        kb = [[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in CITIES]

        await callback.message.edit_text(
            "🌍 Выбери город:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== ГОРОД =====
    elif callback.data.startswith("city_"):
        city = callback.data.split("_")[1]

        subjects = SUBJECTS.copy()
        if city == "Татарстан":
            subjects.append("Татарский язык")

        kb = [[InlineKeyboardButton(text=s, callback_data=f"sub_{city}_{s}")] for s in subjects]

        await callback.message.edit_text(
            f"📚 Город: {city}\nВыбери предмет:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== ПРЕДМЕТ =====
    elif callback.data.startswith("sub_"):
        _, city, subject = callback.data.split("_")

        p1, p30, pf = get_prices(user_id)

        kb = [
            [InlineKeyboardButton(text=f"📄 1 вариант — {p1}₽", callback_data=f"t1_{city}_{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {p30}₽", callback_data=f"t30_{city}_{subject}")],
            [InlineKeyboardButton(text=f"🔥 Полный доступ — {pf}₽", callback_data=f"tfull_{city}_{subject}")]
        ]

        await callback.message.edit_text(
            f"📚 {city} | {subject}\nВыбери тариф:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== 1 ВАРИАНТ =====
    elif callback.data.startswith("t1_"):
        _, city, subject = callback.data.
split("_")

        kb = []
        for i in range(1, 31):
            kb.append([InlineKeyboardButton(text=f"Вариант {i}", callback_data=f"buy1_{i}")])

        await callback.message.edit_text(
            f"{city} | {subject}\nВыбери вариант:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== ПОКУПКА =====
    elif callback.data.startswith("buy1_") or callback.data.startswith("t30") or callback.data.startswith("tfull"):

        price = 1000  # 10 звёзд (пример)

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка",
            description="Доступ к вариантам",
            payload="stars",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=price)]
        )

    # ===== РЕФЕРАЛЫ =====
    elif callback.data == "ref":
        invited = get_invited(user_id)
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        await callback.message.edit_text(
            f"👥 Рефералы: {invited}\n\n"
            "💡 Система:\n"
            "— 1 человек → скидка 100₽\n"
            "— каждый следующий → -200₽\n"
            "— максимум 1000₽\n\n"
            "🎁 Бонусы:\n"
            "— 10 человек → скидка 10%\n"
            "— 20 человек → VIP\n\n"
            f"🔗 Ссылка:\n{link}",
            reply_markup=main_menu()
        )

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda message: message.successful_payment)
async def success_payment(message: types.Message):
    await message.answer("✅ Оплата прошла!\n\nДоступ выдан")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

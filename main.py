import asyncio
import os
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 1780613456
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

    p1 = 250
    p30 = 700
    pf = 2450

    pf -= min(max(invited - 1, 0) * 200, 1000)

    if invited >= 1:
        p30 -= 100

    extra = max(invited - 6, 0)

    if extra >= 10:
        p1 = int(p1 * 0.9)
        p30 = int(p30 * 0.9)
        pf = int(pf * 0.9)

    return p1, p30, pf

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
        kb = [[InlineKeyboardButton(text=city, callback_data=f"city|{city}")] for city in CITIES]

        await callback.message.edit_text(
            "🌍 Выбери город:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== ГОРОД =====
    elif callback.data.startswith("city|"):
        city = callback.data.split("|")[1]

        subjects = SUBJECTS.copy()
        if city == "Татарстан":
            subjects.append("Татарский язык")

        kb = [[InlineKeyboardButton(text=s, callback_data=f"sub|{city}|{s}")] for s in subjects]

        await callback.message.edit_text(
            f"📍 {city}\n\nВыбери предмет:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== ПРЕДМЕТ =====
    elif callback.data.startswith("sub|"):
        _, city, subject = callback.data.split("|")

        p1, p30, pf = get_prices(user_id)

        kb = [
            [InlineKeyboardButton(text=f"📄 1 вариант — {p1}₽", callback_data=f"t1|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {p30}₽", callback_data=f"t30|{city}|{subject}")],
            [InlineKeyboardButton(text=f"🔥 Полный доступ — {pf}₽", callback_data=f"tfull|{city}|{subject}")]
        ]

        await callback.message.edit_text(
            f"📚 {city} | {subject}\n\nВыбери тариф:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== 1 ВАРИАНТ =====
    elif callback.data.startswith("t1|"):
        _, city, subject = callback.data.split("|")

        kb = [
[InlineKeyboardButton(text=f"Вариант {i}", callback_data=f"buy1|{city}|{subject}|{i}")]
            for i in range(1, 31)
        ]

        await callback.message.edit_text(
            f"{city} | {subject}\n\nВыбери вариант:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    # ===== ПОКУПКА =====
    elif callback.data.startswith("buy1|") or callback.data.startswith("t30|") or callback.data.startswith("tfull|"):

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка",
            description="Доступ к вариантам",
            payload="stars",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=1000)]
        )

    # ===== РЕФЕРАЛЫ =====
    elif callback.data == "ref":
        invited = get_invited(user_id)
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        text = (
            f"👥 Приглашено: {invited}\n\n"
            "💡 Как работает:\n"
            "— 1 человек → -100₽\n"
            "— каждый следующий → -200₽\n"
            "— максимум: 1000₽\n\n"
            "🎁 Бонусы:\n"
            "— 10 человек → скидка 10%\n"
            "— 20 человек → VIP\n\n"
            f"🔗 Ссылка:\n{link}"
        )

        await callback.message.edit_text(text, reply_markup=main_menu())

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success_payment(message: types.Message):
    await message.answer("✅ Оплата прошла!\n\nДоступ выдан")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

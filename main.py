import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# === БАЗА ===
conn = sqlite3.connect("db.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    paid INTEGER DEFAULT 0
)
""")
conn.commit()


# === КНОПКИ ===
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Купить доступ")],
        [KeyboardButton(text="📁 Контент")]
    ],
    resize_keyboard=True
)


# === СТАРТ ===
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    await message.answer("Привет 👋\nВыбери действие:", reply_markup=menu)


# === КУПИТЬ ===
@dp.message(lambda msg: msg.text == "📦 Купить доступ")
async def buy(message: types.Message):
    await message.answer(
        "💳 Для покупки нажми кнопку ниже\n\n(здесь будет ЮKassa ссылка)"
    )


# === КОНТЕНТ ===
@dp.message(lambda msg: msg.text == "📁 Контент")
async def content(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("SELECT paid FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()

    if result and result[0] == 1:
        await message.answer("🔥 Вот твой контент\n(здесь твой товар)")
    else:
        await message.answer("❌ Сначала купи доступ")


# === ФЕЙК ОПЛАТА (для теста) ===
@dp.message(lambda msg: msg.text == "testpay")
async def testpay(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("UPDATE users SET paid=1 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("✅ Оплата прошла (тест)")


# === ЗАПУСК ===
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

# 🔑 ВСТАВЬ СВОЙ ID
ADMIN_ID = 1780613456

# 💳 ВСТАВЬ КАРТУ
CARD = "2202208881057849"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== ХРАНИЛИЩЕ ФАЙЛОВ =====
FILES = []

# ===== КНОПКИ =====
menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📄 1 вариант — 100₽", callback_data="buy_1")],
    [InlineKeyboardButton(text="📚 30 вариантов — 500₽", callback_data="buy_30")],
    [InlineKeyboardButton(text="🔥 Полный доступ — 2450₽", callback_data="buy_full")]
])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "📘 <b>Магазин ОГЭ</b>\n\n"
        "🎯 Готовые варианты + ответы\n"
        "⚡ Быстро перед экзаменом\n\n"
        "👇 Выбери тариф:",
        reply_markup=ReplyKeyboardRemove(),  # УБИРАЕТ СТАРЫЕ КНОПКИ
        parse_mode="HTML"
    )
    await message.answer(" ", reply_markup=menu)

# ===== СОХРАНЕНИЕ ФАЙЛОВ (ТОЛЬКО ТЫ) =====
@dp.message(lambda m: m.document)
async def save_file(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    FILES.append(message.document.file_id)
    await message.answer("✅ Файл сохранен")

# ===== ПОКУПКА =====
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy(callback: types.CallbackQuery):
    buyers = random.randint(10, 40)
    left = random.randint(2, 7)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{callback.data}")]
    ])

    if callback.data == "buy_1":
        text = f"""
📄 <b>1 вариант</b>
💰 100₽

⚡ Быстрое решение

📈 Купили: {buyers}
⏳ Осталось: {left}

💳 <code>{CARD}</code>

Нажми после оплаты 👇
"""

    elif callback.data == "buy_30":
        text = f"""
📚 <b>30 вариантов</b>
💰 500₽

🔥 Самый популярный

📈 Купили: {buyers}
⏳ Осталось: {left}

💳 <code>{CARD}</code>

Нажми после оплаты 👇
"""

    else:
        text = f"""
🔥 <b>Полный доступ</b>
💰 2450₽

👥 Скиньтесь классом — выйдет дешево

📦 Все предметы + ответы

📈 Купили: {buyers}
⏳ Осталось: {left}

💳 <code>{CARD}</code>

Нажми после оплаты 👇
"""

    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    asyncio.create_task(remind_later(callback.from_user.id))

# ===== ОПЛАТИЛ =====
@dp.callback_query(lambda c: c.data.startswith("paid_"))
async def paid(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Выдать доступ", callback_data=f"give_{user_id}")]
    ])

    await bot.send_message(
        ADMIN_ID,
        f"💰 Оплата от {user_id}",
        reply_markup=kb
    )

    await callback.message.answer("⏳ Проверяю оплату...")

# ===== ВЫДАЧА =====
@dp.callback_query(lambda c: c.data.startswith("give_"))
async def give(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    user_id = int(callback.data.split("_")[1])

    if not FILES:
        await callback.message.answer("❌ Нет файлов")
        return

    for file_id in FILES:
        await bot.send_document(
            user_id,
            file_id,
            protect_content=True
        )

    await callback.message.answer("✅ Выдано")

# ===== ДОЖИМ =====
async def remind_later(user_id):
    await asyncio.sleep(600)

    try:
        await bot.send_message(
            user_id,
            "⏳ Ты не завершил покупку\n\n"
            "⚠️ Осталось мало мест\n"
            "💸 Успей оплатить"
        )
    except:
        pass

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

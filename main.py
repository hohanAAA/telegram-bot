import asyncio
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN")

# 👇 ВСТАВЬ СВОЙ ID
ADMIN_ID = 1780613456

# 👇 ВСТАВЬ КАРТУ
CARD = "2202208881057849"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== ФАЙЛЫ (заполним потом) =====
FILES = []

# ===== МЕНЮ =====
menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📄 1 вариант — 100₽", callback_data="buy_1")],
    [InlineKeyboardButton(text="📚 30 вариантов — 500₽", callback_data="buy_30")],
    [InlineKeyboardButton(text="🔥 Полный доступ — 2450₽", callback_data="buy_full")]
])

# ===== СТАРТ =====
@dp.message(lambda m: m.text == "/start")
async def start(message: types.Message):
    await message.answer("📘 Магазин ОГЭ\n\nВыбери товар:", reply_markup=menu)

# ===== ЗАГРУЗКА ФАЙЛОВ (только ты) =====
@dp.message(lambda m: m.document)
async def save_file(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    file_id = message.document.file_id
    FILES.append(file_id)

    await message.answer("✅ Файл добавлен")

# ===== ПОКУПКА =====
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy(callback: types.CallbackQuery):
    buyers_today = random.randint(12, 37)
    left = random.randint(3, 9)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{callback.data}")]
    ])

    text = (
        f"💳 Оплата:\n{CARD}\n\n"
        f"📈 Уже купили: {buyers_today}\n"
        f"⏳ Осталось: {left}\n\n"
        "После оплаты нажми кнопку ниже 👇"
    )

    await callback.message.answer(text, reply_markup=kb)

    asyncio.create_task(remind_later(callback.from_user.id))

# ===== НАЖАЛ "ОПЛАТИЛ" =====
@dp.callback_query(lambda c: c.data.startswith("paid_"))
async def paid(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Выдать доступ", callback_data=f"give_{user_id}")]
    ])

    await bot.send_message(
        ADMIN_ID,
        f"💰 Пользователь {user_id} оплатил",
        reply_markup=kb
    )

    await callback.message.answer("⏳ Ожидай подтверждения...")

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

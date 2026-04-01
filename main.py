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

# ===== МЕНЮ =====
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
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await message.answer(" ", reply_markup=menu)

# ===== ЗАГРУЗКА ФАЙЛОВ (ТОЛЬКО ТЫ) =====
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
    left = random.randint(3, 7)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{callback.data}")]
    ])

    if callback.data == "buy_1":
        text = (
            "📄 <b>1 вариант ОГЭ</b>\n"
            "💰 Цена: 100₽\n\n"
            "⚡ Быстрое решение перед экзаменом\n\n"
            f"📈 Купили сегодня: {buyers_today}\n"
            f"⏳ Осталось: {left} мест\n\n"
            f"💳 Оплата:\n<code>{CARD}</code>\n\n"
            "После оплаты нажми кнопку 👇"
        )

    elif callback.data == "buy_30":
        text = (
            "📚 <b>30 вариантов ОГЭ</b>\n"
            "💰 Цена: 500₽\n\n"
            "🔥 Самый выгодный пакет\n\n"
            f"📈 Купили сегодня: {buyers_today}\n"
            f"⏳ Осталось: {left} мест\n\n"
            f"💳 Оплата:\n<code>{CARD}</code>\n\n"
            "После оплаты нажми кнопку 👇"
        )

    else:
        text = (
            "🔥 <b>Полный доступ ко всем вариантам</b>\n"
            "💰 Цена: 2450₽\n\n"
            "👥 Можно скинуться классом (100–200₽ с человека)\n\n"
            "📦 Внутри:\n"
            "• Все предметы\n"
            "• Все варианты\n"
            "• Ответы\n\n"
            f"📈 Купили сегодня: {buyers_today}\n"
            f"⏳ Осталось: {left} мест\n\n"
            f"💳 Оплата:\n<code>{CARD}</code>\n\n"
            "После оплаты нажми кнопку 👇"
        )

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
        f"💰 Оплата от пользователя: {user_id}",
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
        await callback.message.answer("❌ Файлы не загружены")
        return

    for file_id in FILES:
        await bot.send_document(
            user_id,
            file_id,
            protect_content=True
        )

    await callback.message.answer("✅ Доступ выдан")

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

import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1780613456  # <-- ВСТАВЬ СВОЙ ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== ТОВАРЫ =====
products = {
    "buy_1": ("1 вариант", "100₽"),
    "buy_30": ("30 вариантов", "500₽"),
    "buy_full": ("Полный ОГЭ", "2450₽")
}

# ===== FILE_ID ВАРИАНТОВ (ВСТАВИ СВОИ) =====
variants = {
    "1": "FILE_ID_1",
    "2": "FILE_ID_2",
    "3": "FILE_ID_3",
    # ...
    "30": "FILE_ID_30"
}

# ===== МЕНЮ =====
menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📄 1 вариант — 100₽", callback_data="buy_1")],
    [InlineKeyboardButton(text="📚 30 вариантов — 500₽", callback_data="buy_30")],
    [InlineKeyboardButton(text="🔥 Полный ОГЭ — 2450₽", callback_data="buy_full")]
])

# ===== СТАРТ =====
@dp.message()
async def start(message: types.Message):
    await message.answer("📘 Магазин ОГЭ\n\nВыбери товар:", reply_markup=menu)

# ===== ПОКУПКА =====
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy(callback: types.CallbackQuery):
    name, price = products[callback.data]

    await callback.message.answer(
        f"💳 Оплата\n\n"
        f"Товар: {name}\n"
        f"Сумма: {price}\n\n"
        f"Переведи на карту:\n"
        f"2202208881057849\n\n"
        f"После оплаты отправь скрин 📸"
    )

# ===== СКРИН =====
@dp.message()
async def handle_photo(message: types.Message):
    if message.photo:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"ok_{message.from_user.id}"
            )]
        ])

        await bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=f"Оплата от {message.from_user.id}",
            reply_markup=kb
        )

        await message.answer("⏳ Ожидай подтверждения")

# ===== ПОДТВЕРЖДЕНИЕ =====
@dp.callback_query(lambda c: c.data.startswith("ok_"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Выбрать вариант", callback_data="choose")]
    ])

    await bot.send_message(
        user_id,
        "🎉 Оплата подтверждена!\n\nВыбери вариант:",
        reply_markup=kb,
        protect_content=True
    )

    await callback.message.answer("✅ Выдал доступ")

# ===== ВЫБОР ВАРИАНТА =====
@dp.callback_query(lambda c: c.data == "choose")
async def choose_variant(callback: types.CallbackQuery):
    buttons = []

    row = []
    for i in range(1, 31):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"var_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer("Выбери вариант:", reply_markup=kb)

# ===== ВЫДАЧА =====
@dp.callback_query(lambda c: c.data.startswith("var_"))
async def send_variant(callback: types.CallbackQuery):
    num = callback.data.split("_")[1]

    file_id = variants.get(num)

    if not file_id:
        await callback.message.answer("❌ Нет файла")
        return

    await bot.send_document(
        callback.from_user.id,
        file_id,
        protect_content=True
    )

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

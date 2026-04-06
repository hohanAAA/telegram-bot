[06.04.2026 19:49] hohan! AAA: import asyncio
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 1780613456
CARD = "2202208881057849"
BOT_USERNAME = "BoostSkoopiBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

FILES = []
users = {}

# ===== МЕНЮ =====
def get_menu(user_id):
    invited = users.get(user_id, {}).get("invited", 0)

    price_30 = 500
    price_full = 2450

    if invited >= 1:
        price_30 = 400

    if invited >= 2:
        price_full = max(2450 - invited * 200, 500)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📄 1 вариант — 250₽", callback_data="buy_1")],
        [InlineKeyboardButton(text=f"📚 30 вариантов — {price_30}₽", callback_data="buy_30")],
        [InlineKeyboardButton(text=f"🔥 Полный доступ — {price_full}₽", callback_data="buy_full")]
    ])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    ref = args[1] if len(args) > 1 else None

    if user_id not in users:
        users[user_id] = {"ref": ref, "invited": 0}

        # начисляем реферала
        if ref and ref.isdigit():
            ref_id = int(ref)
            if ref_id in users:
                users[ref_id]["invited"] += 1

    await message.answer(
        "📘 <b>Магазин ОГЭ</b>\n\n"
        "🎯 Готовые ответы\n"
        "⚡ Быстро перед экзаменом\n\n"
        "👇 Выбери тариф:",
        reply_markup=get_menu(user_id),
        parse_mode="HTML"
    )

# ===== РЕФЕРАЛКА =====
@dp.message(lambda m: m.text.lower() == "реферал")
async def ref(message: types.Message):
    user_id = message.from_user.id
    invited = users.get(user_id, {}).get("invited", 0)

    price_30 = 400 if invited >= 1 else 500
    price_full = max(2450 - invited * 200, 500) if invited >= 2 else 2450

    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    await message.answer(
        f"👥 Приглашено: {invited}\n\n"
        f"💸 Твои цены:\n"
        f"30 вариантов — {price_30}₽\n"
        f"Полный доступ — {price_full}₽\n\n"
        f"🔗 Твоя ссылка:\n{link}"
    )

# ===== СОХРАНЕНИЕ ФАЙЛОВ =====
@dp.message(lambda m: m.document)
async def save_file(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    FILES.append(message.document.file_id)
    await message.answer("✅ Файл сохранен")

# ===== ПОКУПКА =====
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    invited = users.get(user_id, {}).get("invited", 0)

    price_30 = 400 if invited >= 1 else 500
    price_full = max(2450 - invited * 200, 500) if invited >= 2 else 2450

    buyers = random.randint(10, 40)
    left = random.randint(2, 7)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{callback.data}")]
    ])

    if callback.data == "buy_1":
        text = f"📄 1 вариант\n💰 250₽"

    elif callback.data == "buy_30":
        text = f"📚 30 вариантов\n💰 {price_30}₽"

    else:
        text = f"🔥 Полный доступ\n💰 {price_full}₽"

    text += f"\n\n📈 Купили: {buyers}\n⏳ Осталось: {left}\n\n💳 {CARD}"

    await callback.message.answer(text, reply_markup=kb)

    asyncio.create_task(remind_later(user_id))

# ===== ОПЛАТИЛ =====
@dp.callback_query(lambda c: c.data.startswith("paid_"))
async def paid(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Выдать доступ", callback_data=f"give_{user_id}")]
    ])

    await bot.send_message(ADMIN_ID, f"💰 Оплата от {user_id}", reply_markup=kb)

    await callback.message.answer("⏳ Ожидайте проверку оплаты")

# ===== ВЫДАЧА =====
@dp.callback_query(lambda c: c.data.startswith("give_"))
async def give(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
[06.04.2026 19:49] hohan! AAA: return

    user_id = int(callback.data.split("_")[1])

    for file_id in FILES:
        await bot.send_document(user_id, file_id, protect_content=True)

    await callback.message.answer("✅ Выдано")

# ===== ДОЖИМ =====
async def remind_later(user_id):
    await asyncio.sleep(600)
    try:
        await bot.send_message(user_id, "⏳ Ты не завершил покупку")
    except:
        pass

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())

import asyncio
import os
import random
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 123456789
CARD = "0000 0000 0000 0000"
BOT_USERNAME = "your_bot"
SUPPORT = "@your_username"

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

FILES = []
pending = {}

# ===== ДОБАВЛЕНИЕ =====
def add_user(user_id, ref_id=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        if ref_id and ref_id != user_id:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?", (ref_id,))
            conn.commit()

# ===== ПОЛУЧЕНИЕ ПРИГЛАШЕННЫХ =====
def get_invited(user_id):
    cursor.execute("SELECT invited FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

# ===== ЦЕНЫ =====
def get_prices(user_id):
    invited = get_invited(user_id)

    base_1 = 250
    base_30 = 700
    base_full = 2450

    discount_full = min(max(invited - 1, 0) * 200, 1000)

    price_30 = base_30 - 100 if invited >= 1 else base_30
    price_full = base_full - discount_full

    extra = max(invited - 6, 0)

    bonus = 0
    vip = False

    if extra >= 10:
        bonus = 0.10
    if extra >= 20:
        vip = True

    if bonus > 0:
        price_1 = int(base_1 * (1 - bonus))
        price_30 = int(price_30 * (1 - bonus))
        price_full = int(price_full * (1 - bonus))
    else:
        price_1 = base_1

    return price_1, price_30, price_full, invited, extra, bonus, vip

# ===== МЕНЮ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить варианты", callback_data="menu_buy")],
        [InlineKeyboardButton(text="👥 Мои приглашённые", callback_data="menu_ref")],
        [InlineKeyboardButton(text="📞 Поддержка", callback_data="menu_support")]
    ])

def buy_menu(user_id):
    p1, p30, pf, *_ = get_prices(user_id)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📄 1 вариант — {p1}₽", callback_data="buy_1")],
        [InlineKeyboardButton(text=f"📚 30 вариантов — {p30}₽", callback_data="buy_30")],
        [InlineKeyboardButton(text=f"🔥 Полный доступ — {pf}₽", callback_data="buy_full")],
        [InlineKeyboardButton(text="⭐️ Оплатить (если доступно)", callback_data="stars_full")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]
    ])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    ref_id = None

    if len(args) > 1:
        try:
            ref_id = int(args[1])
        except:
            pass

    add_user(message.from_user.id, ref_id)

    await message.answer("📘 Магазин ОГЭ\n\nВыбери действие:", reply_markup=main_menu())

# ===== СКРИН =====
@dp.message(lambda m: m.photo)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id

    if user_id in pending:
        photo = message.photo[-1].file_id

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выдать доступ", callback_data=f"give_{user_id}")]
        ])

        await bot.send_photo(
            ADMIN_ID,
            photo,
            caption=f"💰 Оплата от {user_id}",
            reply_markup=kb
        )

        await message.answer("⏳ Ожидайте проверку")
        del pending[user_id]

# ===== CALLBACK =====
@dp.callback_query()
async def callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "menu_buy":
        await callback.message.
[06.04.2026 20:55] hohan! AAA: edit_text("🛒 Выбери тариф:", reply_markup=buy_menu(user_id))

    elif callback.data == "menu_ref":
        p1, p30, pf, invited, extra, bonus, vip = get_prices(user_id)
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        text = f"👥 Приглашено: {invited}\n💸 Макс скидка: 1000₽\n\n"

        if invited >= 6:
            text += f"🎯 До -10%: {extra}/10\n👑 До VIP: {extra}/20\n\n"

        if bonus > 0:
            text += "🎁 Активна скидка 10%\n"
        if vip:
            text += "👑 VIP активен\n"

        text += f"\n🔗 {link}"

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]]
        ))

    elif callback.data == "menu_support":
        await callback.message.edit_text(
            f"📞 Поддержка: {SUPPORT}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")]]
            )
        )

    elif callback.data == "menu_back":
        await callback.message.edit_text("📘 Магазин ОГЭ\n\nВыбери действие:", reply_markup=main_menu())

    elif callback.data.startswith("buy_"):
        p1, p30, pf, *_ = get_prices(user_id)

        if callback.data == "buy_1":
            price = p1
            name = "1 вариант"
        elif callback.data == "buy_30":
            price = p30
            name = "30 вариантов"
        else:
            price = pf
            name = "полный доступ"

        pending[user_id] = True

        await callback.message.answer(
            f"💰 {name}\n\nЦена: {price}₽\n\n"
            f"💳 {CARD}\n\n"
            f"📸 Скиньте скрин оплаты"
        )

    elif callback.data.startswith("give_"):
        if callback.from_user.id != ADMIN_ID:
            return

        uid = int(callback.data.split("_")[1])

        await bot.send_message(uid, "✅ Доступ выдан")

    elif callback.data == "stars_full":
        prices = [LabeledPrice(label="Полный доступ", amount=2450 * 100)]

        try:
            await bot.send_invoice(
                chat_id=user_id,
                title="Оплата ⭐️",
                description="Полный доступ",
                payload=f"stars_{user_id}",
                provider_token="",
                currency="XTR",
                prices=prices
            )
        except:
            await callback.message.answer("❌ Звёзды недоступны")

# ===== УСПЕХ ⭐️ =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success_payment(message: types.Message):
    await message.answer("✅ Оплата прошла!")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())

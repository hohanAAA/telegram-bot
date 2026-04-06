import asyncio
import os
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 1780613456
CARD = "2202208881057849"
BOT_USERNAME = "BoostSkoopiBot"
SUPPORT = "@rebuttq"

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

pending = {}

# ===== ДОБАВЛЕНИЕ =====
def add_user(user_id, ref_id=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        if ref_id and ref_id != user_id:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?", (ref_id,))
            conn.commit()

# ===== ДАННЫЕ =====
def get_invited(user_id):
    cursor.execute("SELECT invited FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

# ===== ЦЕНЫ =====
def get_prices(user_id):
    invited = get_invited(user_id)

    base1 = 250
    base30 = 700
    basefull = 2450

    # скидка на полный доступ
    discount = min(max(invited - 1, 0) * 200, 1000)

    price1 = base1
    price30 = base30 - 100 if invited >= 1 else base30
    pricefull = basefull - discount

    extra = max(invited - 6, 0)

    # бонусы
    if extra >= 10:
        price1 = int(price1 * 0.9)
        price30 = int(price30 * 0.9)
        pricefull = int(pricefull * 0.9)

    vip = extra >= 20

    return price1, price30, pricefull, invited, extra, vip

# ===== МЕНЮ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="📞 Поддержка", callback_data="support")]
    ])

def buy_menu(user_id):
    p1, p30, pf, *_ = get_prices(user_id)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📄 1 вариант — {p1}₽", callback_data="b1")],
        [InlineKeyboardButton(text=f"📚 30 вариантов — {p30}₽", callback_data="b30")],
        [InlineKeyboardButton(text=f"🔥 Полный доступ — {pf}₽", callback_data="bfull")],
        [InlineKeyboardButton(text="⭐️ Оплата (если есть)", callback_data="stars")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
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

    await message.answer("📘 Магазин ОГЭ", reply_markup=main_menu())

# ===== СКРИН =====
@dp.message(lambda m: m.photo)
async def photo(message: types.Message):
    user_id = message.from_user.id

    if user_id in pending:
        await bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=f"💰 Оплата от {user_id}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Выдать", callback_data=f"give_{user_id}")]
                ]
            )
        )

        await message.answer("⏳ Ожидайте проверки администратора")
        del pending[user_id]

# ===== CALLBACK =====
@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "buy":
        await callback.message.edit_text("Выбери тариф:", reply_markup=buy_menu(user_id))

    elif callback.data == "ref":
        p1, p30, pf, invited, extra, vip = get_prices(user_id)

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
[06.04.2026 21:13] hohan! AAA: text = f"👥 Приглашено: {invited}\n💸 Макс скидка: 1000₽\n\n"

        if invited >= 6:
            text += f"🎯 До бонуса: {extra}/10\n👑 До VIP: {extra}/20\n"

        if extra >= 10:
            text += "\n🎁 Скидка 10% активна"
        if vip:
            text += "\n👑 VIP статус активен"

        text += f"\n\n🔗 {link}"

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]]
        ))

    elif callback.data == "support":
        await callback.message.edit_text(
            f"📞 {SUPPORT}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]]
            )
        )

    elif callback.data == "back":
        await callback.message.edit_text("📘 Магазин ОГЭ", reply_markup=main_menu())

    elif callback.data in ["b1", "b30", "bfull"]:
        p1, p30, pf, *_ = get_prices(user_id)

        if callback.data == "b1":
            price = p1
            name = "1 вариант"
        elif callback.data == "b30":
            price = p30
            name = "30 вариантов"
        else:
            price = pf
            name = "полный доступ"

        pending[user_id] = True

        await callback.message.answer(
            f"💳 {name}\n\nСумма: {price}₽\n\n{CARD}\n\n📸 Скиньте скрин оплаты"
        )

    elif callback.data.startswith("give_"):
        if callback.from_user.id != ADMIN_ID:
            return

        uid = int(callback.data.split("_")[1])

        await bot.send_message(uid, "✅ Доступ выдан")

    elif callback.data == "stars":
        prices = [LabeledPrice(label="Оплата", amount=2450 * 100)]

        try:
            await bot.send_invoice(
                chat_id=user_id,
                title="Оплата ⭐️",
                description="Доступ",
                payload="stars",
                provider_token="",
                currency="XTR",
                prices=prices
            )
        except:
            await callback.message.answer("❌ Звёзды недоступны")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())

import asyncio
import os
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import CommandStart

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 8079396037
CHANNEL = "@higanchick"
BOT_USERNAME = "BoostSkoopiBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invited INTEGER DEFAULT 0,
    bought INTEGER DEFAULT 0
)
""")
conn.commit()

waiting_variant = {}

CITIES = ["Самара", "Татарстан", "Москва", "Питер"]

SUBJECTS = [
    "Математика","Русский","География","Информатика",
    "Физика","Химия","Обществознание",
    "Литература","Английский","Биология","История"
]

# ===== ЦЕНА С РЕФЕРАЛКОЙ =====
def get_discount_price(user_id):
    invited, _ = get_user(user_id)
    price = 300 - (invited * 20)
    if price < 200:
        price = 200
    return price

# ===== ПОДПИСКА =====
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== БАЗА =====
def add_user(user_id, ref=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        if ref and ref != user_id:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?", (ref,))
            conn.commit()

def get_user(user_id):
    cursor.execute("SELECT invited, bought FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row if row else (0, 0)

# ===== МЕНЮ =====
def main_menu(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="admin")]
    ])

def back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    add_user(message.from_user.id, ref)

    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/higanchick")],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await message.answer("❗ Подпишись на канал", reply_markup=kb)
        return

    await message.answer("🚀 BoostSkoopiBot", reply_markup=main_menu(message.from_user.id))

# ===== ЛЮБОЙ ТЕКСТ =====
@dp.message()
async def any_text(message: types.Message):
    user_id = message.from_user.id

    if user_id in waiting_variant:
        if not message.text.isdigit():
            await message.answer("❌ Введи число от 1 до 30")
            return

        data = waiting_variant[user_id]
        del waiting_variant[user_id]

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка варианта",
            description=f"Вариант №{message.text}",
            payload=f"{data}|{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=100)]
        )
        return

    await message.answer("🏠 Главное меню", reply_markup=main_menu(user_id))

# ===== CALLBACK =====
@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "back":
        await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu(user_id))

    elif callback.data == "check_sub":
        if await check_sub(user_id):
            await callback.message.edit_text("✅ Подписка подтверждена", reply_markup=main_menu(user_id))
        else:
            await callback.answer("❌ Не подписан", show_alert=True)

    elif callback.data == "about":
        await callback.message.edit_text(
            "📘 BoostSkoopiBot\n\n"
            "🔥 Бот для покупки вариантов ОГЭ\n\n"
            "📚 Все предметы\n"
            "⚡ Быстро\n"
            "💸 Оплата через ⭐\n\n"
            "Выбирай и покупай",
            reply_markup=back_btn()
        )

    elif callback.data == "buy":
        kb = [[InlineKeyboardButton(text=c, callback_data=f"city|{c}")] for c in CITIES]
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
        await callback.message.edit_text("🌍 Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city|"):
        city = callback.data.split("|")[1]

        subs = SUBJECTS.copy()
        if city == "Татарстан":
            subs.append("Татарский язык")

        kb = [[InlineKeyboardButton(text="🔥 Полный доступ — 1500 ⭐", callback_data=f"tfull|{city}|all")]]

        for s in subs:
            kb.append([InlineKeyboardButton(text=s, callback_data=f"sub|{city}|{s}")])

        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="buy")])

        await callback.message.edit_text(f"{city}\n\nВыбери предмет:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("sub|"):
        _, city, subject = callback.data.split("|")

        price30 = get_discount_price(user_id)

        kb = [
            [InlineKeyboardButton(text="📄 1 вариант — 100 ⭐", callback_data=f"t1|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30} ⭐", callback_data=f"t30|{city}|{subject}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city|{city}")]
        ]

        await callback.message.edit_text(f"{city} | {subject}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("t1|"):
        waiting_variant[user_id] = callback.data
        await callback.message.answer("✏️ Введи номер варианта (1-30)")

    elif callback.data.startswith("t30|") or callback.data.startswith("tfull|"):
        if "t30" in callback.data:
            price = get_discount_price(user_id)
        else:
            price = 1500

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка",
            description=f"💰 Цена: {price} ⭐",
            payload=f"{callback.data}|{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=price)]
        )

    elif callback.data == "ref":
        invited, _ = get_user(user_id)
        price_now = get_discount_price(user_id)
        to_vip = max(5 - invited, 0)

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        text = (
            "👥 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
            "💸 Цена уменьшается за друзей\n\n"
            "📉 Было: 300 ⭐\n"
            f"💰 Сейчас: {price_now} ⭐\n\n"
            "— каждый друг: -20 ⭐\n"
            "— минимум: 200 ⭐\n\n"
            "👑 VIP с 5 друзей\n\n"
            f"📊 До VIP: {to_vip}\n\n"
            f"🔗 {link}"
        )

        await callback.message.edit_text(text, reply_markup=back_btn())

    elif callback.data == "admin":
        if user_id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]

        await callback.message.edit_text(
            f"👑 Админ панель\n👥 {users} пользователей",
            reply_markup=back_btn()
        )

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success_payment(message: types.Message):
    await message.answer("✅ Оплата прошла!")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

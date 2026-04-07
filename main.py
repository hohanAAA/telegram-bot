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

# ===== БАЗА =====
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

# ===== ДАННЫЕ =====
CITIES = ["Самара", "Татарстан", "Москва", "Питер"]

SUBJECTS = [
    "Математика","Русский","География","Информатика",
    "Физика","Химия","Обществознание",
    "Литература","Английский","Биология","История"
]

# ===== ПОДПИСКА =====
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status != "left"
    except:
        return False

# ===== ФУНКЦИИ =====
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

# ===== СКИДКИ =====
def calc_price(user_id, base_price):
    invited, _ = get_user(user_id)

    discount = 0

    if invited >= 1:
        discount += 100

    if invited > 1:
        discount += (invited - 1) * 200

    discount = min(discount, 1000)

    price = base_price - discount

    if invited >= 10:
        price = int(price * 0.9)

    return max(price, 50)

def get_price_data(data, user_id):
    if data.startswith("buy1|"):
        base = 250
    elif data.startswith("t30|"):
        base = 700
    elif data.startswith("tfull|"):
        base = 2450
    else:
        base = 100

    final = calc_price(user_id, base)
    return base, final, final * 100  # stars

# ===== МЕНЮ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="admin")]
    ])

# ===== СТАРТ =====
@dp.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    add_user(message.from_user.id, ref)

    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL[1:]}")],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await message.answer("Подпишись на канал", reply_markup=kb)
        return

    await message.answer("📘 Магазин ОГЭ", reply_markup=main_menu())

# ===== CALLBACK =====
@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "check_sub":
        if await check_sub(user_id):
            await callback.message.edit_text("✅ Подписка подтверждена", reply_markup=main_menu())
        else:
            await callback.answer("❌ Ты не подписан", show_alert=True)

    elif callback.data == "buy":
        kb = [[InlineKeyboardButton(text=c, callback_data=f"city|{c}")] for c in CITIES]
        await callback.message.edit_text("🌍 Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city|"):
        city = callback.data.split("|")[1]

        subs = SUBJECTS.copy()
        if city == "Татарстан":
            subs.append("Татарский язык")

        kb = []

        kb.append([
            InlineKeyboardButton(text="🔥 Полный доступ (всё)", callback_data=f"tfull|{city}|all")
        ])

        for s in subs:
            kb.append([
                InlineKeyboardButton(text=s, callback_data=f"sub|{city}|{s}")
            ])

        await callback.message.edit_text(
            f"{city}\n\nВыбери предмет или полный доступ:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data.startswith("sub|"):
        _, city, subject = callback.data.split("|")

        base1, final1, _ = get_price_data(f"buy1|{city}|{subject}", user_id)
        base30, final30, _ = get_price_data(f"t30|{city}|{subject}", user_id)

        kb = [
            [InlineKeyboardButton(text=f"📄 1 вариант — {final1}₽", callback_data=f"t1|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {final30}₽", callback_data=f"t30|{city}|{subject}")]
        ]

        await callback.message.edit_text(
            f"{city} | {subject}\n\n💸 Цены с учётом скидки",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

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

    elif (
        callback.data.startswith("buy1|") or
        callback.data.startswith("t30|") or
        callback.data.startswith("tfull|")
    ):
        invited, bought = get_user(user_id)

        if bought:
            await callback.message.answer("❌ Уже куплено")
            return

        base, final, stars = get_price_data(callback.data, user_id)

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка",
            description=f"Цена: {final}₽ (скидка применена)",
            payload=f"{callback.data}|{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=stars)]
        )

    elif callback.data == "ref":
        invited, _ = get_user(user_id)

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        await callback.message.edit_text(
            f"👥 Приглашено: {invited}\n\n"
            f"🔗 Ссылка:\n{link}",
            reply_markup=main_menu()
        )

    elif callback.data == "admin":
        if user_id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]

        await callback.message.edit_text(
            f"👑 Админ\n👥 Пользователей: {users}",
            reply_markup=main_menu()
        )

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success_payment(message: types.Message):
    user_id = message.from_user.id

    if str(user_id) not in message.successful_payment.invoice_payload:
        await message.answer("❌ Ошибка")
        return

    cursor.execute("UPDATE users SET bought = 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("✅ Оплата прошла!")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

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

# ===== СОСТОЯНИЕ ВВОДА =====
waiting_variant = {}

# ===== ДАННЫЕ =====
CITIES = ["Самара", "Татарстан", "Москва", "Питер"]

SUBJECTS = [
    "Математика","Русский","География","Информатика",
    "Физика","Химия","Обществознание",
    "Литература","Английский","Биология","История"
]

# ===== ЦЕНЫ =====
PRICES = {
    "buy1": 100,
    "t30": 300,
    "tfull": 1500
}

# ===== ПРОВЕРКА ПОДПИСКИ =====
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
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

# ===== МЕНЮ =====
def main_menu(user_id):
    kb = [
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

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
        await message.answer("Подпишись на канал для доступа", reply_markup=kb)
        return

    await message.answer("🚀 Добро пожаловать в BoostSkoopiBot", reply_markup=main_menu(message.from_user.id))

# ===== ВВОД ВАРИАНТА =====
@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id

    if user_id in waiting_variant:
        variant = message.text

        if not variant.isdigit():
            await message.answer("❌ Введи номер цифрой (1-30)")
            return

        data = waiting_variant[user_id]
        del waiting_variant[user_id]

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка варианта",
            description=f"Вариант №{variant}",
            payload=f"{data}|{variant}|{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=PRICES["buy1"])]
        )

# ===== CALLBACK =====
@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "check_sub":
        if await check_sub(user_id):
            await callback.message.edit_text("✅ Подписка подтверждена", reply_markup=main_menu(user_id))
        else:
            await callback.answer("❌ Не подписан", show_alert=True)

    elif callback.data == "about":
        await callback.message.edit_text(
            "📘 BoostSkoopiBot\n\n"
            "Бот для покупки вариантов ОГЭ по всем регионам.\n\n"
            "📚 Доступны предметы:\n"
            "— математика, русский, физика и др.\n\n"
            "⚡ Быстро\n"
            "💰 Удобная оплата звездами\n"
            "🔒 Безопасно\n\n"
            "Выбери «Купить» чтобы начать",
            reply_markup=main_menu(user_id)
        )

    elif callback.data == "buy":
        kb = [[InlineKeyboardButton(text=c, callback_data=f"city|{c}")] for c in CITIES]
        await callback.message.edit_text("🌍 Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city|"):
        city = callback.data.split("|")[1]

        subs = SUBJECTS.copy()
        if city == "Татарстан":
            subs.append("Татарский язык")

        kb = [[InlineKeyboardButton(text=s, callback_data=f"sub|{city}|{s}")] for s in subs]

        kb.insert(0, [InlineKeyboardButton(text="🔥 Полный доступ — 1500 ⭐", callback_data=f"tfull|{city}|all")])

        await callback.message.edit_text(
            f"{city}\n\nВыбери предмет:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data.startswith("sub|"):
        _, city, subject = callback.data.split("|")

        kb = [
            [InlineKeyboardButton(text="📄 1 вариант — 100 ⭐", callback_data=f"t1|{city}|{subject}")],
            [InlineKeyboardButton(text="📚 30 вариантов — 300 ⭐", callback_data=f"t30|{city}|{subject}")]
        ]

        await callback.message.edit_text(
            f"{city} | {subject}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data.startswith("t1|"):
        waiting_variant[user_id] = callback.data
        await callback.message.answer("✏️ Введи номер варианта (1-30)")

    elif callback.data.startswith("t30|") or callback.data.startswith("tfull|"):
        invited, bought = get_user(user_id)

        if bought:
            await callback.message.answer("❌ Уже куплено")
            return

        key = "t30" if "t30" in callback.data else "tfull"

        await bot.send_invoice(
            chat_id=user_id,
            title="Покупка",
            description="Доступ к материалам",
            payload=f"{callback.data}|{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=PRICES[key])]
        )

    elif callback.data == "ref":
        invited, _ = get_user(user_id)
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        await callback.message.edit_text(
            f"👥 Приглашено: {invited}\n\n{link}",
            reply_markup=main_menu(user_id)
        )

    elif callback.data == "admin":
        if user_id != ADMIN_ID:
            return

        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]

        await callback.message.edit_text(
            f"👑 Админ панель\n\n👥 Пользователей: {users}",
            reply_markup=main_menu(user_id)
        )

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success_payment(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("UPDATE users SET bought=1 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("✅ Оплата прошла! Скоро выдача.")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

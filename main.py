import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import Command
import asyncio

TOKEN = os.getenv("TOKEN")

ADMIN_IDS = [8079396037, 5156716817]
CHANNEL_ID = "@higanchick"
BOT_USERNAME = "BoostSkoopiBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invited INTEGER DEFAULT 0,
    ref_by INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS purchases (
    user_id INTEGER,
    item TEXT
)
""")

conn.commit()

broadcast_mode = {}
# all / vip

# ===== UTILS =====

def add_user(user_id, ref=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, ref_by) VALUES (?, ?)", (user_id, ref))
        if ref:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?", (ref,))
        conn.commit()

def get_user(user_id):
    cursor.execute("SELECT invited FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def get_discount_price(user_id):
    invited = get_user(user_id)
    discount = min(invited * 20, 100)
    return 300 - discount

def is_vip(user_id):
    return get_user(user_id) >= 5

def back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

# ===== MENU =====

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data="buy")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="📄 О боте", callback_data="about")],
        [InlineKeyboardButton(text="👑 Админ", callback_data="admin")]
    ])

# ===== START =====

@dp.message(Command("start"))
async def start(message: types.Message):
    ref = None
    if len(message.text.split()) > 1:
        ref = int(message.text.split()[1])

    add_user(message.from_user.id, ref)

    await message.answer(
        "📚 ОГЭ варианты по всем городам\n⚡ Быстро и удобно\n💰 Оплата через Telegram ⭐\n\n👇 Выбери действие",
        reply_markup=main_menu()
    )

# ===== CALLBACK =====

@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # ===== РЕФЕРАЛКА =====
    if callback.data == "ref":
        invited = get_user(user_id)
        price = get_discount_price(user_id)
        to_vip = max(5 - invited, 0)

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        text = (
            "👥 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
            "💡 За каждого друга -20 ⭐️\n"
            "🔥 Максимальная скидка: -100 ⭐️\n\n"
            f"💰 Текущая цена: {price} ⭐️\n\n"
            f"👥 Приглашено: {invited}\n"
            f"👑 До VIP: {to_vip}\n\n"
            f"🔗 {link}"
        )

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Что дает VIP", callback_data="vip_info")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ]))

    elif callback.data == "vip_info":
        text = (
            "👑 VIP СТАТУС\n\n"
            "🔥 Даётся от 5 приглашённых\n\n"
            "⚡ Преимущества:\n"
            "— Быстрая выдача\n"
            "— Приоритет\n"
            "— Статус VIP\n"
            "— Уважение 😈\n"
        )
        await callback.message.edit_text(text, reply_markup=back_btn())

    # ===== ПОКУПКИ =====
    elif callback.data == "my":
        cursor.execute("SELECT item FROM purchases WHERE user_id=?", (user_id,))
        items = cursor.fetchall()

        if not items:
            text = "❌ У тебя нет покупок"
        else:
            text = "📦 Твои покупки:\n\n"
            for i in items:
                text += f"— {i[0]}\n"

        await callback.message.edit_text(text, reply_markup=back_btn())

    # ===== О БОТЕ =====
    elif callback.data == "about":
        await callback.message.edit_text(
            "📄 О боте\n\nБыстрая покупка вариантов ОГЭ\nРаботает по всей России 🇷🇺",
            reply_markup=back_btn()
        )

    # ===== АДМИН =====
    elif callback.data == "admin":
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return

        await callback.message.edit_text(
            "👑 Админ панель",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📩 Рассылка всем", callback_data="broadcast_all")],
                [InlineKeyboardButton(text="👑 Рассылка VIP", callback_data="broadcast_vip")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ])
        )

    elif callback.data == "broadcast_all":
        broadcast_mode[user_id] = "all"
        await callback.message.edit_text("📩 Отправь сообщение")

    elif callback.data == "broadcast_vip":
        broadcast_mode[user_id] = "vip"
        await callback.message.edit_text("👑 Отправь сообщение для VIP")

    elif callback.data == "back":
        await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu())

# ===== РАССЫЛКА =====

@dp.message()
async def broadcast_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id not in broadcast_mode:
        return

    mode = broadcast_mode[user_id]
    del broadcast_mode[user_id]

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for u in users:
        try:
            if mode == "vip" and not is_vip(u[0]):
                continue

            if message.photo:
                await bot.send_photo(u[0], message.photo[-1].file_id, caption=message.caption or "")
            else:
                await bot.send_message(u[0], message.text)
        except:
            pass

    await message.answer("✅ Рассылка завершена")

# ===== RUN =====

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

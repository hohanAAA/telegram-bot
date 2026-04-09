import os
import sqlite3
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import Command

TOKEN = "8730940207:AAFOWZbt_NpaTkx4WYSEu8iQjj2UAiKaGQ0"

ADMIN_IDS = [8079396037, 5156716817]
CHANNEL_ID = "@FunPayProfitLab"
BOT_USERNAME = "BoostSkoopiBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== БД =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
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
waiting_variant = {}

# ===== WEB =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ===== ГОРОДА =====
cities = [
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань",
    "Красноярск","Нижний Новгород","Челябинск","Уфа","Ростов-на-Дону",
    "Самара","Омск","Краснодар","Воронеж","Пермь"
]

# ===== ПРЕДМЕТЫ =====
subjects = [
    "Математика","Русский","Английский","Информатика","Физика",
    "Химия","Биология","Общество","История","География",
    "Татарский язык"
]

# ===== UTILS =====
def add_user(user_id, ref=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        if ref and ref != user_id:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?", (ref,))
        cursor.execute("INSERT INTO users (user_id, ref_by) VALUES (?, ?)", (user_id, ref))
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

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member","administrator","creator"]
    except:
        return False

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
        try:
            ref = int(message.text.split()[1])
        except:
            pass

    add_user(message.from_user.id, ref)

    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/FunPayProfitLab")],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await message.answer("❗ Подпишись на канал", reply_markup=kb)
        return

    await message.answer("🏠 Главное меню", reply_markup=main_menu())

# ===== CALLBACK =====
@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "buy":
        kb = [[InlineKeyboardButton(text=c, callback_data=f"city|{c}")] for c in cities]
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
        await callback.message.edit_text("Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city|"):
        city = callback.data.split("|")[1]
        kb = [[InlineKeyboardButton(text=s, callback_data=f"sub|{city}|{s}")] for s in subjects]
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="buy")])
        await callback.message.edit_text(city, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("sub|"):
        _, city, subject = callback.data.split("|")
        price30 = get_discount_price(user_id)

        kb = [
            [InlineKeyboardButton(text="📄 1 вариант — 100 ⭐️", callback_data=f"t1|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30} ⭐️", callback_data=f"t30|{city}|{subject}")],
            [InlineKeyboardButton(text="🔥 Все предметы — 1500 ⭐️", callback_data=f"all|{city}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city|{city}")]
        ]

        await callback.message.edit_text(f"{city} | {subject}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("t1|"):
        waiting_variant[user_id] = callback.data
        await callback.message.answer("✏️ Введи номер варианта (1-30)")

    elif callback.data.startswith("t30|"):
        price = get_discount_price(user_id)

        await bot.send_invoice(
            chat_id=user_id,
            title="30 вариантов",
            description=f"{price} ⭐️",
            payload=f"{callback.data}|{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=price)]
        )

    elif callback.data.startswith("all|"):
        city = callback.data.split("|")[1]

        await bot.send_invoice(
            chat_id=user_id,
            title="Все предметы",
            description=f"{city} | все предметы",
            payload=f"all|{city}|{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оплата", amount=1500)]
        )

    elif callback.data == "ref":
        invited = get_user(user_id)
        price = get_discount_price(user_id)
        to_vip = max(5 - invited, 0)

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        kb = [
            [InlineKeyboardButton(text="👑 Что дает VIP", callback_data="vip")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ]

        await callback.message.edit_text(
            f"👥 Приглашено: {invited}\n💰 Цена: {price}⭐\n👑 До VIP: {to_vip}\n\n{link}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data == "vip":
        await callback.message.edit_text(
            "👑 VIP\n\nДаётся от 5 друзей\n\n⚡ Быстрая выдача\n⚡ Приоритет",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="ref")]
            ])
        )

    elif callback.data == "about":
        await callback.message.edit_text(
            "📄 О боте\n\n🔥 ОГЭ без стресса\n\nВсе предметы и города\n\n⚡ Быстро и удобно",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ])
        )

    elif callback.data == "admin":
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ Нет доступа", show_alert=True)
            return

        kb = [
            [InlineKeyboardButton(text="📩 Всем", callback_data="b_all")],
            [InlineKeyboardButton(text="👑 VIP", callback_data="b_vip")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ]

        await callback.message.edit_text("Админка", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data == "b_all":
        broadcast_mode[user_id] = "all"
        await callback.message.answer("Отправь сообщение")

    elif callback.data == "b_vip":
        broadcast_mode[user_id] = "vip"
        await callback.message.answer("Отправь сообщение VIP")

    elif callback.data == "back":
        await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu())

# ===== RUN =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

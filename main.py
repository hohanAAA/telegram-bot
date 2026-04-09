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

# ===== WEB (фикс Render) =====
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

# ===== ДАННЫЕ =====
cities = [
    "Москва","СПБ","Казань","Новосибирск","Екатеринбург",
    "Нижний Новгород","Челябинск","Самара","Омск","Ростов",
    "Уфа","Красноярск","Пермь","Воронеж","Волгоград",
    "Краснодар","Саратов","Тюмень","Тольятти"
]

subjects = [
    "Математика","Русский","Английский",
    "Информатика","Физика","Химия",
    "Биология","Общество","История","География"
]

# ===== UTILS =====
def add_user(user_id, ref=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        if ref == user_id:
            ref = None

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
            ref = None

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
    print("MY ID:", user_id)

    if callback.data == "check_sub":
        if await check_sub(user_id):
            await callback.message.edit_text("✅ Подписка подтверждена", reply_markup=main_menu())
        else:
            await callback.answer("❌ Не подписан", show_alert=True)

    elif callback.data == "buy":
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
            title="Покупка",
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

        text = (
            "👥 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
            "💡 За каждого друга -20 ⭐️\n"
            "🔥 Максимальная скидка: -100 ⭐️\n\n"
            f"💰 Сейчас: {price} ⭐️\n\n"
            f"👥 Приглашено: {invited}\n"
            f"👑 До VIP: {to_vip}\n\n"
            f"{link}"
        )

        kb = [
            [InlineKeyboardButton(text="👑 Что дает VIP", callback_data="vip")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data == "vip":
        await callback.message.edit_text(
            "👑 VIP\n\nДаётся от 5 друзей\n\n⚡ Быстрая выдача\n⚡ Приоритет",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="ref")]
            ])
        )

    elif callback.data == "my":
        cursor.execute("SELECT item FROM purchases WHERE user_id=?", (user_id,))
        data = cursor.fetchall()

        text = "📦 Покупки:\n\n" if data else "❌ Нет покупок"
        for i in data:
            text += f"— {i[0]}\n"

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ])
        )

    elif callback.data == "about":
        await callback.message.edit_text(
            """📄 О боте

🔥 ОГЭ без стресса

Здесь ты получаешь готовые варианты по всем городам  
— быстро  
— удобно  
— без лишней воды  

📚 Все основные предметы:
математика, русский, английский и другие

⚡ Мгновенный доступ после покупки  
💸 Скидки до -100⭐ через рефералов  
👑 VIP статус = приоритет + быстрее выдача  

🎯 Подходит если:
— нужно подготовиться быстро  
— хочешь уверенно сдать  
— не хочешь тратить время на поиски  

Удачи на экзамене 🍀""",
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
        await callback.message.edit_text("Отправь сообщение")

    elif callback.data == "b_vip":
        broadcast_mode[user_id] = "vip"
        await callback.message.edit_text("Отправь сообщение VIP")

    elif callback.data == "back":
        await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu())

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda m: m.successful_payment)
async def success_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    data = payload.split("|")

    try:
    user_id = int(data[-1])

    # 🔥 ВСЕ ПРЕДМЕТЫ
    if data[0] == "all":
        city = data[1]
        item = f"{city} | ВСЕ ПРЕДМЕТЫ"

    # 📚 30 ВАРИАНТОВ
    else:
        city = data[1]
        subject = data[2]
        item = f"{city} | {subject} | 30 вариантов"

    cursor.execute("INSERT INTO purchases (user_id, item) VALUES (?, ?)", (user_id, item))
    conn.commit()

except:
    pass
    await message.answer("✅ Оплата прошла и сохранена!")

# ===== РАССЫЛКА =====
@dp.message()
async def msg(message: types.Message):
    user_id = message.from_user.id

    # ===== ОБРАБОТКА ВАРИАНТА =====
    if user_id in waiting_variant:
        try:
            num = int(message.text)
            if num < 1 or num > 30:
                await message.answer("❗ Введи число от 1 до 30")
                return

            data = waiting_variant[user_id]
            del waiting_variant[user_id]

            _, city, subject = data.split("|")

            item = f"{city} | {subject} | вариант {num}"

            cursor.execute("INSERT INTO purchases (user_id, item) VALUES (?, ?)", (user_id, item))
            conn.commit()

            await message.answer(f"✅ Куплен вариант {num}\n\n📩 Отправка...")

        except:
            await message.answer("❗ Введи число")
        return

    # ===== РАССЫЛКА =====
  @dp.message()
async def msg(message: types.Message):
    user_id = message.from_user.id

    # ===== ОБРАБОТКА ВАРИАНТА =====
    if user_id in waiting_variant:
        try:
            num = int(message.text)
            if num < 1 or num > 30:
                await message.answer("❗ Введи число от 1 до 30")
                return

            data = waiting_variant[user_id]
            del waiting_variant[user_id]

            _, city, subject = data.split("|")

            item = f"{city} | {subject} | вариант {num}"

            cursor.execute("INSERT INTO purchases (user_id, item) VALUES (?, ?)", (user_id, item))
            conn.commit()

            await message.answer(f"✅ Куплен вариант {num}")

        except:
            await message.answer("❗ Введи число")
        return

    # ===== РАССЫЛКА =====
@dp.message()
async def msg(message: types.Message):
    user_id = message.from_user.id

    # ===== ОБРАБОТКА ВАРИАНТА =====
    if user_id in waiting_variant:
        try:
            num = int(message.text)
            if num < 1 or num > 30:
                await message.answer("❗ Введи число от 1 до 30")
                return

            data = waiting_variant[user_id]
            del waiting_variant[user_id]

            _, city, subject = data.split("|")

            item = f"{city} | {subject} | вариант {num}"

            cursor.execute("INSERT INTO purchases (user_id, item) VALUES (?, ?)", (user_id, item))
            conn.commit()

            await message.answer(f"✅ Куплен вариант {num}")

        except:
            await message.answer("❗ Введи число")
        return

    # ===== РАССЫЛКА =====
  @dp.message()
async def msg(message: types.Message):
    user_id = message.from_user.id

    # ===== ОБРАБОТКА ВАРИАНТА =====
    if user_id in waiting_variant:
        try:
            num = int(message.text)
            if num < 1 or num > 30:
                await message.answer("❗ Введи число от 1 до 30")
                return

            data = waiting_variant[user_id]
            del waiting_variant[user_id]

            _, city, subject = data.split("|")

            item = f"{city} | {subject} | вариант {num}"

            cursor.execute("INSERT INTO purchases (user_id, item) VALUES (?, ?)", (user_id, item))
            conn.commit()

            await message.answer(f"✅ Куплен вариант {num}")

        except:
            await message.answer("❗ Введи число")
        return

    # ===== РАССЫЛКА =====
@dp.message()
async def msg(message: types.Message):
    user_id = message.from_user.id
if user_id in waiting_variant:
        try:
            num = int(message.text)
            if num < 1 or num > 30:
                await message.answer("❗ Введи число от 1 до 30")
                return

            data = waiting_variant[user_id]
            del waiting_variant[user_id]

            _, city, subject = data.split("|")

            item = f"{city} | {subject} | вариант {num}"

            cursor.execute("INSERT INTO purchases (user_id, item) VALUES (?, ?)", (user_id, item))
            conn.commit()

            await message.answer(f"✅ Куплен вариант {num}")
            return
        except:
            await message.answer("❗ Введи число")
        return
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

    await message.answer("✅ Готово")

# ===== RUN =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

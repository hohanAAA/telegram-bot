import os
import sqlite3
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import Command

TOKEN = "8730940207:AAFOWZbt_NpaTkx4WYSEu8iQjj2UAiKaGQ0"

ADMIN_IDS = [8079396037, 1780613456]
CHANNEL_ID = "@FunPayProfitLab"
BOT_USERNAME = "BoostSkoopiBot"
ADMIN_USERNAME = "rebuttq"

bot = Bot(token=TOKEN)
dp = Dispatcher()

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

cities = [
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань",
    "Красноярск","Нижний Новгород","Челябинск","Уфа","Ростов-на-Дону",
    "Самара","Омск","Краснодар","Воронеж","Пермь","Татарстан"
]

# ОГЭ предметы
oge_subjects_base = [
    "Математика","Русский","Английский","Информатика","Физика",
    "Химия","Биология","Общество","История","География"
]

# ЕГЭ предметы
ege_subjects_base = [
    "Математика (профиль)","Математика (база)","Русский","Английский",
    "Физика","Химия","Биология","Общество","История",
    "Информатика","География","Литература"
]

tatar_cities = ["Казань", "Татарстан"]

# Цены ОГЭ
OGE_PRICE_1 = 100
OGE_PRICE_30 = 300
OGE_PRICE_ALL = 1500

# Цены ЕГЭ (+20%)
EGE_PRICE_1 = 120
EGE_PRICE_30 = 360
EGE_PRICE_ALL = 1800

def get_oge_subjects(city):
    if city in tatar_cities:
        return oge_subjects_base + ["Татарский язык"]
    return oge_subjects_base

def get_ege_subjects(city):
    if city in tatar_cities:
        return ege_subjects_base + ["Татарский язык"]
    return ege_subjects_base

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

def get_discount_price(user_id, base_price):
    invited = get_user(user_id)
    discount_percent = min(invited * 20, 100)
    discount = int(base_price * discount_percent / 100)
    return base_price - discount

def is_vip(user_id):
    return get_user(user_id) >= 5

def stars_to_rub(stars):
    return int(stars * 1.6)

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member","administrator","creator"]
    except:
        return False

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 ОГЭ", callback_data="oge"), InlineKeyboardButton(text="📗 ЕГЭ", callback_data="ege")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my"), InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")],
        [InlineKeyboardButton(text="🛡️Admin", callback_data="admin")],
        [InlineKeyboardButton(text="📄 О боте", callback_data="about")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    ref = None
    if len(message.text.split()) > 1:
        try:
            ref = int(message.text.split()[1])
        except:
            pass

    add_user(user_id, ref)

    if not await check_sub(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/FunPayProfitLab")],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await message.answer("❗ Подпишись на канал", reply_markup=kb)
        return

    welcome_text = """🏠 Главное меню

🔥 АКЦИЯ: -50% на всё!
⏰ Только до 20 апреля!

Выбери нужный раздел:"""

    await message.answer(welcome_text, reply_markup=main_menu())

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    help_text = """🆘 Помощь

🎯 Как купить варианты:
1. Нажми «📘 ОГЭ» или «📗 ЕГЭ»
2. Выбери город
3. Выбери предмет
4. Выбери тариф и оплати

👥 Рефералка:
Приглашай друзей — получай скидку!

❓ Остались вопросы?
Жми «🛡️Admin» → «Написать админу»"""

    await message.answer(help_text, reply_markup=main_menu())

@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in waiting_variant:
        text = message.text.strip()
        
        if not text.isdigit():
            await message.answer("❌ Введи число от 1 до 30")
            return
        
        variant_num = int(text)
        if variant_num < 1 or variant_num > 30:
            await message.answer("❌ Номер варианта должен быть от 1 до 30")
            return
        
        data = waiting_variant.pop(user_id)
        parts = data.split("|")
        exam_type = parts[0]  # t1_oge или t1_ege
        city = parts[1]
        subject = parts[2]

        if "ege" in exam_type:
            stars = EGE_PRICE_1
            exam_label = "ЕГЭ"
        else:
            stars = OGE_PRICE_1
            exam_label = "ОГЭ"

        rub = stars_to_rub(stars)

        pay_text = f"""🎯 {exam_label} | {city} | {subject} | Вариант №{variant_num}

💰 Стоимость: {stars}⭐ = {rub}₽

Выбери способ оплаты:"""

        transfer_msg = quote(f"Хочу оплатить переводом:\n📍 Город: {city}\n📚 Предмет: {subject}\n📄 Тариф: {exam_label} | 1 вариант (№{variant_num})\n💰 Сумма: {stars}⭐ = {rub}₽")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплата звёздами ({stars}⭐)", callback_data=f"pay_stars|{exam_type}|{city}|{subject}|{variant_num}")],
            [InlineKeyboardButton(text=f"💳 Оплата переводом ({rub}₽)", url=f"https://t.me/{ADMIN_USERNAME}?text={transfer_msg}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sub_{exam_type.split('_')[1]}|{city}|{subject}")]
        ])

        await message.answer(pay_text, reply_markup=kb)
        return

    if user_id in broadcast_mode:
        mode = broadcast_mode.pop(user_id)
        
        if mode == "all":
            cursor.execute("SELECT user_id FROM users")
        else:
            cursor.execute("SELECT user_id FROM users WHERE invited >= 5")
        
        users = cursor.fetchall()
        sent = 0
        
        for (uid,) in users:
            try:
                await bot.copy_message(uid, user_id, message.message_id)
                sent += 1
            except:
                pass
        
        await message.answer(f"✅ Отправлено: {sent}")
        return

@dp.callback_query()
async def cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if callback.data == "check_sub":
        if await check_sub(user_id):
            welcome_text = """🏠 Главное меню

🔥 АКЦИЯ: -50% на всё!
⏰ Только до 20 апреля!

Выбери нужный раздел:"""
            await callback.message.edit_text(welcome_text, reply_markup=main_menu())
        else:
            await callback.answer("❌ Ты не подписан!", show_alert=True)

    # ===== ОГЭ =====
    elif callback.data == "oge":
        kb = []
        row = []
        for c in cities:
            row.append(InlineKeyboardButton(text=c, callback_data=f"city_oge|{c}"))
            if len(row) == 3:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
        await callback.message.edit_text("📘 ОГЭ — Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city_oge|"):
        city = callback.data.split("|")[1]
        subjects = get_oge_subjects(city)

        kb = []
        row = []
        for s in subjects:
            row.append(InlineKeyboardButton(text=s, callback_data=f"sub_oge|{city}|{s}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        kb.append([InlineKeyboardButton(text="🔥 Все предметы — 1500 ⭐️", callback_data=f"all_oge|{city}")])
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="oge")])
        await callback.message.edit_text(f"📘 ОГЭ | {city} — выбери предмет:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("sub_oge|"):
        _, city, subject = callback.data.split("|")
        price30 = get_discount_price(user_id, OGE_PRICE_30)

        kb = [
            [InlineKeyboardButton(text=f"📄 1 вариант — {OGE_PRICE_1} ⭐️", callback_data=f"t1_oge|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30} ⭐️", callback_data=f"t30_oge|{city}|{subject}")],
            [InlineKeyboardButton(text=f"🔥 Все предметы — {OGE_PRICE_ALL} ⭐️", callback_data=f"all_oge|{city}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city_oge|{city}")]
        ]

        tariff_text = f"""📘 ОГЭ | {city} | {subject}

📄 1 вариант — {OGE_PRICE_1}⭐ (было 200⭐)
📚 30 вариантов — {price30}⭐ (было 600⭐)
🔥 Все предметы — {OGE_PRICE_ALL}⭐ (было 3000⭐)

Выбери тариф:"""

        await callback.message.edit_text(tariff_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("t1_oge|"):
        waiting_variant[user_id] = callback.data
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"sub_oge|{callback.data.split('|')[1]}|{callback.data.split('|')[2]}")]
        ])
        await callback.message.edit_text("✏️ Введи номер варианта (1-30):", reply_markup=kb)

    elif callback.data.startswith("t30_oge|"):
        _, city, subject = callback.data.split("|")
        price = get_discount_price(user_id, OGE_PRICE_30)
        rub = stars_to_rub(price)

        pay_text = f"""📘 ОГЭ | {city} | {subject} | 30 вариантов

💰 Стоимость: {price}⭐ = {rub}₽

Выбери способ оплаты:"""

        transfer_msg = quote(f"Хочу оплатить переводом:\n📍 Город: {city}\n📚 Предмет: {subject}\n📄 Тариф: ОГЭ | 30 вариантов\n💰 Сумма: {price}⭐ = {rub}₽")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплата звёздами ({price}⭐)", callback_data=f"pay_stars|t30_oge|{city}|{subject}")],
            [InlineKeyboardButton(text=f"💳 Оплата переводом ({rub}₽)", url=f"https://t.me/{ADMIN_USERNAME}?text={transfer_msg}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sub_oge|{city}|{subject}")]
        ])

        await callback.message.edit_text(pay_text, reply_markup=kb)

    elif callback.data.startswith("all_oge|"):
        city = callback.data.split("|")[1]
        rub = stars_to_rub(OGE_PRICE_ALL)

        pay_text = f"""📘 ОГЭ | {city} | Все предметы

💰 Стоимость: {OGE_PRICE_ALL}⭐ = {rub}₽

Выбери способ оплаты:"""

        transfer_msg = quote(f"Хочу оплатить переводом:\n📍 Город: {city}\n📄 Тариф: ОГЭ | Все предметы\n💰 Сумма: {OGE_PRICE_ALL}⭐ = {rub}₽")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплата звёздами ({OGE_PRICE_ALL}⭐)", callback_data=f"pay_stars|all_oge|{city}")],
            [InlineKeyboardButton(text=f"💳 Оплата переводом ({rub}₽)", url=f"https://t.me/{ADMIN_USERNAME}?text={transfer_msg}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city_oge|{city}")]
        ])

        await callback.message.edit_text(pay_text, reply_markup=kb)

    # ===== ЕГЭ =====
    elif callback.data == "ege":
        kb = []
        row = []
        for c in cities:
            row.append(InlineKeyboardButton(text=c, callback_data=f"city_ege|{c}"))
            if len(row) == 3:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
        await callback.message.edit_text("📗 ЕГЭ — Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("city_ege|"):
        city = callback.data.split("|")[1]
        subjects = get_ege_subjects(city)

        kb = []
        row = []
        for s in subjects:
            row.append(InlineKeyboardButton(text=s, callback_data=f"sub_ege|{city}|{s}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        kb.append([InlineKeyboardButton(text=f"🔥 Все предметы — {EGE_PRICE_ALL} ⭐️", callback_data=f"all_ege|{city}")])
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="ege")])
        await callback.message.edit_text(f"📗 ЕГЭ | {city} — выбери предмет:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("sub_ege|"):
        _, city, subject = callback.data.split("|")
        price30 = get_discount_price(user_id, EGE_PRICE_30)

        kb = [
            [InlineKeyboardButton(text=f"📄 1 вариант — {EGE_PRICE_1} ⭐️", callback_data=f"t1_ege|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30} ⭐️", callback_data=f"t30_ege|{city}|{subject}")],
            [InlineKeyboardButton(text=f"🔥 Все предметы — {EGE_PRICE_ALL} ⭐️", callback_data=f"all_ege|{city}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city_ege|{city}")]
        ]

        tariff_text = f"""📗 ЕГЭ | {city} | {subject}

📄 1 вариант — {EGE_PRICE_1}⭐ (было 240⭐)
📚 30 вариантов — {price30}⭐ (было 720⭐)
🔥 Все предметы — {EGE_PRICE_ALL}⭐ (было 3600⭐)

Выбери тариф:"""

        await callback.message.edit_text(tariff_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("t1_ege|"):
        waiting_variant[user_id] = callback.data
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"sub_ege|{callback.data.split('|')[1]}|{callback.data.split('|')[2]}")]
        ])
        await callback.message.edit_text("✏️ Введи номер варианта (1-30):", reply_markup=kb)

    elif callback.data.startswith("t30_ege|"):
        _, city, subject = callback.data.split("|")
        price = get_discount_price(user_id, EGE_PRICE_30)
        rub = stars_to_rub(price)

        pay_text = f"""📗 ЕГЭ | {city} | {subject} | 30 вариантов

💰 Стоимость: {price}⭐ = {rub}₽

Выбери способ оплаты:"""

        transfer_msg = quote(f"Хочу оплатить переводом:\n📍 Город: {city}\n📚 Предмет: {subject}\n📄 Тариф: ЕГЭ | 30 вариантов\n💰 Сумма: {price}⭐ = {rub}₽")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплата звёздами ({price}⭐)", callback_data=f"pay_stars|t30_ege|{city}|{subject}")],
            [InlineKeyboardButton(text=f"💳 Оплата переводом ({rub}₽)", url=f"https://t.me/{ADMIN_USERNAME}?text={transfer_msg}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sub_ege|{city}|{subject}")]
        ])

        await callback.message.edit_text(pay_text, reply_markup=kb)

    elif callback.data.startswith("all_ege|"):
        city = callback.data.split("|")[1]
        rub = stars_to_rub(EGE_PRICE_ALL)

        pay_text = f"""📗 ЕГЭ | {city} | Все предметы

💰 Стоимость: {EGE_PRICE_ALL}⭐ = {rub}₽

Выбери способ оплаты:"""

        transfer_msg = quote(f"Хочу оплатить переводом:\n📍 Город: {city}\n📄 Тариф: ЕГЭ | Все предметы\n💰 Сумма: {EGE_PRICE_ALL}⭐ = {rub}₽")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплата звёздами ({EGE_PRICE_ALL}⭐)", callback_data=f"pay_stars|all_ege|{city}")],
            [InlineKeyboardButton(text=f"💳 Оплата переводом ({rub}₽)", url=f"https://t.me/{ADMIN_USERNAME}?text={transfer_msg}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city_ege|{city}")]
        ])

        await callback.message.edit_text(pay_text, reply_markup=kb)

    # ===== ОПЛАТА ЗВЁЗДАМИ =====
    elif callback.data.startswith("pay_stars|"):
        parts = callback.data.split("|")
        tariff_type = parts[1]

        if tariff_type == "t1_oge":
            city, subject, variant_num = parts[2], parts[3], parts[4]
            await bot.send_invoice(
                chat_id=user_id,
                title=f"ОГЭ | Вариант №{variant_num}",
                description=f"{city} | {subject} | Вариант {variant_num}",
                payload=f"t1_oge|{city}|{subject}|{variant_num}|{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="1 вариант ОГЭ", amount=OGE_PRICE_1)]
            )

        elif tariff_type == "t30_oge":
            city, subject = parts[2], parts[3]
            price = get_discount_price(user_id, OGE_PRICE_30)
            await bot.send_invoice(
                chat_id=user_id,
                title="ОГЭ | 30 вариантов",
                description=f"{city} | {subject} | Все 30 вариантов",
                payload=f"t30_oge|{city}|{subject}|{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="30 вариантов ОГЭ", amount=price)]
            )

        elif tariff_type == "all_oge":
            city = parts[2]
            await bot.send_invoice(
                chat_id=user_id,
                title="ОГЭ | Все предметы",
                description=f"{city} | Все предметы ОГЭ",
                payload=f"all_oge|{city}|{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Все предметы ОГЭ", amount=OGE_PRICE_ALL)]
            )

        elif tariff_type == "t1_ege":
            city, subject, variant_num = parts[2], parts[3], parts[4]
            await bot.send_invoice(
                chat_id=user_id,
                title=f"ЕГЭ | Вариант №{variant_num}",
                description=f"{city} | {subject} | Вариант {variant_num}",
                payload=f"t1_ege|{city}|{subject}|{variant_num}|{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="1 вариант ЕГЭ", amount=EGE_PRICE_1)]
            )

        elif tariff_type == "t30_ege":
            city, subject = parts[2], parts[3]
            price = get_discount_price(user_id, EGE_PRICE_30)
            await bot.send_invoice(
                chat_id=user_id,
                title="ЕГЭ | 30 вариантов",
                description=f"{city} | {subject} | Все 30 вариантов",
                payload=f"t30_ege|{city}|{subject}|{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="30 вариантов ЕГЭ", amount=price)]
            )

        elif tariff_type == "all_ege":
            city = parts[2]
            await bot.send_invoice(
                chat_id=user_id,
                title="ЕГЭ | Все предметы",
                description=f"{city} | Все предметы ЕГЭ",
                payload=f"all_ege|{city}|{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Все предметы ЕГЭ", amount=EGE_PRICE_ALL)]
            )

    elif callback.data == "my":
        cursor.execute("SELECT item FROM purchases WHERE user_id=?", (user_id,))
        rows = cursor.fetchall()

        if rows:
            items = "\n".join([f"• {row[0]}" for row in rows])
            text = f"📦 Твои покупки:\n\n{items}"
        else:
            text = "📦 У тебя пока нет покупок"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ])
        await callback.message.edit_text(text, reply_markup=kb)

    elif callback.data == "ref":
        invited = get_user(user_id)
        price_oge = get_discount_price(user_id, OGE_PRICE_30)
        price_ege = get_discount_price(user_id, EGE_PRICE_30)
        to_vip = max(5 - invited, 0)
        current_discount = min(invited * 20, 100)

        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

        kb = [
            [InlineKeyboardButton(text="👑 Что даёт VIP", callback_data="vip")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ]

        text = f"""👥 Реферальная система

📊 Приглашено друзей: {invited}
📘 Цена ОГЭ 30 вариантов: {price_oge}⭐
📗 Цена ЕГЭ 30 вариантов: {price_ege}⭐
🎁 Твоя скидка: {current_discount}%
👑 До VIP статуса: {to_vip} друзей

📌 Максимальная скидка: 100⭐
📌 Минимальная цена ОГЭ: 200⭐
📌 Минимальная цена ЕГЭ: 260⭐

🔗 Твоя ссылка:
{link}

💡 За каждого друга -20% к цене!"""

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data == "vip":
        await callback.message.edit_text(
            "👑 VIP статус\n\n✅ Даётся за 5 приглашённых друзей\n\n⚡ Быстрая выдача товара\n⚡ Приоритетная поддержка\n⚡ Максимальная скидка",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="ref")]
            ])
        )

    elif callback.data == "about":
        await callback.message.edit_text(
            "📄 О боте\n\n🔥 ОГЭ и ЕГЭ без стресса!\n\n📘 Все предметы ОГЭ\n📗 Все предметы ЕГЭ\n🏙 Все города России\n📝 Варианты 1-30\n\n⚡ Быстро и удобно\n💎 Оплата звёздами или переводом",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ])
        )

    elif callback.data == "admin":
        if user_id in ADMIN_IDS:
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE invited >= 5")
            vip_count = cursor.fetchone()[0]

            kb = [
                [InlineKeyboardButton(text="📩 Рассылка всем", callback_data="b_all"), InlineKeyboardButton(text="👑 Рассылка VIP", callback_data="b_vip")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ]

            await callback.message.edit_text(
                f"👑 Админ-панель\n\n👥 Всего юзеров: {total}\n👑 VIP юзеров: {vip_count}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
            )
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📩 Написать админу", url="https://t.me/rebuttq")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ])
            await callback.message.edit_text(
                "🛡️Admin\n\nЕсли есть вопросы — напиши нам!",
                reply_markup=kb
            )

    elif callback.data == "b_all":
        if user_id not in ADMIN_IDS:
            return
        broadcast_mode[user_id] = "all"
        await callback.message.answer("📩 Отправь сообщение для рассылки ВСЕМ:")

    elif callback.data == "b_vip":
        if user_id not in ADMIN_IDS:
            return
        broadcast_mode[user_id] = "vip"
        await callback.message.answer("👑 Отправь сообщение для рассылки VIP:")

    elif callback.data == "back":
        waiting_variant.pop(user_id, None)
        broadcast_mode.pop(user_id, None)
        welcome_text = """🏠 Главное меню

🔥 АКЦИЯ: -50% на всё!
⏰ Только до 20 апреля!

Выбери нужный раздел:"""
        await callback.message.edit_text(welcome_text, reply_markup=main_menu())

    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(lambda m: m.successful_payment)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload

    cursor.execute("INSERT INTO purchases (user_id, item) VALUES (?, ?)", (user_id, payload))
    conn.commit()

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 Новая оплата!\n\n👤 ID: {user_id}\n📦 Товар: {payload}\n💵 Сумма: {message.successful_payment.total_amount}⭐"
            )
        except:
            pass

    await message.answer("✅ Оплата прошла успешно!\n\n📦 Товар скоро будет отправлен.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

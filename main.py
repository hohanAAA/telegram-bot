import os
import sqlite3
import asyncio
import threading
import random
import string
from datetime import datetime
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
MATERIAL_LINK = "https://ibb.co/zTzXHSS2"

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
    item TEXT,
    amount INTEGER DEFAULT 0,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER,
    item TEXT,
    used INTEGER DEFAULT 0,
    created_at TEXT
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

    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ===== ГОРОДА С ЧАСОВЫМИ ПОЯСАМИ =====
cities = [
    ("Москва", "UTC+3"),
    ("Санкт-Петербург", "UTC+3"),
    ("Новосибирск", "UTC+7"),
    ("Екатеринбург", "UTC+5"),
    ("Красноярск", "UTC+7"),
    ("Нижний Новгород", "UTC+3"),
    ("Челябинск", "UTC+5"),
    ("Уфа", "UTC+5"),
    ("Ростов-на-Дону", "UTC+3"),
    ("Самара", "UTC+4"),
    ("Омск", "UTC+6"),
    ("Краснодар", "UTC+3"),
    ("Воронеж", "UTC+3"),
    ("Пермь", "UTC+5"),
    ("Татарстан", "UTC+3"),
]

# ===== ПРЕДМЕТЫ ОГЭ =====
oge_subjects_base = [
    "Математика", "Русский", "Английский", "Информатика", "Физика",
    "Химия", "Биология", "Общество", "История", "География"
]

# ===== ПРЕДМЕТЫ ЕГЭ =====
ege_subjects_base = [
    "Математика (профиль)", "Математика (база)", "Русский", "Английский",
    "Физика", "Химия", "Биология", "Общество", "История",
    "Информатика", "География", "Литература"
]

tatar_cities = ["Татарстан"]

# ===== ЦЕНЫ ОГЭ (со скидкой -50%) =====
OGE_PRICE_1 = 100
OGE_PRICE_30 = 300
OGE_PRICE_ALL = 1500

# ===== ЦЕНЫ ЕГЭ (со скидкой -50%) =====
EGE_PRICE_1 = 120
EGE_PRICE_30 = 360
EGE_PRICE_ALL = 1800

# ===== СТАРЫЕ ЦЕНЫ =====
OGE_OLD_1 = 200
OGE_OLD_30 = 600
OGE_OLD_ALL = 3000
EGE_OLD_1 = 240
EGE_OLD_30 = 720
EGE_OLD_ALL = 3600

def get_city_names():
    return [c[0] for c in cities]

def get_city_tz(city_name):
    for c in cities:
        if c[0] == city_name:
            return c[1]
    return ""

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
    result = base_price - discount
    if base_price == OGE_PRICE_30:
        return max(result, 200)
    if base_price == EGE_PRICE_30:
        return max(result, 260)
    return result

def stars_to_rub(stars):
    return int(stars * 1.6)

def is_vip(user_id):
    return get_user(user_id) >= 5

def generate_token():
    chars = string.ascii_uppercase + string.digits
    return "OGE-" + "".join(random.choices(chars, k=8))

def create_token(user_id, item):
    token = generate_token()
    # Проверяем уникальность
    while cursor.execute("SELECT * FROM tokens WHERE token=?", (token,)).fetchone():
        token = generate_token()
    cursor.execute(
        "INSERT INTO tokens (token, user_id, item, used, created_at) VALUES (?, ?, ?, 0, ?)",
        (token, user_id, item, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    return token

def use_token(token):
    row = cursor.execute("SELECT * FROM tokens WHERE token=? AND used=0", (token,)).fetchone()
    if row:
        cursor.execute("UPDATE tokens SET used=1 WHERE token=?", (token,))
        conn.commit()
        return True
    return False

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📘 ОГЭ", callback_data="oge"),
            InlineKeyboardButton(text="📗 ЕГЭ", callback_data="ege")
        ],
        [
            InlineKeyboardButton(text="📦 Мои покупки", callback_data="my"),
            InlineKeyboardButton(text="👥 Рефералы", callback_data="ref")
        ],
        [InlineKeyboardButton(text="🛡️Admin", callback_data="admin")],
        [InlineKeyboardButton(text="📄 О боте", callback_data="about")]
    ])

def build_city_kb(exam_type):
    kb = []
    row = []
    for city_name, tz in cities:
        btn_text = f"{city_name} ({tz})"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"city_{exam_type}|{city_name}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return kb

# ===== КОМАНДА START =====
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

# ===== КОМАНДА HELP =====
@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    help_text = """🆘 Помощь

🎯 Как купить варианты:
1. Нажми «📘 ОГЭ» или «📗 ЕГЭ»
2. Выбери город
3. Выбери предмет
4. Выбери тариф и оплати
5. Получи токен и активируй за 48 часов до экзамена

👥 Рефералка:
Приглашай друзей — получай скидку!

❓ Остались вопросы?
Жми «🛡️Admin» → «Написать админу»"""

    await message.answer(help_text, reply_markup=main_menu())

# ===== ОБРАБОТЧИК ТЕКСТА =====
@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id

    # ===== ПРОВЕРКА ТОКЕНА =====
    text = message.text.strip() if message.text else ""

    if text.startswith("OGE-") and len(text) == 12:
        if use_token(text):
            await message.answer(
                f"✅ Токен активирован!\n\n"
                f"📦 Вот твой материал:\n"
                f"🔗 {MATERIAL_LINK}\n\n"
                f"⚠️ Токен использован. Повторно использовать нельзя."
            )
        else:
            await message.answer(
                "❌ Токен недействителен или уже использован!\n\n"
                "Проверь токен и попробуй снова."
            )
        return

    # ===== ВВОД НОМЕРА ВАРИАНТА =====
    if user_id in waiting_variant:
        if not text.isdigit():
            await message.answer("❌ Введи число от 1 до 30")
            return

        variant_num = int(text)
        if variant_num < 1 or variant_num > 30:
            await message.answer("❌ Номер варианта должен быть от 1 до 30")
            return

        data = waiting_variant.pop(user_id)
        parts = data.split("|")
        exam_type = parts[0]
        city = parts[1]
        subject = parts[2]

        if "ege" in exam_type:
            stars = EGE_PRICE_1
            old_stars = EGE_OLD_1
            exam_label = "ЕГЭ"
        else:
            stars = OGE_PRICE_1
            old_stars = OGE_OLD_1
            exam_label = "ОГЭ"

        rub = stars_to_rub(stars)

        pay_text = f"""🎯 {exam_label} | {city} | {subject} | Вариант №{variant_num}

💰 Стоимость: {stars}⭐ = {rub}₽
📉 Было: {old_stars}⭐

Выбери способ оплаты:"""

        transfer_msg = quote(
            f"Хочу оплатить переводом:\n"
            f"📍 Город: {city}\n"
            f"📚 Предмет: {subject}\n"
            f"📄 Тариф: {exam_label} | 1 вариант (№{variant_num})\n"
            f"💰 Сумма: {stars}⭐ = {rub}₽"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплата звёздами ({stars}⭐)", callback_data=f"pay_stars|{exam_type}|{city}|{subject}|{variant_num}")],
            [InlineKeyboardButton(text=f"💳 Оплата переводом ({rub}₽)", url=f"https://t.me/{ADMIN_USERNAME}?text={transfer_msg}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sub_{exam_type.split('_')[1]}|{city}|{subject}")]
        ])

        await message.answer(pay_text, reply_markup=kb)
        return

    # ===== РАССЫЛКА =====
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

# ===== CALLBACK =====
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
        kb = build_city_kb("oge")
        await callback.message.edit_text(
            "📘 ОГЭ — Выбери город:\n\n💡 Не нашёл свой город? Выбери тот, в котором тот же часовой пояс!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data.startswith("city_oge|"):
        city = callback.data.split("|")[1]
        subjects = get_oge_subjects(city)
        tz = get_city_tz(city)

        kb = []
        row = []
        for s in subjects:
            row.append(InlineKeyboardButton(text=s, callback_data=f"sub_oge|{city}|{s}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        kb.append([InlineKeyboardButton(text=f"🔥 Все предметы — {OGE_PRICE_ALL}⭐️", callback_data=f"all_oge|{city}")])
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="oge")])
        await callback.message.edit_text(
            f"📘 ОГЭ | {city} ({tz}) — выбери предмет:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data.startswith("sub_oge|"):
        _, city, subject = callback.data.split("|")
        price30 = get_discount_price(user_id, OGE_PRICE_30)

        kb = [
            [InlineKeyboardButton(text=f"📄 1 вариант — {OGE_PRICE_1}⭐️", callback_data=f"t1_oge|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30}⭐️", callback_data=f"t30_oge|{city}|{subject}")],
            [InlineKeyboardButton(text=f"🔥 Все предметы — {OGE_PRICE_ALL}⭐️", callback_data=f"all_oge|{city}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city_oge|{city}")]
        ]

        tariff_text = f"""📘 ОГЭ | {city} | {subject}

📄 1 вариант — {OGE_PRICE_1}⭐ (было {OGE_OLD_1}⭐)
📚 30 вариантов — {price30}⭐ (было {OGE_OLD_30}⭐)
🔥 Все предметы — {OGE_PRICE_ALL}⭐ (было {OGE_OLD_ALL}⭐)

⏰ Акция -50% до 20 апреля!

Выбери тариф:"""

        await callback.message.edit_text(tariff_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("t1_oge|"):
        waiting_variant[user_id] = callback.data
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"sub_oge|{callback.data.split('|')[1]}|{callback.data.split('|')[2]}"
            )]
        ])
        await callback.message.edit_text("✏️ Введи номер варианта (1-30):", reply_markup=kb)

    elif callback.data.startswith("t30_oge|"):
        _, city, subject = callback.data.split("|")
        price = get_discount_price(user_id, OGE_PRICE_30)
        rub = stars_to_rub(price)

        pay_text = f"""📘 ОГЭ | {city} | {subject} | 30 вариантов

💰 Стоимость: {price}⭐ = {rub}₽
📉 Было: {OGE_OLD_30}⭐

Выбери способ оплаты:"""

        transfer_msg = quote(
            f"Хочу оплатить переводом:\n"
            f"📍 Город: {city}\n"
            f"📚 Предмет: {subject}\n"
            f"📄 Тариф: ОГЭ | 30 вариантов\n"
            f"💰 Сумма: {price}⭐ = {rub}₽"
        )

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
📉 Было: {OGE_OLD_ALL}⭐

Выбери способ оплаты:"""

        transfer_msg = quote(
            f"Хочу оплатить переводом:\n"
            f"📍 Город: {city}\n"
            f"📄 Тариф: ОГЭ | Все предметы\n"
            f"💰 Сумма: {OGE_PRICE_ALL}⭐ = {rub}₽"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплата звёздами ({OGE_PRICE_ALL}⭐)", callback_data=f"pay_stars|all_oge|{city}")],
            [InlineKeyboardButton(text=f"💳 Оплата переводом ({rub}₽)", url=f"https://t.me/{ADMIN_USERNAME}?text={transfer_msg}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city_oge|{city}")]
        ])

        await callback.message.edit_text(pay_text, reply_markup=kb)

    # ===== ЕГЭ =====
    elif callback.data == "ege":
        kb = build_city_kb("ege")
        await callback.message.edit_text(
            "📗 ЕГЭ — Выбери город:\n\n💡 Не нашёл свой город? Выбери тот, в котором тот же часовой пояс!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data.startswith("city_ege|"):
        city = callback.data.split("|")[1]
        subjects = get_ege_subjects(city)
        tz = get_city_tz(city)

        kb = []
        row = []
        for s in subjects:
            row.append(InlineKeyboardButton(text=s, callback_data=f"sub_ege|{city}|{s}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        kb.append([InlineKeyboardButton(text=f"🔥 Все предметы — {EGE_PRICE_ALL}⭐️", callback_data=f"all_ege|{city}")])
        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="ege")])
        await callback.message.edit_text(
            f"📗 ЕГЭ | {city} ({tz}) — выбери предмет:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    elif callback.data.startswith("sub_ege|"):
        _, city, subject = callback.data.split("|")
        price30 = get_discount_price(user_id, EGE_PRICE_30)

        kb = [
            [InlineKeyboardButton(text=f"📄 1 вариант — {EGE_PRICE_1}⭐️", callback_data=f"t1_ege|{city}|{subject}")],
            [InlineKeyboardButton(text=f"📚 30 вариантов — {price30}⭐️", callback_data=f"t30_ege|{city}|{subject}")],
            [InlineKeyboardButton(text=f"🔥 Все предметы — {EGE_PRICE_ALL}⭐️", callback_data=f"all_ege|{city}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"city_ege|{city}")]
        ]

        tariff_text = f"""📗 ЕГЭ | {city} | {subject}

📄 1 вариант — {EGE_PRICE_1}⭐ (было {EGE_OLD_1}⭐)
📚 30 вариантов — {price30}⭐ (было {EGE_OLD_30}⭐)
🔥 Все предметы — {EGE_PRICE_ALL}⭐ (было {EGE_OLD_ALL}⭐)

⏰ Акция -50% до 20 апреля!

Выбери тариф:"""

        await callback.message.edit_text(tariff_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    elif callback.data.startswith("t1_ege|"):
        waiting_variant[user_id] = callback.data
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"sub_ege|{callback.data.split('|')[1]}|{callback.data.split('|')[2]}"
            )]
        ])
        await callback.message.edit_text("✏️ Введи номер варианта (1-30):", reply_markup=kb)

    elif callback.data.startswith("t30_ege|"):
        _, city, subject = callback.data.split("|")
        price = get_discount_price(user_id, EGE_PRICE_30)
        rub = stars_to_rub(price)

        pay_text = f"""📗 ЕГЭ | {city} | {subject} | 30 вариантов

💰 Стоимость: {price}⭐ = {rub}₽
📉 Было: {EGE_OLD_30}⭐

Выбери способ оплаты:"""

        transfer_msg = quote(
            f"Хочу оплатить переводом:\n"
            f"📍 Город: {city}\n"
            f"📚 Предмет: {subject}\n"
            f"📄 Тариф: ЕГЭ | 30 вариантов\n"
            f"💰 Сумма: {price}⭐ = {rub}₽"
        )

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
📉 Было: {EGE_OLD_ALL}⭐

Выбери способ оплаты:"""

        transfer_msg = quote(
            f"Хочу оплатить переводом:\n"
            f"📍 Город: {city}\n"
            f"📄 Тариф: ЕГЭ | Все предметы\n"
            f"💰 Сумма: {EGE_PRICE_ALL}⭐ = {rub}₽"
        )

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

    # ===== МОИ ПОКУПКИ =====
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

    # ===== РЕФЕРАЛЫ =====
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

📌 Максимальная скидка: 20%
📌 Минимальная цена ОГЭ: 200⭐
📌 Минимальная цена ЕГЭ: 260⭐

🔗 Твоя ссылка:
{link}

💡 За каждого друга +20% скидки!"""

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    # ===== VIP =====
    elif callback.data == "vip":
        await callback.message.edit_text(
            "👑 VIP статус\n\n✅ Даётся за 5 приглашённых друзей\n\n⚡ Быстрая выдача товара\n⚡ Приоритетная поддержка\n⚡ Максимальная скидка",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="ref")]
            ])
        )

    # ===== О БОТЕ =====
    elif callback.data == "about":
        await callback.message.edit_text(
            "📄 О боте\n\n🔥 ОГЭ и ЕГЭ без стресса!\n\n📘 Все предметы ОГЭ\n📗 Все предметы ЕГЭ\n🏙 Все города России\n📝 Варианты 1-30\n\n⚡ Быстро и удобно\n💎 Оплата звёздами или переводом",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ])
        )

    # ===== АДМИН =====
    elif callback.data == "admin":
        if user_id in ADMIN_IDS:
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE invited >= 5")
            vip_count = cursor.fetchone()[0]

            # Статистика оплат звёздами
            cursor.execute("SELECT COUNT(*), SUM(amount) FROM purchases WHERE amount > 0")
            row = cursor.fetchone()
            total_orders = row[0] or 0
            total_stars = row[1] or 0
            total_rub = stars_to_rub(total_stars)

            kb = [
                [
                    InlineKeyboardButton(text="📩 Рассылка всем", callback_data="b_all"),
                    InlineKeyboardButton(text="👑 Рассылка VIP", callback_data="b_vip")
                ],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
            ]

            await callback.message.edit_text(
                f"👑 Админ-панель\n\n"
                f"👥 Всего юзеров: {total}\n"
                f"👑 VIP юзеров: {vip_count}\n\n"
                f"💰 Статистика оплат (звёзды):\n"
                f"📦 Всего заказов: {total_orders}\n"
                f"⭐ Всего звёзд: {total_stars}⭐\n"
                f"💵 В рублях: ~{total_rub}₽",
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

    # ===== НАЗАД =====
    elif callback.data == "back":
        waiting_variant.pop(user_id, None)
        broadcast_mode.pop(user_id, None)
        welcome_text = """🏠 Главное меню

🔥 АКЦИЯ: -50% на всё!
⏰ Только до 20 апреля!

Выбери нужный раздел:"""
        await callback.message.edit_text(welcome_text, reply_markup=main_menu())

    await callback.answer()

# ===== ОПЛАТА =====
@dp.pre_checkout_query()
async def pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(lambda m: m.successful_payment)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    amount = message.successful_payment.total_amount

    # Сохраняем покупку с суммой и датой
    cursor.execute(
        "INSERT INTO purchases (user_id, item, amount, date) VALUES (?, ?, ?, ?)",
        (user_id, payload, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

    # Генерируем токен
    token = create_token(user_id, payload)

    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💰 Новая оплата!\n\n"
                f"👤 ID: {user_id}\n"
                f"📦 Товар: {payload}\n"
                f"💵 Сумма: {amount}⭐ = {stars_to_rub(amount)}₽"
            )
        except:
            pass

    # Отправляем токен пользователю
    await message.answer(
        f"✅ Оплата прошла успешно!\n\n"
        f"🔑 Твой токен:\n"
        f"`{token}`\n\n"
        f"⚠️ Отправь этот токен боту за 48 часов до начала экзамена чтобы получить материал\n\n"
        f"Просто скопируй и вставь токен в этот чат!",
        parse_mode="Markdown"
    )

# ===== ЗАПУСК =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

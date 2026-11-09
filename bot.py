import asyncio
import json
import sqlite3
import random
from datetime import date

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery

# ==========================================
# НАСТРОЙКИ (ОБЯЗАТЕЛЬНО ПОМЕНЯЙ ЭТО)
# ==========================================
BOT_TOKEN = "9134817516:AAGBfC_v5NkBRO69vkwL6GVpGZix10rRPLU"
WEB_APP_URL = "https://regal-tarsier-c0531e.netlify.app" # Позже заменишь на ссылку твоей игры

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# БАЗА ДАННЫХ (Хранит вращения и номерки)
# ==========================================
db = sqlite3.connect("game.db")
db.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    spins INTEGER DEFAULT 5,
    last_free TEXT,
    numbers TEXT DEFAULT '[]'
)""")
db.commit()

FREE_PER_DAY = 5          # Бесплатных вращений в день
SPIN_PACK = 10            # Сколько вращений в пакете
SPIN_PACK_PRICE = 15      # Цена пакета в Stars

def get_user(uid):
    cur = db.execute("SELECT spins, last_free, numbers FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    if not row:
        db.execute("INSERT INTO users (user_id, last_free) VALUES (?, ?)", (uid, str(date.today())))
        db.commit()
        return FREE_PER_DAY, str(date.today()), "[]"
    return row

def save_user(uid, spins, numbers):
    db.execute("UPDATE users SET spins=?, numbers=? WHERE user_id=?", (spins, numbers, uid))
    db.commit()

# ==========================================
# ОБРАБОТЧИКИ КОМАНД
# ==========================================
@dp.message(CommandStart())
async def start(msg: types.Message):
    spins, last_free, numbers = get_user(msg.from_user.id)
    
    # Ежедневный бонус
    if last_free < str(date.today()):
        spins += FREE_PER_DAY
        db.execute("UPDATE users SET last_free=? WHERE user_id=?", (str(date.today()), msg.from_user.id))
        save_user(msg.from_user.id, spins, numbers)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Играть", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="⭐ Купить 10 вращений", callback_data="buy_spins")]
    ])
    await msg.answer(f"Привет! У тебя {spins} вращений. Крути номерки!", reply_markup=kb)

# Покупка вращений
@dp.callback_query(F.data == "buy_spins")
async def buy_spins(cb: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"{SPIN_PACK} вращений",
        description="Пакет дополнительных вращений для игры Номерок",
        payload=f"spins_{SPIN_PACK}",
        currency="XTR", # XTR - это Telegram Stars
        prices=[LabeledPrice(label="Пакет вращений", amount=SPIN_PACK_PRICE)],
    )
    await cb.answer()

# Подтверждение перед оплатой (обязательно для Stars)
@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

# Успешная оплата
@dp.message(F.successful_payment)
async def paid(msg: types.Message):
    spins, _, numbers = get_user(msg.from_user.id)
    spins += SPIN_PACK
    save_user(msg.from_user.id, spins, numbers)
    await msg.answer(f"✅ Оплата прошла! Начислено +{SPIN_PACK} вращений. Теперь у тебя {spins}.")

# Получение данных из Mini App (когда нажимают "Крутить")
@dp.message(F.web_app_data)
async def webapp(msg: types.Message):
    data = json.loads(msg.web_app_data.data)
    if data.get("action") == "spin":
        spins, _, numbers = get_user(msg.from_user.id)
        
        if spins <= 0:
            await msg.answer("🚫 Вращения закончились! Купи пакет за ⭐ (кнопка ниже).", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Купить 10 вращений", callback_data="buy_spins")]
            ]))
            return
            
        num = random.randint(1, 100)
        spins -= 1
        nums = json.loads(numbers)
        nums.append(num)
        save_user(msg.from_user.id, spins, json.dumps(nums))
        
        await msg.answer(f"🎲 Выпал номерок: **{num}**\nОсталось вращений: {spins}", parse_mode="Markdown")

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    print("Бот запущен! Не закрывай Termux.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
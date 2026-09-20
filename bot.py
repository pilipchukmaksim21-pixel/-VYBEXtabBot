import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Replace these demo products with your real catalogue later.
PRODUCTS = [
    {"id": "p1", "name": "VYBEX Product 1", "price": 40, "description": "30 ml • demo product"},
    {"id": "p2", "name": "VYBEX Product 2", "price": 40, "description": "30 ml • demo product"},
]
carts = {}

def age_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Мне 18+", callback_data="age_yes")],
        [InlineKeyboardButton(text="❌ Мне нет 18", callback_data="age_no")],
    ])

def menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders")],
        [InlineKeyboardButton(text="🎁 Акции", callback_data="promo")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
    ])

def catalog_keyboard():
    rows = [[InlineKeyboardButton(text=f"{p['name']} — {p['price']} zł", callback_data=f"product:{p['id']}")] for p in PRODUCTS]
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в VYBEX.\n\nДля доступа к каталогу подтвердите, что вам исполнилось 18 лет.",
        reply_markup=age_keyboard()
    )

@dp.callback_query(F.data == "age_yes")
async def age_yes(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("Добро пожаловать в VYBEX 👋\n\nВыберите раздел:", reply_markup=menu_keyboard())

@dp.callback_query(F.data == "age_no")
async def age_no(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("Доступ закрыт. Для использования сервиса необходимо быть 18+.")

@dp.callback_query(F.data == "menu")
async def menu(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("Главное меню VYBEX:", reply_markup=menu_keyboard())

@dp.callback_query(F.data == "catalog")
async def catalog(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("🛍 Каталог VYBEX\n\nВыберите товар:", reply_markup=catalog_keyboard())

@dp.callback_query(F.data.startswith("product:"))
async def product(c: CallbackQuery):
    await c.answer()
    pid = c.data.split(":", 1)[1]
    p = next((x for x in PRODUCTS if x["id"] == pid), None)
    if not p:
        return await c.message.answer("Товар не найден.")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Добавить в корзину", callback_data=f"add:{pid}")],
        [InlineKeyboardButton(text="⬅️ Каталог", callback_data="catalog")],
    ])
    await c.message.edit_text(f"🧴 {p['name']}\n\n{p['description']}\n\nЦена: {p['price']} zł", reply_markup=kb)

@dp.callback_query(F.data.startswith("add:"))
async def add(c: CallbackQuery):
    await c.answer("Добавлено в корзину ✅")
    pid = c.data.split(":", 1)[1]
    carts.setdefault(c.from_user.id, []).append(pid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
    ])
    await c.message.edit_text("Товар добавлен в корзину ✅", reply_markup=kb)

@dp.callback_query(F.data == "cart")
async def cart(c: CallbackQuery):
    await c.answer()
    ids = carts.get(c.from_user.id, [])
    if not ids:
        text = "🛒 Корзина пуста."
    else:
        lines, total = [], 0
        for pid in ids:
            p = next((x for x in PRODUCTS if x["id"] == pid), None)
            if p:
                lines.append(f"• {p['name']} — {p['price']} zł")
                total += p["price"]
        text = "🛒 Ваша корзина:\n\n" + "\n".join(lines) + f"\n\nИтого: {total} zł"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu")],
    ])
    await c.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data == "orders")
async def orders(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("📦 История заказов пока пуста.", reply_markup=menu_keyboard())

@dp.callback_query(F.data == "promo")
async def promo(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("🎁 Акции\n\nЗдесь будут отображаться актуальные предложения.", reply_markup=menu_keyboard())

@dp.callback_query(F.data == "support")
async def support(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("💬 Поддержка\n\nЗдесь будет контакт поддержки.", reply_markup=menu_keyboard())

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Add it in Railway Variables.")
    await dp.start_polling(Bot(BOT_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())

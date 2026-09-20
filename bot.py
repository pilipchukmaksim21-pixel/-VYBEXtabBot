import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json

TOKEN = os.environ.get("BOT_TOKEN")
with open("catalog_categories.json", encoding="utf-8") as f:
    CATEGORIES = json.load(f)

LANG = {}
T = {
 "ru":{"title":"VYBEX","age":"🔞 Только для лиц 18+","info":"Информационный каталог. Заказы и дистанционная продажа отключены.","catalog":"🛍 Каталог","manager":"💬 Связаться с менеджером"},
 "uk":{"title":"VYBEX","age":"🔞 Тільки для осіб 18+","info":"Інформаційний каталог. Замовлення та дистанційний продаж вимкнені.","catalog":"🛍 Каталог","manager":"💬 Зв'язатися з менеджером"},
 "pl":{"title":"VYBEX","age":"🔞 Tylko dla osób 18+","info":"Katalog informacyjny. Zamówienia i sprzedaż na odległość są wyłączone.","catalog":"🛍 Katalog","manager":"💬 Kontakt z menedżerem"},
 "en":{"title":"VYBEX","age":"🔞 18+ only","info":"Informational catalog. Ordering and distance sales are disabled.","catalog":"🛍 Catalog","manager":"💬 Contact manager"}}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    LANG.setdefault(uid,"ru")
    k=LANG[uid]
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("🇷🇺 Русский",callback_data="l_ru"),
                              InlineKeyboardButton("🇺🇦 Українська",callback_data="l_uk")],
                             [InlineKeyboardButton("🇵🇱 Polski",callback_data="l_pl"),
                              InlineKeyboardButton("🇬🇧 English",callback_data="l_en")],
                             [InlineKeyboardButton("🔞 18+ — подтвердить",callback_data="age")]])
    await update.message.reply_text(f"{T[k]['title']}\n\n{T[k]['age']}\n{T[k]['info']}",reply_markup=kb)

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id
    if q.data.startswith("l_"):
        LANG[uid]=q.data[2:]
        await q.edit_message_text(T[LANG[uid]]["title"],reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(T[LANG[uid]]["catalog"],callback_data="cat")],
            [InlineKeyboardButton(T[LANG[uid]]["manager"],callback_data="manager")]]))
    elif q.data=="age":
        k=LANG.get(uid,"ru")
        await q.edit_message_text(f"{T[k]['title']}\n\n{T[k]['age']}\n{T[k]['info']}",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(T[k]["catalog"],callback_data="cat")],
                                                                       [InlineKeyboardButton(T[k]["manager"],callback_data="manager")]]))
    elif q.data=="cat":
        k=LANG.get(uid,"ru")
        kb=[[InlineKeyboardButton(c,callback_data=f"c:{i}")] for i,c in enumerate(CATEGORIES)]
        await q.edit_message_text(T[k]["catalog"],reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("c:"):
        k=LANG.get(uid,"ru"); c=CATEGORIES[int(q.data[2:])]
        await q.edit_message_text(f"{c}\n\n{T[k]['info']}",reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(T[k]["catalog"],callback_data="cat")]]))
    elif q.data=="manager":
        await q.edit_message_text("💬 Менеджер / Manager\n\nДобавьте сюда ваш официальный контакт после его создания.")

app=Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start",start))
app.add_handler(CallbackQueryHandler(cb))
app.run_polling()

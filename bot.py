import os, json, logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "fvmfm1").lstrip("@").lower()
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "manager_VYBEX").lstrip("@").lower()
DATA = Path("catalog.json")
USERS = Path("users.json")
logging.basicConfig(level=logging.INFO)

LANGS = {
 "ru":{"cat":"🛍 Каталог","manager":"💬 Связаться с менеджером","lang":"🌐 Язык","back":"◀️ Назад","age":"🔞 Только 18+","info":"Информационный каталог. Для товара свяжитесь с менеджером.","name":"Введите имя:","phone":"Введите номер телефона:","district":"Выберите район встречи:","interest":"Какой товар вас интересует?","sent":"✅ Заявка отправлена менеджеру.","admin":"⚙️ Админ-панель"},
 "uk":{"cat":"🛍 Каталог","manager":"💬 Зв'язатися з менеджером","lang":"🌐 Мова","back":"◀️ Назад","age":"🔞 Лише 18+","info":"Інформаційний каталог. Для товару зв'яжіться з менеджером.","name":"Введіть ім'я:","phone":"Введіть номер телефону:","district":"Оберіть район зустрічі:","interest":"Який товар вас цікавить?","sent":"✅ Заявку надіслано менеджеру.","admin":"⚙️ Адмін-панель"},
 "pl":{"cat":"🛍 Katalog","manager":"💬 Kontakt z menedżerem","lang":"🌐 Język","back":"◀️ Wstecz","age":"🔞 Tylko 18+","info":"Katalog informacyjny. Skontaktuj się z menedżerem.","name":"Podaj imię:","phone":"Podaj numer telefonu:","district":"Wybierz dzielnicę spotkania:","interest":"Jaki produkt Cię interesuje?","sent":"✅ Zgłoszenie wysłane do menedżera.","admin":"⚙️ Panel administratora"},
 "en":{"cat":"🛍 Catalog","manager":"💬 Contact manager","lang":"🌐 Language","back":"◀️ Back","age":"🔞 18+ only","info":"Informational catalog. Contact the manager for the product.","name":"Enter your name:","phone":"Enter your phone number:","district":"Choose meeting district:","interest":"Which product interests you?","sent":"✅ Request sent to manager.","admin":"⚙️ Admin panel"}
}
langs={}
forms={}
admin_state={}

def data():
    if not DATA.exists(): DATA.write_text('{"categories":[],"products":[]}',encoding="utf-8")
    return json.loads(DATA.read_text(encoding="utf-8"))
def save(d): DATA.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
def load_users():
    if not USERS.exists(): USERS.write_text("{}",encoding="utf-8")
    try: return json.loads(USERS.read_text(encoding="utf-8"))
    except Exception: return {}
def save_users(d): USERS.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
def register_user(user):
    users=load_users(); uid=str(user.id); username=(user.username or "").lstrip("@").lower()
    role=users.get(uid,{}).get("role")
    if username==ADMIN_USERNAME: role="admin"
    elif username==MANAGER_USERNAME: role="manager"
    users[uid]={"chat_id":user.id,"username":user.username or "","role":role or "user"}
    save_users(users)
    return users[uid]
def registered_role(uid): return load_users().get(str(uid),{}).get("role")
def manager_chat_id():
    if MANAGER_CHAT_ID: return MANAGER_CHAT_ID
    users=load_users()
    for u in users.values():
        if u.get("role")=="manager" and u.get("chat_id"): return u["chat_id"]
    return None
def t(uid,k): return LANGS[langs.get(uid,"ru")][k]
def is_admin(uid):
    return (ADMIN_ID and str(uid)==str(ADMIN_ID)) or registered_role(uid)=="admin"

async def start(update, context):
    uid=update.effective_user.id; register_user(update.effective_user); langs.setdefault(uid,"ru")
    kb=InlineKeyboardMarkup([
      [InlineKeyboardButton("🇷🇺 Русский",callback_data="l_ru"),InlineKeyboardButton("🇺🇦 Українська",callback_data="l_uk")],
      [InlineKeyboardButton("🇵🇱 Polski",callback_data="l_pl"),InlineKeyboardButton("🇬🇧 English",callback_data="l_en")],
      [InlineKeyboardButton("🔞 18+ — подтвердить",callback_data="age")]])
    await update.message.reply_text("VYBEX\n\n"+t(uid,"age"),reply_markup=kb)

async def admin(update,context):
    uid=update.effective_user.id
    if not is_admin(uid): return
    kb=InlineKeyboardMarkup([
      [InlineKeyboardButton("➕ Добавить товар",callback_data="a_add")],
      [InlineKeyboardButton("📋 Товары",callback_data="a_list")],
      [InlineKeyboardButton("🗑 Удалить товар",callback_data="a_delete")],
    ])
    await update.message.reply_text("⚙️ Админ-панель",reply_markup=kb)

async def cb(update,context):
    q=update.callback_query; await q.answer(); uid=q.from_user.id; d=q.data
    if d.startswith("l_"):
        langs[uid]=d[2:]; await q.edit_message_text("VYBEX",reply_markup=main(uid)); return
    if d=="age":
        await q.edit_message_text("VYBEX\n\n"+t(uid,"age"),reply_markup=main(uid)); return
    if d=="catalog":
        kb=[[InlineKeyboardButton(c,callback_data=f"c:{i}")] for i,c in enumerate(data()["categories"])]
        kb += [[InlineKeyboardButton(t(uid,"manager"),callback_data="manager")],[InlineKeyboardButton(t(uid,"lang"),callback_data="langs")]]
        await q.edit_message_text(t(uid,"cat"),reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="langs":
        await q.edit_message_text(t(uid,"lang"),reply_markup=InlineKeyboardMarkup([
          [InlineKeyboardButton("🇷🇺",callback_data="l_ru"),InlineKeyboardButton("🇺🇦",callback_data="l_uk")],
          [InlineKeyboardButton("🇵🇱",callback_data="l_pl"),InlineKeyboardButton("🇬🇧",callback_data="l_en")]])); return
    if d.startswith("c:"):
        cat=data()["categories"][int(d[2:])]
        products=[p for p in data()["products"] if p["category"]==cat and p.get("active",True)]
        if not products:
            await q.edit_message_text(cat+"\n\n"+t(uid,"info"),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(uid,"manager"),callback_data="manager")]])); return
        kb=[[InlineKeyboardButton(p["name"],callback_data=f"p:{p['id']}")] for p in products]
        await q.edit_message_text(cat,reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("p:"):
        p=next((x for x in data()["products"] if x["id"]==d[2:]),None)
        if not p: return
        text=f"📦 {p['name']}\n\n{p.get('description','')}\n\n{t(uid,'info')}"
        await q.message.reply_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(uid,"manager"),callback_data=f"m:{p['id']}")]]))
        if p.get("photo"):
            try: await q.message.reply_photo(p["photo"],caption=p["name"])
            except: pass
        return
    if d.startswith("m:"):
        forms[uid]={"step":"name","product":d[2:]}
        await q.edit_message_text(t(uid,"name")); return
    if d=="manager":
        forms[uid]={"step":"name","product":""}; await q.edit_message_text(t(uid,"name")); return

    if is_admin(uid):
        dta=data()
        if d=="a_add":
            admin_state[uid]={"step":"name"}; await q.edit_message_text("➕ Введите название товара:"); return
        if d=="a_list":
            lines=[f"{p['id']} — {p['name']} ({p['category']})" for p in dta["products"]]
            await q.edit_message_text("📋 Товары\n\n"+("\n".join(lines) if lines else "Пусто")); return
        if d=="a_delete":
            admin_state[uid]={"step":"delete"}; await q.edit_message_text("Введите ID товара для удаления:"); return

async def text(update,context):
    uid=update.effective_user.id; msg=update.message
    if is_admin(uid) and uid in admin_state:
        st=admin_state[uid]; d=data()
        if st["step"]=="name":
            st["name"]=msg.text; st["step"]="category"
            kb=[[InlineKeyboardButton(c,callback_data=f"admincat:{c}")] for c in d["categories"]]
            await msg.reply_text("Выберите категорию:",reply_markup=InlineKeyboardMarkup(kb)); return
        if st["step"]=="description":
            st["description"]=msg.text; st["step"]="photo"
            await msg.reply_text("Отправьте фото товара. Если фото не нужно, отправьте /skip."); return
        if st["step"]=="delete":
            before=len(d["products"]); d["products"]=[p for p in d["products"] if p["id"]!=msg.text.strip()]
            save(d); admin_state.pop(uid,None); await msg.reply_text("Удалено." if len(d["products"])<before else "ID не найден."); return

    f=forms.get(uid)
    if not f: return
    if f["step"]=="name":
        f["name"]=msg.text; f["step"]="phone"; await msg.reply_text(t(uid,"phone")); return
    if f["step"]=="phone":
        f["phone"]=msg.text; f["step"]="district"
        await msg.reply_text(t(uid,"district"),reply_markup=InlineKeyboardMarkup([
          [InlineKeyboardButton("Targówek",callback_data="d:Targówek")],
          [InlineKeyboardButton("Bemowo",callback_data="d:Bemowo")],
          [InlineKeyboardButton("Wola",callback_data="d:Wola")]])); return
    if f["step"]=="interest":
        f["interest"]=msg.text; await send_lead(update,context,f); return

async def admin_cb(update,context):
    q=update.callback_query; await q.answer(); uid=q.from_user.id
    if not is_admin(uid): return
    d=q.data
    if d.startswith("admincat:"):
        st=admin_state[uid]; st["category"]=d.split(":",1)[1]; st["step"]="description"
        await q.edit_message_text("Введите описание товара:"); return
    if d.startswith("d:"):
        f=forms[uid]; f["district"]=d[2:]; f["step"]="interest"
        await q.edit_message_text(t(uid,"interest")); return

async def photo(update,context):
    uid=update.effective_user.id
    if not is_admin(uid) or uid not in admin_state: return
    st=admin_state[uid]
    if st.get("step")!="photo": return
    d=data(); pid=str(max([int(p["id"]) for p in d["products"] if str(p["id"]).isdigit()] or [0])+1)
    d["products"].append({"id":pid,"name":st["name"],"category":st["category"],"description":st["description"],"photo":update.message.photo[-1].file_id,"active":True})
    save(d); admin_state.pop(uid,None)
    await update.message.reply_text(f"✅ Товар добавлен. ID: {pid}")

async def skip(update,context):
    uid=update.effective_user.id
    if is_admin(uid) and admin_state.get(uid,{}).get("step")=="photo":
        st=admin_state[uid]; d=data(); pid=str(max([int(p["id"]) for p in d["products"] if str(p["id"]).isdigit()] or [0])+1)
        d["products"].append({"id":pid,"name":st["name"],"category":st["category"],"description":st["description"],"photo":None,"active":True})
        save(d); admin_state.pop(uid,None); await update.message.reply_text(f"✅ Товар добавлен. ID: {pid}")

async def send_lead(update,context,f):
    uid=update.effective_user.id
    manager_id=manager_chat_id()
    if not manager_id:
        await update.message.reply_text("Менеджер ещё не подключён. Пусть аккаунт @manager_VYBEX один раз откроет бота и нажмёт /start."); forms.pop(uid,None); return
    p=next((x for x in data()["products"] if x["id"]==f["product"]),None)
    text=(f"🔔 НОВАЯ ЗАЯВКА НА ЛИЧНУЮ ВСТРЕЧУ\n\nИмя: {f['name']}\nТелефон: {f['phone']}\nРайон: {f.get('district','')}\nТовар: {p['name'] if p else f.get('interest','')}\nTelegram: @{update.effective_user.username or 'нет'}\nID: {uid}")
    await context.bot.send_message(chat_id=manager_id,text=text)
    await update.message.reply_text(t(uid,"sent"))
    forms.pop(uid,None)

def main(uid):
    return InlineKeyboardMarkup([[InlineKeyboardButton(LANGS[langs.get(uid,"ru")]["cat"],callback_data="catalog")],
      [InlineKeyboardButton(LANGS[langs.get(uid,"ru")]["manager"],callback_data="manager")],
      [InlineKeyboardButton(LANGS[langs.get(uid,"ru")]["lang"],callback_data="langs")]])

app=Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("admin",admin))
app.add_handler(CommandHandler("skip",skip))
app.add_handler(CallbackQueryHandler(admin_cb,pattern=r"^(admincat:|d:)"))
app.add_handler(CallbackQueryHandler(cb))
app.add_handler(MessageHandler(filters.PHOTO,photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text))
app.run_polling()

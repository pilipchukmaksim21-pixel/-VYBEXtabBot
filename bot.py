import os, json, logging
from pathlib import Path
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = "829871240"  # Fixed administrator Telegram user ID
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "fvmfm1").lstrip("@").lower()
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "manager_VYBEX").lstrip("@").lower()
DATA = Path("catalog.json")
USERS = Path("users.json")
BUTTONS = Path("buttons.json")
BROADCAST = Path("broadcast.json")
PROMOS = Path("promos.json")
TZ = ZoneInfo("Europe/Warsaw")
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
carts={}


def ensure_file(path, default):
    if not path.exists(): path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")


def data():
    ensure_file(DATA, {"categories":[],"products":[]})
    try: return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception: return {"categories":[],"products":[]}


def save(d): DATA.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")


def load_users():
    ensure_file(USERS, {})
    try: return json.loads(USERS.read_text(encoding="utf-8"))
    except Exception: return {}


def save_users(d): USERS.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")


def load_buttons():
    ensure_file(BUTTONS, [])
    try: return json.loads(BUTTONS.read_text(encoding="utf-8"))
    except Exception: return []


def save_buttons(d): BUTTONS.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")


def load_broadcast():
    ensure_file(BROADCAST, {"enabled":False,"time":"20:00","text":"","video":None})
    try: return json.loads(BROADCAST.read_text(encoding="utf-8"))
    except Exception: return {"enabled":False,"time":"20:00","text":"","video":None}


def save_broadcast(d): BROADCAST.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")

def load_promos():
    ensure_file(PROMOS, [])
    try: return json.loads(PROMOS.read_text(encoding="utf-8"))
    except Exception: return []

def save_promos(d): PROMOS.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")


def register_user(user):
    users=load_users(); uid=str(user.id); username=(user.username or "").lstrip("@").lower()
    role=users.get(uid,{}).get("role")
    if str(user.id)==ADMIN_ID: role="admin"
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
    return str(uid)==ADMIN_ID


def next_id(items):
    nums=[int(x.get("id")) for x in items if str(x.get("id","")).isdigit()]
    return str(max(nums or [0])+1)


def find_button(bid):
    for b in load_buttons():
        if str(b.get("id"))==str(bid): return b
    return None


def root_buttons(): return [b for b in load_buttons() if not b.get("parent_id") and b.get("active",True)]


def child_buttons(parent_id): return [b for b in load_buttons() if str(b.get("parent_id"))==str(parent_id) and b.get("active",True)]


def button_editor_kb(bid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить название", callback_data=f"be_label:{bid}")],
        [InlineKeyboardButton("📝 Изменить текст", callback_data=f"be_text:{bid}")],
        [InlineKeyboardButton("🖼️ Добавить/изменить картинку", callback_data=f"be_photo:{bid}")],
        [InlineKeyboardButton("🎥 Добавить/изменить видео", callback_data=f"be_video:{bid}")],
        [InlineKeyboardButton("➕ Добавить вложенную кнопку", callback_data=f"be_add:{bid}")],
        [InlineKeyboardButton("🗑 Удалить кнопку", callback_data=f"be_del:{bid}")],
        [InlineKeyboardButton("◀️ К списку кнопок", callback_data="b_list")]
    ])

def all_button_rows():
    """Return a flat admin list with indentation so every nested button is directly editable."""
    bs=load_buttons(); by_parent={}
    for b in bs:
        by_parent.setdefault(str(b.get("parent_id") or "root"), []).append(b)
    rows=[]
    def walk(parent, depth=0):
        for b in by_parent.get(str(parent), []):
            prefix="  "*depth + ("↳ " if depth else "")
            rows.append([InlineKeyboardButton(prefix + b.get("label","Без названия"), callback_data=f"be_open:{b['id']}")])
            walk(b.get("id"), depth+1)
    walk("root")
    return rows


def render_button(b):
    rows=[]
    for c in child_buttons(b["id"]):
        rows.append([InlineKeyboardButton(c["label"],callback_data=f"custom:{c['id']}")])
    rows.append([InlineKeyboardButton("◀️ Назад",callback_data=f"custom_back:{b.get('parent_id') or 'root'}")])
    return InlineKeyboardMarkup(rows)


def button_content_text(b):
    text=b.get("text") or ""
    if not text:
        text=""
    return text

async def start(update, context):
    uid=update.effective_user.id; register_user(update.effective_user); langs.setdefault(uid,"ru")
    kb=InlineKeyboardMarkup([
      [InlineKeyboardButton("🇺🇦 Українська",callback_data="l_uk"),InlineKeyboardButton("🇵🇱 Polski",callback_data="l_pl")],
      [InlineKeyboardButton("🇬🇧 English",callback_data="l_en"),InlineKeyboardButton("🇷🇺 Русский",callback_data="l_ru")],
      [InlineKeyboardButton("🔞 18+ — подтвердить",callback_data="age")]])
    await update.message.reply_text("VYBEX\n\n"+t(uid,"age"),reply_markup=kb)

async def admin(update,context):
    uid=update.effective_user.id
    if not is_admin(uid): return
    kb=InlineKeyboardMarkup([
      [InlineKeyboardButton("➕ Добавить товар",callback_data="a_add")],
      [InlineKeyboardButton("📋 Товары",callback_data="a_list")],
      [InlineKeyboardButton("🗑 Удалить товар",callback_data="a_delete")],
      [InlineKeyboardButton("🧩 Конструктор кнопок",callback_data="b_menu")],
      [InlineKeyboardButton("📣 Реклама",callback_data="ad_menu")],
      [InlineKeyboardButton("🏷️ Акции",callback_data="promo_menu")],
    ])
    await update.message.reply_text("⚙️ Админ-панель",reply_markup=kb)

async def show_button(update, context, b, edit=False):
    text = button_content_text(b)
    markup = render_button(b)
    target = update.callback_query.message if edit else update.message

    if text:
        if edit:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=markup)
            except Exception:
                await target.reply_text(text, reply_markup=markup)
        else:
            await target.reply_text(text, reply_markup=markup)
        if b.get("photo"):
            try:
                await target.reply_photo(b["photo"])
            except Exception:
                pass
        if b.get("video"):
            try:
                await target.reply_video(b["video"])
            except Exception:
                pass
    else:
        # Text is optional. If absent, media (if any) carries the button keyboard.
        if b.get("photo"):
            try:
                await target.reply_photo(b["photo"], reply_markup=markup)
            except Exception:
                await target.reply_text(" ", reply_markup=markup)
        elif b.get("video"):
            try:
                await target.reply_video(b["video"], reply_markup=markup)
            except Exception:
                await target.reply_text(" ", reply_markup=markup)
        else:
            await target.reply_text(" ", reply_markup=markup)

async def cb(update,context):
    q=update.callback_query; await q.answer(); uid=q.from_user.id; d=q.data
    if d=="admin_panel":
        if not is_admin(uid):
            return
        await q.edit_message_text("⚙️ Адмін-панель",reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Додати товар",callback_data="a_add")],
            [InlineKeyboardButton("📋 Товари",callback_data="a_list")],
            [InlineKeyboardButton("🗑 Видалити товар",callback_data="a_delete")],
            [InlineKeyboardButton("🧩 Конструктор кнопок",callback_data="b_menu")],
            [InlineKeyboardButton("📣 Реклама",callback_data="ad_menu")],
            [InlineKeyboardButton("🏷️ Акции",callback_data="promo_menu")],
        ])); return
    if d.startswith("l_"):
        langs[uid]=d[2:]; await q.edit_message_text("VYBEX",reply_markup=main(uid)); return
    if d=="age":
        await q.edit_message_text("VYBEX\n\n"+t(uid,"age"),reply_markup=main(uid)); return
    if d=="catalog":
        kb=[[InlineKeyboardButton(c,callback_data=f"c:{i}")] for i,c in enumerate(data()["categories"])]
        kb += [[InlineKeyboardButton("🛒 Мій список",callback_data="cart")],[InlineKeyboardButton("🏷️ Акції",callback_data="promos")],[InlineKeyboardButton(t(uid,"manager"),callback_data="manager")],[InlineKeyboardButton(t(uid,"lang"),callback_data="langs")]]
        await q.edit_message_text(t(uid,"cat"),reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="langs":
        await q.edit_message_text(t(uid,"lang"),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🇺🇦",callback_data="l_uk"),InlineKeyboardButton("🇵🇱",callback_data="l_pl")],[InlineKeyboardButton("🇬🇧",callback_data="l_en"),InlineKeyboardButton("🇷🇺",callback_data="l_ru")]])); return
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
        await q.message.reply_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Додати до списку",callback_data=f"add:{p['id']}" )],[InlineKeyboardButton("🛒 Мій список",callback_data="cart")],[InlineKeyboardButton(t(uid,"manager"),callback_data=f"m:{p['id']}")]]))
        if p.get("photo"):
            try: await q.message.reply_photo(p["photo"],caption=p["name"])
            except: pass
        return
    if d.startswith("m:"):
        forms[uid]={"step":"name","product":d[2:]}; await q.edit_message_text(t(uid,"name")); return
    if d=="manager":
        forms[uid]={"step":"name","product":""}; await q.edit_message_text(t(uid,"name")); return
    if d.startswith("add:"):
        pid=d[4:]; p=next((x for x in data()["products"] if x["id"]==pid),None)
        if p:
            carts.setdefault(uid,[])
            carts[uid].append(pid)
            await q.answer("Додано до списку",show_alert=False)
        return
    if d=="cart":
        items=carts.get(uid,[])
        products=data()["products"]
        names=[next((p["name"] for p in products if p["id"]==pid),pid) for pid in items]
        if not names:
            await q.edit_message_text("🛒 Мій список порожній.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="catalog")]])); return
        text="🛒 Мій список\n\n"+"\n".join(f"• {n}" for n in names)+"\n\nЦе список для узгодження з менеджером."
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Передати менеджеру",callback_data="cart_manager")],[InlineKeyboardButton("🗑 Очистити список",callback_data="cart_clear")],[InlineKeyboardButton("◀️ Назад",callback_data="catalog")]])); return
    if d=="cart_clear":
        carts[uid]=[]
        await q.edit_message_text("🗑 Список очищено.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Каталог",callback_data="catalog")]])); return
    if d=="cart_manager":
        items=carts.get(uid,[])
        if not items:
            await q.answer("Список порожній",show_alert=True); return
        forms[uid]={"step":"name","product":"CART","cart":items[:]}
        await q.edit_message_text(t(uid,"name")); return
    if d=="promos":
        promos=[x for x in load_promos() if x.get("active",True)]
        if not promos:
            await q.edit_message_text("🏷️ Акцій зараз немає.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="catalog")]])); return
        for pr in promos:
            txt="🏷️ "+pr.get("title","")+"\n\n"+pr.get("text","")
            await q.message.reply_text(txt)
        await q.message.reply_text("🏷️ Акції",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="catalog")]])); return

    if d.startswith("custom_back:"):
        target=d.split(":",1)[1]
        if target=="root": await q.edit_message_text("VYBEX",reply_markup=main(uid)); return
        b=find_button(target)
        if b: await show_button(update,context,b,edit=True)
        return
    if d.startswith("custom:"):
        bid=d.split(":",1)[1]; b=find_button(bid)
        if b: await show_button(update,context,b,edit=True)
        return

    if is_admin(uid):
        dta=data()
        if d=="b_menu":
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Создать кнопку",callback_data="b_add")],
              [InlineKeyboardButton("📋 Управление кнопками",callback_data="b_list")],
              [InlineKeyboardButton("🗑 Удалить кнопку",callback_data="b_delete")]])
            await q.edit_message_text("🧩 Конструктор кнопок\n\nСоздавай кнопки и внутри каждой добавляй другие кнопки, текст и видео.",reply_markup=kb); return
        if d=="b_add":
            admin_state[uid]={"step":"button_label","parent_id":None}; await q.edit_message_text("Введите название главной кнопки:"); return
        if d=="b_list":
            kb=all_button_rows()
            if not kb:
                await q.edit_message_text("📋 Пока нет кнопок.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="b_menu")]])); return
            kb.append([InlineKeyboardButton("◀️ Назад",callback_data="b_menu")])
            await q.edit_message_text("📋 Нажми на любую кнопку — можно редактировать даже вложенные кнопки:",reply_markup=InlineKeyboardMarkup(kb)); return
        if d=="b_delete":
            admin_state[uid]={"step":"button_delete"}; await q.edit_message_text("Введите ID кнопки. Будут удалены и её вложенные кнопки:"); return
        if d.startswith("be_open:"):
            bid=d.split(":",1)[1]; b=find_button(bid)
            if b: await q.edit_message_text(f"🔧 {b['label']}\nID: {b['id']}\n\nТекст: {'есть' if b.get('text') else 'нет'}\nВидео: {'есть' if b.get('video') else 'нет'}\nВложенных кнопок: {len(child_buttons(b['id']))}",reply_markup=button_editor_kb(bid))
            return
        if d.startswith("be_add:"):
            parent=d.split(":",1)[1]; admin_state[uid]={"step":"button_label","parent_id":parent}; await q.edit_message_text("Введите название вложенной кнопки:"); return
        if d.startswith("be_label:"):
            bid=d.split(":",1)[1]; admin_state[uid]={"step":"button_label_edit","button_id":bid}; await q.edit_message_text("Введите новое название кнопки:"); return
        if d.startswith("be_text:"):
            bid=d.split(":",1)[1]; admin_state[uid]={"step":"button_text","button_id":bid}; await q.edit_message_text("Відправте новий текст або /skip, щоб залишити кнопку без тексту:"); return
        if d.startswith("be_photo:"):
            bid=d.split(":",1)[1]; admin_state[uid]={"step":"button_photo","button_id":bid}; await q.edit_message_text("Відправте картинку або /skip, щоб видалити картинку:"); return
        if d.startswith("be_video:"):
            bid=d.split(":",1)[1]; admin_state[uid]={"step":"button_video","button_id":bid}; await q.edit_message_text("Отправьте видео для этой кнопки. Можно MP4/Telegram video:"); return
        if d.startswith("be_del:"):
            bid=d.split(":",1)[1]; bs=load_buttons(); ids={bid}; changed=True
            while changed:
                changed=False
                for b in bs:
                    if str(b.get("parent_id")) in ids and str(b.get("id")) not in ids: ids.add(str(b.get("id"))); changed=True
            new=[b for b in bs if str(b.get("id")) not in ids]; save_buttons(new)
            await q.edit_message_text("🗑 Кнопка и её вложенные кнопки удалены.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К конструктору",callback_data="b_menu")]])); return
        if d=="promo_menu":
            promos=load_promos()
            rows=[[InlineKeyboardButton("➕ Створити акцію",callback_data="promo_add")]]
            for pr in promos:
                rows.append([InlineKeyboardButton(("🟢 " if pr.get("active",True) else "🔴 ")+pr.get("title",""),callback_data=f"promo_open:{pr['id']}")])
            rows.append([InlineKeyboardButton("◀️ Адмін-панель",callback_data="admin_back")])
            await q.edit_message_text("🏷️ Управління акціями",reply_markup=InlineKeyboardMarkup(rows)); return
        if d=="promo_add":
            admin_state[uid]={"step":"promo_title"}; await q.edit_message_text("Введіть назву акції:"); return
        if d.startswith("promo_open:"):
            pid=d.split(":",1)[1]; pr=next((x for x in load_promos() if x.get("id")==pid),None)
            if not pr: return
            await q.edit_message_text("🏷️ "+pr.get("title","")+"\n\n"+pr.get("text","")+f"\n\nСтатус: {'🟢 активна' if pr.get('active',True) else '🔴 вимкнена'}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✏️ Редагувати текст",callback_data=f"promo_edit:{pid}")],[InlineKeyboardButton("⏯ Увімк./вимк.",callback_data=f"promo_toggle:{pid}")],[InlineKeyboardButton("🗑 Видалити",callback_data=f"promo_del:{pid}")],[InlineKeyboardButton("◀️ Назад",callback_data="promo_menu")]])); return
        if d.startswith("promo_edit:"):
            pid=d.split(":",1)[1]; admin_state[uid]={"step":"promo_edit","promo_id":pid}; await q.edit_message_text("Введіть новий текст акції:"); return
        if d.startswith("promo_toggle:"):
            pid=d.split(":",1)[1]; ps=load_promos()
            for pr in ps:
                if pr.get("id")==pid: pr["active"]=not pr.get("active",True)
            save_promos(ps); await q.edit_message_text("Статус акції змінено.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="promo_menu")]])); return
        if d.startswith("promo_del:"):
            pid=d.split(":",1)[1]; save_promos([x for x in load_promos() if x.get("id")!=pid]); await q.edit_message_text("🗑 Акцію видалено.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="promo_menu")]])); return

        if d=="ad_menu":
            ad=load_broadcast(); status="🟢 включена" if ad.get("enabled") else "🔴 выключена"
            kb=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Создать/изменить рассылку",callback_data="ad_create")],
                [InlineKeyboardButton("⏯ Вкл/выкл ежедневную рассылку",callback_data="ad_toggle")],
                [InlineKeyboardButton("🗑 Удалить рассылку",callback_data="ad_delete")],
                [InlineKeyboardButton("◀️ Админ-панель",callback_data="admin_back")]
            ])
            await q.edit_message_text(f"📣 Реклама / ежедневные объявления\n\nСтатус: {status}\nВремя: {ad.get('time','20:00')} (Варшава)\nТекст: {'есть' if ad.get('text') else 'нет'}\nВидео: {'есть' if ad.get('video') else 'нет'}",reply_markup=kb); return
        if d=="ad_create":
            admin_state[uid]={"step":"ad_text"}; await q.edit_message_text("Введите текст ежедневного сообщения:"); return
        if d=="ad_toggle":
            ad=load_broadcast(); ad["enabled"]=not ad.get("enabled",False); save_broadcast(ad); schedule_broadcast(context.application)
            await q.edit_message_text("📣 Ежедневная рассылка теперь "+("🟢 включена" if ad["enabled"] else "🔴 выключена"),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="ad_menu")]])); return
        if d=="ad_delete":
            save_broadcast({"enabled":False,"time":"20:00","text":"","video":None}); schedule_broadcast(context.application)
            await q.edit_message_text("🗑 Ежедневная рассылка удалена.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад",callback_data="ad_menu")]])); return
        if d=="admin_back":
            await q.edit_message_text("⚙️ Админ-панель",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧩 Конструктор кнопок",callback_data="b_menu")],[InlineKeyboardButton("📣 Реклама",callback_data="ad_menu")],[InlineKeyboardButton("🏷️ Акції",callback_data="promo_menu")]])); return
        if d.startswith("ad_video_yes"):
            admin_state[uid]["step"]="ad_video"; await q.edit_message_text("Отправьте видео. Если видео не нужно, отправьте /skip:"); return
        if d.startswith("ad_video_no"):
            admin_state[uid]["video"]=None; admin_state[uid]["step"]="ad_time"; await q.edit_message_text("Введите время ежедневной рассылки в формате HH:MM по Варшаве, например 20:00:"); return
    
    if d.startswith("d:"):
        f=forms[uid]; f["district"]=d[2:]; f["step"]="interest"; await q.edit_message_text(t(uid,"interest")); return

async def finish_button(uid, message):
    st=admin_state.get(uid,{})
    bs=load_buttons(); bid=next_id(bs)
    bs.append({
        "id":bid,
        "label":st["label"],
        "parent_id":st.get("parent_id"),
        "text":st.get("text",""),
        "photo":st.get("photo"),
        "video":None,
        "active":True
    })
    save_buttons(bs); admin_state.pop(uid,None)
    await message.reply_text(f"✅ Кнопка создана. ID: {bid}")

async def text(update,context):
    uid=update.effective_user.id; msg=update.message
    if is_admin(uid) and uid in admin_state:
        st=admin_state[uid]; d=data(); step=st["step"]
        if step=="promo_title":
            st["title"]=msg.text.strip(); st["step"]="promo_text"; await msg.reply_text("Введіть текст акції:"); return
        if step=="promo_text":
            ps=load_promos(); nums=[int(x.get("id")) for x in ps if str(x.get("id","")).isdigit()]; pid=str(max(nums or [0])+1)
            ps.append({"id":pid,"title":st["title"],"text":msg.text,"active":True}); save_promos(ps); admin_state.pop(uid,None); await msg.reply_text("✅ Акцію створено."); return
        if step=="promo_edit":
            ps=load_promos(); pid=st["promo_id"]
            for pr in ps:
                if pr.get("id")==pid: pr["text"]=msg.text
            save_promos(ps); admin_state.pop(uid,None); await msg.reply_text("✅ Акцію оновлено."); return

        if step=="button_label":
            st["label"]=msg.text.strip()
            st["step"]="button_text_create"
            await msg.reply_text("📝 Введіть текст для кнопки або /skip, якщо текст не потрібен:")
            return
        if step=="button_text_create":
            st["text"]=msg.text
            st["step"]="button_photo_create"
            await msg.reply_text("🖼️ Додайте картинку або /skip, якщо картинка не потрібна:")
            return
        if step=="button_label_edit":
            bid=st["button_id"]; bs=load_buttons(); found=False
            for b in bs:
                if str(b.get("id"))==str(bid): b["label"]=msg.text.strip(); found=True
            save_buttons(bs); admin_state.pop(uid,None)
            await msg.reply_text("✅ Название кнопки изменено." if found else "❌ Кнопка не найдена."); return
        if step=="button_text":
            bid=st["button_id"]; bs=load_buttons(); found=False
            for b in bs:
                if str(b.get("id"))==str(bid): b["text"]=msg.text; found=True
            save_buttons(bs); admin_state.pop(uid,None); await msg.reply_text("✅ Текст сохранён." if found else "❌ Кнопка не найдена."); return
        if step in ("button_photo_create","button_photo"):
            await msg.reply_text("Надішліть картинку або /skip.")
            return
        if step=="button_delete":
            bid=msg.text.strip(); bs=load_buttons(); ids={bid}; changed=True
            while changed:
                changed=False
                for b in bs:
                    if str(b.get("parent_id")) in ids and str(b.get("id")) not in ids: ids.add(str(b.get("id"))); changed=True
            new=[b for b in bs if str(b.get("id")) not in ids]; save_buttons(new); admin_state.pop(uid,None)
            await msg.reply_text("🗑 Удалено." if len(new)<len(bs) else "ID не найден."); return
        if step=="ad_text":
            st["text"]=msg.text; st["step"]="ad_video_choice"
            await msg.reply_text("Добавить видео к ежедневному сообщению?",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎥 Да",callback_data="ad_video_yes")],[InlineKeyboardButton("Без видео",callback_data="ad_video_no")]])); return
        if step=="ad_time":
            raw=msg.text.strip()
            try:
                hh,mm=map(int,raw.split(":")); assert 0<=hh<24 and 0<=mm<60
            except Exception:
                await msg.reply_text("Неверный формат. Введите HH:MM, например 20:00:"); return
            ad=load_broadcast(); ad.update({"enabled":True,"time":f"{hh:02d}:{mm:02d}","text":st.get("text",""),"video":st.get("video")}); save_broadcast(ad); admin_state.pop(uid,None); schedule_broadcast(context.application)
            await msg.reply_text(f"✅ Ежедневная рассылка сохранена и включена на {ad['time']} по Варшаве."); return
        if step=="name":
            st["name"]=msg.text; st["step"]="category"
            kb=[[InlineKeyboardButton(c,callback_data=f"admincat:{c}")] for c in d["categories"]]
            await msg.reply_text("Выберите категорию:",reply_markup=InlineKeyboardMarkup(kb)); return
        if step=="description":
            st["description"]=msg.text; st["step"]="photo"; await msg.reply_text("Отправьте фото товара. Если фото не нужно, отправьте /skip."); return
        if step=="delete":
            before=len(d["products"]); d["products"]=[p for p in d["products"] if p["id"]!=msg.text.strip()]; save(d); admin_state.pop(uid,None); await msg.reply_text("Удалено." if len(d["products"])<before else "ID не найден."); return

    f=forms.get(uid)
    if not f: return
    if f["step"]=="name": f["name"]=msg.text; f["step"]="phone"; await msg.reply_text(t(uid,"phone")); return
    if f["step"]=="phone":
        f["phone"]=msg.text; f["step"]="district"; await msg.reply_text(t(uid,"district"),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Targówek",callback_data="d:Targówek")],[InlineKeyboardButton("Bemowo",callback_data="d:Bemowo")],[InlineKeyboardButton("Wola",callback_data="d:Wola")]])); return
    if f["step"]=="interest": f["interest"]=msg.text; await send_lead(update,context,f); return

async def photo(update,context):
    uid=update.effective_user.id
    if not is_admin(uid) or uid not in admin_state: return
    st=admin_state[uid]
    if st.get("step")=="button_photo_create":
        st["photo"]=update.message.photo[-1].file_id
        await finish_button(uid, update.message)
        return
    if st.get("step")=="button_photo":
        bs=load_buttons(); bid=st["button_id"]; found=False
        for b in bs:
            if str(b.get("id"))==str(bid):
                b["photo"]=update.message.photo[-1].file_id
                found=True
        save_buttons(bs); admin_state.pop(uid,None)
        await update.message.reply_text("✅ Картинка кнопки сохранена." if found else "❌ Кнопка не найдена.")
        return
    if st.get("step")!="photo": return
    d=data(); pid=next_id(d["products"])
    d["products"].append({"id":pid,"name":st["name"],"category":st["category"],"description":st["description"],"photo":update.message.photo[-1].file_id,"active":True})
    save(d); admin_state.pop(uid,None); await update.message.reply_text(f"✅ Товар добавлен. ID: {pid}")

async def video(update,context):
    uid=update.effective_user.id
    if not is_admin(uid) or uid not in admin_state: return
    st=admin_state[uid]
    if st.get("step")=="button_video":
        bs=load_buttons(); bid=st["button_id"]
        for b in bs:
            if str(b.get("id"))==str(bid): b["video"]=update.message.video.file_id
        save_buttons(bs); admin_state.pop(uid,None); await update.message.reply_text("✅ Видео кнопки сохранено."); return
    if st.get("step")=="ad_video":
        st["video"]=update.message.video.file_id; st["step"]="ad_time"; await update.message.reply_text("Введите время ежедневной рассылки в формате HH:MM по Варшаве, например 20:00:"); return

async def skip(update,context):
    uid=update.effective_user.id
    if not is_admin(uid): return
    st=admin_state.get(uid,{})
    if st.get("step")=="button_text_create":
        st["text"]=""; st["step"]="button_photo_create"
        await update.message.reply_text("🖼️ Додайте картинку або /skip, якщо картинка не потрібна:")
        return
    if st.get("step")=="button_photo_create":
        st["photo"]=None
        await finish_button(uid, update.message)
        return
    if st.get("step")=="button_text":
        bid=st["button_id"]; bs=load_buttons()
        for b in bs:
            if str(b.get("id"))==str(bid): b["text"]=""
        save_buttons(bs); admin_state.pop(uid,None)
        await update.message.reply_text("✅ Текст кнопки очищено.")
        return
    if st.get("step")=="button_photo":
        bid=st["button_id"]; bs=load_buttons()
        for b in bs:
            if str(b.get("id"))==str(bid): b["photo"]=None
        save_buttons(bs); admin_state.pop(uid,None)
        await update.message.reply_text("✅ Картинку кнопки видалено.")
        return
    if st.get("step")=="photo":
        d=data(); pid=next_id(d["products"])
        d["products"].append({"id":pid,"name":st["name"],"category":st["category"],"description":st["description"],"photo":None,"active":True})
        save(d); admin_state.pop(uid,None); await update.message.reply_text(f"✅ Товар добавлен. ID: {pid}"); return
    if st.get("step")=="ad_video":
        st["video"]=None; st["step"]="ad_time"; await update.message.reply_text("Введите время ежедневной рассылки в формате HH:MM по Варшаве, например 20:00:")

async def send_lead(update,context,f):
    uid=update.effective_user.id; manager_id=manager_chat_id()
    if not manager_id:
        await update.message.reply_text("Менеджер ещё не подключён. Пусть аккаунт @manager_VYBEX один раз откроет бота и нажмёт /start."); forms.pop(uid,None); return
    p=next((x for x in data()["products"] if x["id"]==f["product"]),None)
    if f.get("product")=="CART":
        names=[next((x["name"] for x in data()["products"] if x["id"]==pid),pid) for pid in f.get("cart",[])]
        item_text="\n".join("• "+n for n in names)
    else:
        item_text=p["name"] if p else f.get("interest","")
    text=(f"🔔 НОВАЯ ЗАЯВКА НА ЛИЧНУЮ ВСТРЕЧУ\n\nИмя: {f['name']}\nТелефон: {f['phone']}\nРайон: {f.get('district','')}\nТовар(и): {item_text}\nTelegram: @{update.effective_user.username or 'нет'}\nID: {uid}")
    await context.bot.send_message(chat_id=manager_id,text=text); await update.message.reply_text(t(uid,"sent")); forms.pop(uid,None); carts[uid]=[]


def main(uid):
    rows=[[InlineKeyboardButton(LANGS[langs.get(uid,"ru")]["cat"],callback_data="catalog")],[InlineKeyboardButton("🛒 Мій список",callback_data="cart"),InlineKeyboardButton("🏷️ Акції",callback_data="promos")],[InlineKeyboardButton(LANGS[langs.get(uid,"ru")]["manager"],callback_data="manager")],[InlineKeyboardButton(LANGS[langs.get(uid,"ru")]["lang"],callback_data="langs")]]
    for b in root_buttons(): rows.append([InlineKeyboardButton(b["label"],callback_data=f"custom:{b['id']}")])
    # Admin button is visible only to the fixed Telegram user ID 829871240.
    if str(uid)==ADMIN_ID:
        rows.append([InlineKeyboardButton("⚙️ Адмін",callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)

async def daily_broadcast(context):
    ad=load_broadcast()
    if not ad.get("enabled") or not ad.get("text"): return
    users=load_users()
    for u in users.values():
        if u.get("role") in ("admin","manager"): continue
        cid=u.get("chat_id")
        if not cid: continue
        try:
            await context.bot.send_message(chat_id=cid,text=ad["text"])
            if ad.get("video"): await context.bot.send_video(chat_id=cid,video=ad["video"])
        except Exception as e:
            logging.warning("broadcast to %s failed: %s",cid,e)


def schedule_broadcast(application):
    jq=application.job_queue
    if jq is None: return
    for job in jq.get_jobs_by_name("vybex_daily_broadcast"): job.schedule_removal()
    ad=load_broadcast()
    if not ad.get("enabled"): return
    try:
        hh,mm=map(int,ad.get("time","20:00").split(":"))
        jq.run_daily(daily_broadcast,time=__import__('datetime').time(hh,mm,tzinfo=TZ),name="vybex_daily_broadcast")
    except Exception as e:
        logging.exception("schedule error: %s",e)

async def post_init(application):
    schedule_broadcast(application)

app=Application.builder().token(TOKEN).post_init(post_init).build()
app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("admin",admin))
app.add_handler(CommandHandler("skip",skip))
app.add_handler(CallbackQueryHandler(cb))
app.add_handler(MessageHandler(filters.PHOTO,photo))
app.add_handler(MessageHandler(filters.VIDEO,video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text))
app.run_polling()

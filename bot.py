import os
import json
import logging
from pathlib import Path
from datetime import time as dt_time
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = "829871240"
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
log = logging.getLogger("vybex")

LANGS = {
    "ru": {
        "cat": "🛍 Каталог", "manager": "💬 Связаться с менеджером", "lang": "🌐 Язык",
        "back": "◀️ Назад", "age": "🔞 Только 18+",
        "info": "Информационный каталог. Для товара свяжитесь с менеджером.",
        "name": "Введите имя:", "phone": "Введите номер телефона:",
        "district": "Выберите район встречи:", "interest": "Какой товар вас интересует?",
        "sent": "✅ Заявка отправлена менеджеру.", "admin": "⚙️ Админ-панель",
    },
    "uk": {
        "cat": "🛍 Каталог", "manager": "💬 Зв'язатися з менеджером", "lang": "🌐 Мова",
        "back": "◀️ Назад", "age": "🔞 Лише 18+",
        "info": "Інформаційний каталог. Для товару зв'яжіться з менеджером.",
        "name": "Введіть ім'я:", "phone": "Введіть номер телефону:",
        "district": "Оберіть район зустрічі:", "interest": "Який товар вас цікавить?",
        "sent": "✅ Заявку надіслано менеджеру.", "admin": "⚙️ Адмін-панель",
    },
    "pl": {
        "cat": "🛍 Katalog", "manager": "💬 Kontakt z menedżerem", "lang": "🌐 Język",
        "back": "◀️ Wstecz", "age": "🔞 Tylko 18+",
        "info": "Katalog informacyjny. Skontaktuj się z menedżerem.",
        "name": "Podaj imię:", "phone": "Podaj numer telefonu:",
        "district": "Wybierz dzielnicę spotkania:", "interest": "Jaki produkt Cię interesuje?",
        "sent": "✅ Zgłoszenie wysłane do menedżera.", "admin": "⚙️ Panel administratora",
    },
    "en": {
        "cat": "🛍 Catalog", "manager": "💬 Contact manager", "lang": "🌐 Language",
        "back": "◀️ Back", "age": "🔞 18+ only",
        "info": "Informational catalog. Contact the manager for the product.",
        "name": "Enter your name:", "phone": "Enter your phone number:",
        "district": "Choose meeting district:", "interest": "Which product interests you?",
        "sent": "✅ Request sent to manager.", "admin": "⚙️ Admin panel",
    },
}

langs = {}
forms = {}
admin_state = {}
carts = {}


def ensure_file(path: Path, default):
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path, default):
    ensure_file(path, default)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        log.exception("Could not read %s", path)
        return default


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def data():
    d = read_json(DATA, {"categories": [], "products": []})
    if not isinstance(d, dict):
        d = {"categories": [], "products": []}
    d.setdefault("categories", [])
    d.setdefault("products", [])
    return d


def save(d):
    write_json(DATA, d)


def load_users():
    return read_json(USERS, {})


def save_users(d):
    write_json(USERS, d)


def load_buttons():
    value = read_json(BUTTONS, [])
    return value if isinstance(value, list) else []


def save_buttons(d):
    write_json(BUTTONS, d)


def load_broadcast():
    default = {"enabled": False, "time": "20:00", "text": "", "video": None}
    value = read_json(BROADCAST, default)
    return value if isinstance(value, dict) else default


def save_broadcast(d):
    write_json(BROADCAST, d)


def load_promos():
    value = read_json(PROMOS, [])
    return value if isinstance(value, list) else []


def save_promos(d):
    write_json(PROMOS, d)


def register_user(user):
    users = load_users()
    uid = str(user.id)
    username = (user.username or "").lstrip("@").lower()
    role = users.get(uid, {}).get("role")
    if uid == ADMIN_ID:
        role = "admin"
    elif username == MANAGER_USERNAME:
        role = "manager"
    users[uid] = {
        "chat_id": user.id,
        "username": user.username or "",
        "role": role or "user",
    }
    save_users(users)
    return users[uid]


def manager_chat_id():
    if MANAGER_CHAT_ID:
        return MANAGER_CHAT_ID
    for user in load_users().values():
        if user.get("role") == "manager" and user.get("chat_id"):
            return user["chat_id"]
    return None


def t(uid, key):
    return LANGS.get(langs.get(uid, "ru"), LANGS["ru"])[key]


def is_admin(uid):
    return str(uid) == ADMIN_ID


def next_id(items):
    nums = []
    for item in items:
        raw = item.get("id")
        if str(raw).isdigit():
            nums.append(int(raw))
    return str(max(nums or [0]) + 1)


def find_button(bid):
    return next((b for b in load_buttons() if str(b.get("id")) == str(bid)), None)


def root_buttons():
    return [b for b in load_buttons() if not b.get("parent_id") and b.get("active", True)]


def child_buttons(parent_id):
    return [b for b in load_buttons() if str(b.get("parent_id")) == str(parent_id) and b.get("active", True)]


def button_editor_kb(bid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить название", callback_data=f"be_label:{bid}")],
        [InlineKeyboardButton("📝 Изменить текст", callback_data=f"be_text:{bid}")],
        [InlineKeyboardButton("🖼️ Добавить/изменить картинку", callback_data=f"be_photo:{bid}")],
        [InlineKeyboardButton("🎥 Добавить/изменить видео", callback_data=f"be_video:{bid}")],
        [InlineKeyboardButton("➕ Добавить вложенную кнопку", callback_data=f"be_add:{bid}" )],
        [InlineKeyboardButton("🗑 Удалить кнопку", callback_data=f"be_del:{bid}" )],
        [InlineKeyboardButton("◀️ К списку кнопок", callback_data="b_list")],
    ])


def all_button_rows():
    bs = load_buttons()
    by_parent = {}
    for b in bs:
        by_parent.setdefault(str(b.get("parent_id") or "root"), []).append(b)
    rows = []

    def walk(parent, depth=0):
        for b in by_parent.get(str(parent), []):
            prefix = "  " * depth + ("↳ " if depth else "")
            rows.append([InlineKeyboardButton(prefix + b.get("label", "Без названия"), callback_data=f"be_open:{b['id']}")])
            walk(b.get("id"), depth + 1)

    walk("root")
    return rows


def render_button(b):
    rows = [[InlineKeyboardButton(c["label"], callback_data=f"custom:{c['id']}")] for c in child_buttons(b["id"])]
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data=f"custom_back:{b.get('parent_id') or 'root'}")])
    return InlineKeyboardMarkup(rows)


def button_content_text(b):
    return b.get("text") or ""


def product_by_id(pid):
    return next((p for p in data()["products"] if str(p.get("id")) == str(pid)), None)


def product_list_keyboard(action="open"):
    rows = []
    for p in data()["products"]:
        label = f"{p.get('id')}. {p.get('name', 'Без названия')}"
        rows.append([InlineKeyboardButton(label, callback_data=f"a_product:{p['id']}" if action == "open" else f"a_delprod:{p['id']}" )])
    return rows


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    register_user(update.effective_user)
    langs.setdefault(uid, "ru")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇦 Українська", callback_data="l_uk"), InlineKeyboardButton("🇵🇱 Polski", callback_data="l_pl")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="l_en"), InlineKeyboardButton("🇷🇺 Русский", callback_data="l_ru")],
        [InlineKeyboardButton("🔞 18+ — подтвердить", callback_data="age")],
    ])
    await update.message.reply_text("VYBEX\n\n" + t(uid, "age"), reply_markup=kb)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    register_user(update.effective_user)
    if not is_admin(uid):
        return
    await send_admin_panel(update, context, edit=False)


async def send_admin_panel(update, context, edit=False):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить товар", callback_data="a_add")],
        [InlineKeyboardButton("📋 Товары", callback_data="a_list")],
        [InlineKeyboardButton("🗑 Удалить товар", callback_data="a_delete")],
        [InlineKeyboardButton("🧩 Конструктор кнопок", callback_data="b_menu")],
        [InlineKeyboardButton("📣 Реклама", callback_data="ad_menu")],
        [InlineKeyboardButton("🏷️ Акции", callback_data="promo_menu")],
    ])
    if edit:
        await update.callback_query.edit_message_text("⚙️ Админ-панель", reply_markup=kb)
    else:
        await update.message.reply_text("⚙️ Админ-панель", reply_markup=kb)


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
                log.exception("Could not send button photo")
        if b.get("video"):
            try:
                await target.reply_video(b["video"])
            except Exception:
                log.exception("Could not send button video")
    elif b.get("photo"):
        try:
            await target.reply_photo(b["photo"], reply_markup=markup)
        except Exception:
            await target.reply_text("Без текста", reply_markup=markup)
    elif b.get("video"):
        try:
            await target.reply_video(b["video"], reply_markup=markup)
        except Exception:
            await target.reply_text("Без текста", reply_markup=markup)
    else:
        await target.reply_text("Без текста", reply_markup=markup)


async def finish_button(uid, message):
    st = admin_state.get(uid, {})
    bs = load_buttons()
    bid = next_id(bs)
    bs.append({
        "id": bid,
        "label": st.get("label", "Без названия"),
        "parent_id": st.get("parent_id"),
        "text": st.get("text", ""),
        "photo": st.get("photo"),
        "video": st.get("video"),
        "active": True,
    })
    save_buttons(bs)
    parent = st.get("parent_id")
    admin_state.pop(uid, None)
    await message.reply_text(
        f"✅ Кнопка создана. ID: {bid}\n"
        + ("Она добавлена внутрь родительской кнопки." if parent else "Она добавлена в главное меню.")
    )


async def handle_admin_skip_callback(q, context):
    uid = q.from_user.id
    if not is_admin(uid):
        return
    st = admin_state.get(uid, {})
    step = st.get("step")

    if step == "button_text_create":
        st["text"] = ""
        st["step"] = "button_photo_create"
        await q.edit_message_text(
            "🖼️ Добавьте картинку или нажмите «Пропустить».",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]),
        )
        return
    if step == "button_photo_create":
        st["photo"] = None
        await finish_button(uid, q.message)
        return
    if step == "button_text":
        bid = st.get("button_id")
        bs = load_buttons()
        for b in bs:
            if str(b.get("id")) == str(bid):
                b["text"] = ""
        save_buttons(bs)
        admin_state.pop(uid, None)
        await q.edit_message_text("✅ Текст кнопки очищено.")
        return
    if step == "button_photo":
        bid = st.get("button_id")
        bs = load_buttons()
        for b in bs:
            if str(b.get("id")) == str(bid):
                b["photo"] = None
        save_buttons(bs)
        admin_state.pop(uid, None)
        await q.edit_message_text("✅ Картинка кнопки удалена.")
        return
    if step == "promo_photo":
        st["photo"] = None
        st["step"] = "promo_video"
        await q.edit_message_text(
            "🎥 Добавьте видео акции или нажмите «Пропустить».",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]),
        )
        return
    if step == "promo_video":
        st["video"] = None
        save_promo_from_state(uid)
        await q.edit_message_text("✅ Акция создана.")
        return
    if step == "ad_video":
        st["video"] = None
        st["step"] = "ad_time"
        await q.edit_message_text("Введите время ежедневной рассылки в формате HH:MM по Варшаве, например 20:00:")
        return
    if step == "photo":
        d = data()
        pid = next_id(d["products"])
        d["products"].append({
            "id": pid,
            "name": st["name"],
            "category": st["category"],
            "description": st.get("description", ""),
            "photo": None,
            "active": True,
        })
        save(d)
        admin_state.pop(uid, None)
        await q.edit_message_text(f"✅ Товар добавлен без фото. ID: {pid}")
        return
    await q.answer("Сейчас здесь нечего пропускать.", show_alert=True)


async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    register_user(q.from_user)
    d = q.data or ""

    if d == "admin_skip":
        await handle_admin_skip_callback(q, context)
        return

    if d == "admin_panel":
        if is_admin(uid):
            await send_admin_panel(update, context, edit=True)
        return

    if d.startswith("l_"):
        lang = d[2:]
        if lang in LANGS:
            langs[uid] = lang
        await q.edit_message_text("VYBEX", reply_markup=main(uid))
        return

    if d == "age":
        await q.edit_message_text("VYBEX\n\n" + t(uid, "age"), reply_markup=main(uid))
        return

    if d == "catalog":
        dta = data()
        kb = [[InlineKeyboardButton(c, callback_data=f"c:{i}")] for i, c in enumerate(dta["categories"])]
        if not kb:
            kb = [[InlineKeyboardButton(t(uid, "manager"), callback_data="manager")]]
        kb += [
            [InlineKeyboardButton("🛒 Мой список", callback_data="cart")],
            [InlineKeyboardButton("🏷️ Акции", callback_data="promos")],
            [InlineKeyboardButton(t(uid, "manager"), callback_data="manager")],
            [InlineKeyboardButton(t(uid, "lang"), callback_data="langs")],
        ]
        await q.edit_message_text(t(uid, "cat"), reply_markup=InlineKeyboardMarkup(kb))
        return

    if d == "langs":
        await q.edit_message_text(
            t(uid, "lang"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇺🇦 Українська", callback_data="l_uk"), InlineKeyboardButton("🇵🇱 Polski", callback_data="l_pl")],
                [InlineKeyboardButton("🇬🇧 English", callback_data="l_en"), InlineKeyboardButton("🇷🇺 Русский", callback_data="l_ru")],
            ]),
        )
        return

    if d.startswith("c:"):
        try:
            index = int(d[2:])
            cats = data()["categories"]
            cat = cats[index]
        except (ValueError, IndexError):
            await q.answer("Категория не найдена", show_alert=True)
            return
        products = [p for p in data()["products"] if p.get("category") == cat and p.get("active", True)]
        if not products:
            await q.edit_message_text(cat + "\n\n" + t(uid, "info"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t(uid, "manager"), callback_data="manager")], [InlineKeyboardButton("◀️ Назад", callback_data="catalog")]]))
            return
        kb = [[InlineKeyboardButton(p["name"], callback_data=f"p:{p['id']}")] for p in products]
        kb.append([InlineKeyboardButton("◀️ Назад", callback_data="catalog")])
        await q.edit_message_text(cat, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d.startswith("p:"):
        p = product_by_id(d[2:])
        if not p:
            await q.answer("Товар не найден", show_alert=True)
            return
        text_value = f"📦 {p['name']}\n\n{p.get('description', '')}\n\n{t(uid, 'info')}"
        await q.edit_message_text(text_value, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить в список", callback_data=f"add:{p['id']}")],
            [InlineKeyboardButton("🛒 Мой список", callback_data="cart")],
            [InlineKeyboardButton(t(uid, "manager"), callback_data=f"m:{p['id']}")],
            [InlineKeyboardButton("◀️ Назад", callback_data=f"c:{data()['categories'].index(p['category'])}" if p.get('category') in data()['categories'] else "catalog")],
        ]))
        if p.get("photo"):
            try:
                await q.message.reply_photo(p["photo"], caption=p["name"])
            except Exception:
                log.exception("Could not send product photo")
        return

    if d.startswith("m:"):
        forms[uid] = {"step": "name", "product": d[2:]}
        await q.edit_message_text(t(uid, "name"))
        return

    if d == "manager":
        forms[uid] = {"step": "name", "product": ""}
        await q.edit_message_text(t(uid, "name"))
        return

    if d.startswith("add:"):
        pid = d[4:]
        if product_by_id(pid):
            carts.setdefault(uid, [])
            if pid not in carts[uid]:
                carts[uid].append(pid)
            await q.answer("Добавлено в список")
        return

    if d == "cart":
        items = carts.get(uid, [])
        products = data()["products"]
        names = [next((p["name"] for p in products if str(p.get("id")) == str(pid)), pid) for pid in items]
        if not names:
            await q.edit_message_text("🛒 Мой список пуст.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="catalog")]]))
            return
        text_value = "🛒 Мой список\n\n" + "\n".join(f"• {n}" for n in names) + "\n\nЭто список для согласования с менеджером."
        await q.edit_message_text(text_value, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Передать менеджеру", callback_data="cart_manager")],
            [InlineKeyboardButton("🗑 Очистить список", callback_data="cart_clear")],
            [InlineKeyboardButton("◀️ Назад", callback_data="catalog")],
        ]))
        return

    if d == "cart_clear":
        carts[uid] = []
        await q.edit_message_text("🗑 Список очищен.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Каталог", callback_data="catalog")]]))
        return

    if d == "cart_manager":
        items = carts.get(uid, [])
        if not items:
            await q.answer("Список пуст", show_alert=True)
            return
        forms[uid] = {"step": "name", "product": "CART", "cart": items[:]}
        await q.edit_message_text(t(uid, "name"))
        return

    if d == "promos":
        promos = [x for x in load_promos() if x.get("active", True)]
        if not promos:
            await q.edit_message_text("🏷️ Акций сейчас нет.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="catalog")]]))
            return
        await q.edit_message_text("🏷️ Акции")
        for pr in promos:
            txt = "🏷️ " + pr.get("title", "") + "\n\n" + pr.get("text", "")
            try:
                if pr.get("photo"):
                    await q.message.reply_photo(pr["photo"], caption=txt)
                elif pr.get("video"):
                    await q.message.reply_video(pr["video"], caption=txt)
                else:
                    await q.message.reply_text(txt)
            except Exception:
                await q.message.reply_text(txt)
        await q.message.reply_text("🏷️ Акции", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="catalog")]]))
        return

    if d.startswith("custom_back:"):
        target = d.split(":", 1)[1]
        if target == "root":
            await q.edit_message_text("VYBEX", reply_markup=main(uid))
        else:
            b = find_button(target)
            if b:
                await show_button(update, context, b, edit=True)
        return

    if d.startswith("custom:"):
        bid = d.split(":", 1)[1]
        b = find_button(bid)
        if b:
            await show_button(update, context, b, edit=True)
        return

    if not is_admin(uid):
        if d.startswith("d:") and uid in forms:
            f = forms[uid]
            f["district"] = d[2:]
            f["step"] = "interest"
            await q.edit_message_text(t(uid, "interest"))
        return

    # ---------------- ADMIN ----------------
    if d == "a_add":
        admin_state[uid] = {"step": "name"}
        await q.edit_message_text("➕ Добавление товара\n\nВведите название товара:")
        return

    if d == "a_list":
        products = data()["products"]
        if not products:
            await q.edit_message_text("📋 Товаров пока нет.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")]]))
            return
        rows = []
        for p in products:
            rows.append([InlineKeyboardButton(f"{p['id']}. {p['name']}", callback_data=f"a_product:{p['id']}")])
        rows.append([InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")])
        await q.edit_message_text("📋 Товары:", reply_markup=InlineKeyboardMarkup(rows))
        return

    if d == "a_delete":
        products = data()["products"]
        if not products:
            await q.edit_message_text("🗑 Удалять пока нечего.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")]]))
            return
        rows = [[InlineKeyboardButton(f"🗑 {p['id']}. {p['name']}", callback_data=f"a_delprod:{p['id']}")] for p in products]
        rows.append([InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")])
        await q.edit_message_text("Выберите товар для удаления:", reply_markup=InlineKeyboardMarkup(rows))
        return

    if d.startswith("a_product:"):
        pid = d.split(":", 1)[1]
        p = product_by_id(pid)
        if not p:
            await q.answer("Товар не найден", show_alert=True)
            return
        await q.edit_message_text(
            f"📦 {p['name']}\nID: {p['id']}\nКатегория: {p.get('category', '')}\nФото: {'есть' if p.get('photo') else 'нет'}\n\n{p.get('description', '')}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Удалить товар", callback_data=f"a_delprod:{pid}")],
                [InlineKeyboardButton("◀️ К списку товаров", callback_data="a_list")],
            ]),
        )
        return

    if d.startswith("a_delprod:"):
        pid = d.split(":", 1)[1]
        dta = data()
        before = len(dta["products"])
        dta["products"] = [p for p in dta["products"] if str(p.get("id")) != str(pid)]
        save(dta)
        await q.edit_message_text(
            "🗑 Товар удалён." if len(dta["products"]) < before else "❌ Товар не найден.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Товары", callback_data="a_list")], [InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")]]),
        )
        return

    if d.startswith("admincat:"):
        category = d.split(":", 1)[1]
        if category == "__new__":
            admin_state[uid]["step"] = "new_category"
            await q.edit_message_text("Введите название новой категории:")
            return
        if category not in data()["categories"]:
            await q.answer("Категория не найдена", show_alert=True)
            return
        admin_state[uid]["category"] = category
        admin_state[uid]["step"] = "description"
        await q.edit_message_text("Введите описание товара. Если описания нет — напишите /skip:")
        return

    if d == "b_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать кнопку", callback_data="b_add")],
            [InlineKeyboardButton("📋 Управление кнопками", callback_data="b_list")],
            [InlineKeyboardButton("🗑 Удалить кнопку", callback_data="b_delete")],
            [InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")],
        ])
        await q.edit_message_text("🧩 Конструктор кнопок\n\nСоздавайте кнопки, вложенные кнопки, текст, фото и видео.", reply_markup=kb)
        return

    if d == "b_add":
        admin_state[uid] = {"step": "button_label", "parent_id": None}
        await q.edit_message_text("Введите название главной кнопки:")
        return

    if d == "b_list":
        kb = all_button_rows()
        if not kb:
            await q.edit_message_text("📋 Пока нет кнопок.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="b_menu")]]))
            return
        kb.append([InlineKeyboardButton("◀️ Назад", callback_data="b_menu")])
        await q.edit_message_text("📋 Выберите кнопку для редактирования:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if d == "b_delete":
        if not load_buttons():
            await q.edit_message_text("🗑 Кнопок пока нет.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="b_menu")]]))
            return
        rows = [[InlineKeyboardButton(f"🗑 {b.get('label', 'Без названия')} (ID {b['id']})", callback_data=f"be_del:{b['id']}")] for b in load_buttons()]
        rows.append([InlineKeyboardButton("◀️ Назад", callback_data="b_menu")])
        await q.edit_message_text("Выберите кнопку для удаления:", reply_markup=InlineKeyboardMarkup(rows))
        return

    if d.startswith("be_open:"):
        bid = d.split(":", 1)[1]
        b = find_button(bid)
        if not b:
            await q.answer("Кнопка не найдена", show_alert=True)
            return
        await q.edit_message_text(
            f"🔧 {b['label']}\nID: {b['id']}\n\n"
            f"Текст: {'есть' if b.get('text') else 'нет'}\n"
            f"Картинка: {'есть' if b.get('photo') else 'нет'}\n"
            f"Видео: {'есть' if b.get('video') else 'нет'}\n"
            f"Вложенных кнопок: {len(child_buttons(b['id']))}",
            reply_markup=button_editor_kb(bid),
        )
        return

    if d.startswith("be_add:"):
        parent = d.split(":", 1)[1]
        if not find_button(parent):
            await q.answer("Родительская кнопка не найдена", show_alert=True)
            return
        admin_state[uid] = {"step": "button_label", "parent_id": parent}
        await q.edit_message_text("Введите название вложенной кнопки:")
        return

    if d.startswith("be_label:"):
        bid = d.split(":", 1)[1]
        admin_state[uid] = {"step": "button_label_edit", "button_id": bid}
        await q.edit_message_text("Введите новое название кнопки:")
        return

    if d.startswith("be_text:"):
        bid = d.split(":", 1)[1]
        admin_state[uid] = {"step": "button_text", "button_id": bid}
        await q.edit_message_text("Отправьте новый текст или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
        return

    if d.startswith("be_photo:"):
        bid = d.split(":", 1)[1]
        admin_state[uid] = {"step": "button_photo", "button_id": bid}
        await q.edit_message_text("Отправьте картинку или нажмите «Пропустить», чтобы удалить её:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
        return

    if d.startswith("be_video:"):
        bid = d.split(":", 1)[1]
        admin_state[uid] = {"step": "button_video", "button_id": bid}
        await q.edit_message_text("Отправьте видео для этой кнопки:")
        return

    if d.startswith("be_del:"):
        bid = d.split(":", 1)[1]
        bs = load_buttons()
        ids = {str(bid)}
        changed = True
        while changed:
            changed = False
            for b in bs:
                if str(b.get("parent_id")) in ids and str(b.get("id")) not in ids:
                    ids.add(str(b.get("id")))
                    changed = True
        new = [b for b in bs if str(b.get("id")) not in ids]
        save_buttons(new)
        await q.edit_message_text("🗑 Кнопка и её вложенные кнопки удалены.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К конструктору", callback_data="b_menu")]]))
        return

    # Promotions
    if d == "promo_menu":
        promos = load_promos()
        rows = [[InlineKeyboardButton("➕ Создать акцию", callback_data="promo_add")]]
        for pr in promos:
            rows.append([InlineKeyboardButton(("🟢 " if pr.get("active", True) else "🔴 ") + pr.get("title", ""), callback_data=f"promo_open:{pr['id']}")])
        rows.append([InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")])
        await q.edit_message_text("🏷️ Управление акциями", reply_markup=InlineKeyboardMarkup(rows))
        return

    if d == "promo_add":
        admin_state[uid] = {"step": "promo_title"}
        await q.edit_message_text("Введите название акции:")
        return

    if d.startswith("promo_open:"):
        pid = d.split(":", 1)[1]
        pr = next((x for x in load_promos() if str(x.get("id")) == str(pid)), None)
        if not pr:
            await q.answer("Акция не найдена", show_alert=True)
            return
        await q.edit_message_text(
            "🏷️ " + pr.get("title", "") + "\n\n" + pr.get("text", "") +
            f"\n\nСтатус: {'🟢 активна' if pr.get('active', True) else '🔴 выключена'}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Редактировать текст", callback_data=f"promo_edit:{pid}")],
                [InlineKeyboardButton("⏯ Вкл./выкл.", callback_data=f"promo_toggle:{pid}")],
                [InlineKeyboardButton("🗑 Удалить", callback_data=f"promo_del:{pid}")],
                [InlineKeyboardButton("◀️ Назад", callback_data="promo_menu")],
            ]),
        )
        return

    if d.startswith("promo_edit:"):
        pid = d.split(":", 1)[1]
        admin_state[uid] = {"step": "promo_edit", "promo_id": pid}
        await q.edit_message_text("Введите новый текст акции:")
        return

    if d.startswith("promo_toggle:"):
        pid = d.split(":", 1)[1]
        ps = load_promos()
        for pr in ps:
            if str(pr.get("id")) == str(pid):
                pr["active"] = not pr.get("active", True)
        save_promos(ps)
        await q.edit_message_text("Статус акции изменён.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="promo_menu")]]))
        return

    if d.startswith("promo_del:"):
        pid = d.split(":", 1)[1]
        save_promos([x for x in load_promos() if str(x.get("id")) != str(pid)])
        await q.edit_message_text("🗑 Акция удалена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="promo_menu")]]))
        return

    # Broadcast
    if d == "ad_menu":
        ad = load_broadcast()
        status = "🟢 включена" if ad.get("enabled") else "🔴 выключена"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать/изменить рассылку", callback_data="ad_create")],
            [InlineKeyboardButton("⏯ Вкл./выкл. ежедневную рассылку", callback_data="ad_toggle")],
            [InlineKeyboardButton("🗑 Удалить рассылку", callback_data="ad_delete")],
            [InlineKeyboardButton("◀️ Админ-панель", callback_data="admin_panel")],
        ])
        await q.edit_message_text(
            f"📣 Реклама / ежедневные объявления\n\nСтатус: {status}\nВремя: {ad.get('time', '20:00')} (Варшава)\nТекст: {'есть' if ad.get('text') else 'нет'}\nВидео: {'есть' if ad.get('video') else 'нет'}",
            reply_markup=kb,
        )
        return

    if d == "ad_create":
        admin_state[uid] = {"step": "ad_text"}
        await q.edit_message_text("Введите текст ежедневного сообщения:")
        return

    if d == "ad_video_yes":
        if uid in admin_state:
            admin_state[uid]["step"] = "ad_video"
        await q.edit_message_text("Отправьте видео. Если видео не нужно — /skip:")
        return

    if d == "ad_video_no":
        if uid in admin_state:
            admin_state[uid]["video"] = None
            admin_state[uid]["step"] = "ad_time"
        await q.edit_message_text("Введите время ежедневной рассылки в формате HH:MM по Варшаве, например 20:00:")
        return

    if d == "ad_toggle":
        ad = load_broadcast()
        ad["enabled"] = not ad.get("enabled", False)
        save_broadcast(ad)
        schedule_broadcast(context.application)
        await q.edit_message_text("📣 Ежедневная рассылка теперь " + ("🟢 включена" if ad["enabled"] else "🔴 выключена"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="ad_menu")]]))
        return

    if d == "ad_delete":
        save_broadcast({"enabled": False, "time": "20:00", "text": "", "video": None})
        schedule_broadcast(context.application)
        await q.edit_message_text("🗑 Ежедневная рассылка удалена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="ad_menu")]]))
        return

    if d == "admin_back":
        await send_admin_panel(update, context, edit=True)
        return

    if d.startswith("d:"):
        f = forms.get(uid)
        if not f:
            await q.answer("Заявка не найдена", show_alert=True)
            return
        f["district"] = d[2:]
        f["step"] = "interest"
        await q.edit_message_text(t(uid, "interest"))
        return


async def save_promo_from_state(uid):
    st = admin_state.get(uid, {})
    promos = load_promos()
    pid = next_id(promos)
    promos.append({
        "id": pid,
        "title": st.get("title", "Акция"),
        "text": st.get("text", ""),
        "photo": st.get("photo"),
        "video": st.get("video"),
        "active": True,
    })
    save_promos(promos)
    admin_state.pop(uid, None)


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message
    register_user(update.effective_user)

    if is_admin(uid) and uid in admin_state:
        st = admin_state[uid]
        step = st.get("step")
        dta = data()

        if step == "promo_title":
            st["title"] = msg.text.strip()
            st["step"] = "promo_text"
            await msg.reply_text("Введите текст акции. Если текста не нужно — /skip:")
            return
        if step == "promo_text":
            st["text"] = msg.text
            st["step"] = "promo_photo"
            await msg.reply_text("🖼️ Отправьте фото акции или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
            return
        if step == "promo_edit":
            ps = load_promos()
            pid = st.get("promo_id")
            for pr in ps:
                if str(pr.get("id")) == str(pid):
                    pr["text"] = msg.text
            save_promos(ps)
            admin_state.pop(uid, None)
            await msg.reply_text("✅ Акция обновлена.")
            return

        if step == "button_label":
            label = msg.text.strip()
            if not label:
                await msg.reply_text("Название не может быть пустым. Введите ещё раз:")
                return
            st["label"] = label
            st["step"] = "button_text_create"
            await msg.reply_text("📝 Введите текст для кнопки или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
            return
        if step == "button_text_create":
            st["text"] = msg.text
            st["step"] = "button_photo_create"
            await msg.reply_text("🖼️ Добавьте картинку или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
            return
        if step == "button_label_edit":
            bid = st.get("button_id")
            bs = load_buttons()
            found = False
            for b in bs:
                if str(b.get("id")) == str(bid):
                    b["label"] = msg.text.strip()
                    found = True
            save_buttons(bs)
            admin_state.pop(uid, None)
            await msg.reply_text("✅ Название кнопки изменено." if found else "❌ Кнопка не найдена.")
            return
        if step == "button_text":
            bid = st.get("button_id")
            bs = load_buttons()
            found = False
            for b in bs:
                if str(b.get("id")) == str(bid):
                    b["text"] = msg.text
                    found = True
            save_buttons(bs)
            admin_state.pop(uid, None)
            await msg.reply_text("✅ Текст сохранён." if found else "❌ Кнопка не найдена.")
            return
        if step in ("button_photo_create", "button_photo"):
            await msg.reply_text("Надішліть картинку або натисніть «Пропустити».")
            return
        if step == "button_video":
            await msg.reply_text("Надішліть саме відео або поверніться назад.")
            return
        if step == "button_delete":
            bid = msg.text.strip()
            await delete_button_by_id(uid, msg, bid)
            return

        if step == "name":
            st["name"] = msg.text.strip()
            st["step"] = "category"
            cats = dta["categories"]
            rows = [[InlineKeyboardButton(c, callback_data=f"admincat:{c}")] for c in cats]
            rows.append([InlineKeyboardButton("➕ Новая категория", callback_data="admincat:__new__")])
            await msg.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(rows))
            return
        if step == "new_category":
            category = msg.text.strip()
            if not category:
                await msg.reply_text("Название категории не может быть пустым:")
                return
            if category not in dta["categories"]:
                dta["categories"].append(category)
                save(dta)
            st["category"] = category
            st["step"] = "description"
            await msg.reply_text("Введите описание товара. Если описания нет — /skip:")
            return
        if step == "description":
            st["description"] = msg.text
            st["step"] = "photo"
            await msg.reply_text("Отправьте фото товара или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
            return
        if step == "delete":
            before = len(dta["products"])
            dta["products"] = [p for p in dta["products"] if str(p.get("id")) != msg.text.strip()]
            save(dta)
            admin_state.pop(uid, None)
            await msg.reply_text("Удалено." if len(dta["products"]) < before else "ID не найден.")
            return
        if step == "ad_text":
            st["text"] = msg.text
            st["step"] = "ad_video_choice"
            await msg.reply_text("Добавить видео к ежедневному сообщению?", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎥 Да", callback_data="ad_video_yes")],
                [InlineKeyboardButton("Без видео", callback_data="ad_video_no")],
            ]))
            return
        if step == "ad_time":
            raw = msg.text.strip()
            try:
                hh, mm = map(int, raw.split(":"))
                if not (0 <= hh < 24 and 0 <= mm < 60):
                    raise ValueError
            except Exception:
                await msg.reply_text("Неверный формат. Введите HH:MM, например 20:00:")
                return
            ad = load_broadcast()
            ad.update({"enabled": True, "time": f"{hh:02d}:{mm:02d}", "text": st.get("text", ""), "video": st.get("video")})
            save_broadcast(ad)
            admin_state.pop(uid, None)
            schedule_broadcast(context.application)
            await msg.reply_text(f"✅ Ежедневная рассылка сохранена и включена на {ad['time']} по Варшаве.")
            return

    f = forms.get(uid)
    if not f:
        return
    if f["step"] == "name":
        f["name"] = msg.text
        f["step"] = "phone"
        await msg.reply_text(t(uid, "phone"))
        return
    if f["step"] == "phone":
        f["phone"] = msg.text
        f["step"] = "district"
        await msg.reply_text(t(uid, "district"), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Targówek", callback_data="d:Targówek")],
            [InlineKeyboardButton("Bemowo", callback_data="d:Bemowo")],
            [InlineKeyboardButton("Wola", callback_data="d:Wola")],
        ]))
        return
    if f["step"] == "interest":
        f["interest"] = msg.text
        await send_lead(update, context, f)


async def delete_button_by_id(uid, message, bid):
    bs = load_buttons()
    ids = {str(bid)}
    changed = True
    while changed:
        changed = False
        for b in bs:
            if str(b.get("parent_id")) in ids and str(b.get("id")) not in ids:
                ids.add(str(b.get("id")))
                changed = True
    new = [b for b in bs if str(b.get("id")) not in ids]
    save_buttons(new)
    admin_state.pop(uid, None)
    await message.reply_text("🗑 Кнопка и вложенные кнопки удалены." if len(new) < len(bs) else "❌ ID не найден.")


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid) or uid not in admin_state:
        return
    st = admin_state[uid]
    file_id = update.message.photo[-1].file_id

    if st.get("step") == "button_photo_create":
        st["photo"] = file_id
        await finish_button(uid, update.message)
        return
    if st.get("step") == "button_photo":
        bid = st.get("button_id")
        bs = load_buttons()
        found = False
        for b in bs:
            if str(b.get("id")) == str(bid):
                b["photo"] = file_id
                found = True
        save_buttons(bs)
        admin_state.pop(uid, None)
        await update.message.reply_text("✅ Картинка кнопки сохранена." if found else "❌ Кнопка не найдена.")
        return
    if st.get("step") == "promo_photo":
        st["photo"] = file_id
        st["step"] = "promo_video"
        await update.message.reply_text("🎥 Отправьте видео акции или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
        return
    if st.get("step") == "photo":
        dta = data()
        pid = next_id(dta["products"])
        dta["products"].append({
            "id": pid,
            "name": st["name"],
            "category": st["category"],
            "description": st.get("description", ""),
            "photo": file_id,
            "active": True,
        })
        save(dta)
        admin_state.pop(uid, None)
        await update.message.reply_text(f"✅ Товар добавлен. ID: {pid}")


async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid) or uid not in admin_state:
        return
    st = admin_state[uid]
    file_id = update.message.video.file_id

    if st.get("step") == "button_video":
        bid = st.get("button_id")
        bs = load_buttons()
        found = False
        for b in bs:
            if str(b.get("id")) == str(bid):
                b["video"] = file_id
                found = True
        save_buttons(bs)
        admin_state.pop(uid, None)
        await update.message.reply_text("✅ Видео кнопки сохранено." if found else "❌ Кнопка не найдена.")
        return
    if st.get("step") == "promo_video":
        st["video"] = file_id
        await save_promo_from_state(uid)
        await update.message.reply_text("✅ Акция создана.")
        return
    if st.get("step") == "ad_video":
        st["video"] = file_id
        st["step"] = "ad_time"
        await update.message.reply_text("Введите время ежедневной рассылки в формате HH:MM по Варшаве, например 20:00:")


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    st = admin_state.get(uid, {})
    step = st.get("step")
    fake_message = update.message

    if step == "button_text_create":
        st["text"] = ""
        st["step"] = "button_photo_create"
        await fake_message.reply_text("🖼️ Добавьте картинку или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
        return
    if step == "button_photo_create":
        st["photo"] = None
        await finish_button(uid, fake_message)
        return
    if step == "button_text":
        bid = st.get("button_id")
        bs = load_buttons()
        for b in bs:
            if str(b.get("id")) == str(bid):
                b["text"] = ""
        save_buttons(bs)
        admin_state.pop(uid, None)
        await fake_message.reply_text("✅ Текст кнопки очищен.")
        return
    if step == "button_photo":
        bid = st.get("button_id")
        bs = load_buttons()
        for b in bs:
            if str(b.get("id")) == str(bid):
                b["photo"] = None
        save_buttons(bs)
        admin_state.pop(uid, None)
        await fake_message.reply_text("✅ Картинка кнопки удалена.")
        return
    if step == "photo":
        dta = data()
        pid = next_id(dta["products"])
        dta["products"].append({
            "id": pid,
            "name": st["name"],
            "category": st["category"],
            "description": st.get("description", ""),
            "photo": None,
            "active": True,
        })
        save(dta)
        admin_state.pop(uid, None)
        await fake_message.reply_text(f"✅ Товар добавлен без фото. ID: {pid}")
        return
    if step == "promo_text":
        st["text"] = ""
        st["step"] = "promo_photo"
        await fake_message.reply_text("🖼️ Добавьте фото акции или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
        return
    if step == "promo_photo":
        st["photo"] = None
        st["step"] = "promo_video"
        await fake_message.reply_text("🎥 Добавьте видео акции или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
        return
    if step == "promo_video":
        st["video"] = None
        await save_promo_from_state(uid)
        await fake_message.reply_text("✅ Акция создана.")
        return
    if step == "ad_video":
        st["video"] = None
        st["step"] = "ad_time"
        await fake_message.reply_text("Введите время ежедневной рассылки в формате HH:MM по Варшаве, например 20:00:")
        return
    if step == "description":
        st["description"] = ""
        st["step"] = "photo"
        await fake_message.reply_text("Отправьте фото товара или нажмите «Пропустить»:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Пропустить", callback_data="admin_skip")]]))
        return


async def send_lead(update, context, f):
    uid = update.effective_user.id
    manager_id = manager_chat_id()
    if not manager_id:
        await update.message.reply_text("Менеджер ещё не подключён. Пусть @manager_VYBEX один раз откроет бота и нажмёт /start.")
        forms.pop(uid, None)
        return

    if f.get("product") == "CART":
        names = [next((x["name"] for x in data()["products"] if str(x.get("id")) == str(pid)), pid) for pid in f.get("cart", [])]
        item_text = "\n".join("• " + n for n in names)
    else:
        p = product_by_id(f.get("product"))
        item_text = p["name"] if p else f.get("interest", "")

    text_value = (
        "🔔 НОВАЯ ЗАЯВКА НА ЛИЧНУЮ ВСТРЕЧУ\n\n"
        f"Имя: {f.get('name', '')}\n"
        f"Телефон: {f.get('phone', '')}\n"
        f"Район: {f.get('district', '')}\n"
        f"Товар(и): {item_text}\n"
        f"Telegram: @{update.effective_user.username or 'нет'}\n"
        f"ID: {uid}"
    )
    await context.bot.send_message(chat_id=manager_id, text=text_value)
    await update.message.reply_text(t(uid, "sent"))
    forms.pop(uid, None)
    carts[uid] = []


def main(uid):
    rows = [
        [InlineKeyboardButton(LANGS[langs.get(uid, "ru")]["cat"], callback_data="catalog")],
        [InlineKeyboardButton("🛒 Мой список", callback_data="cart"), InlineKeyboardButton("🏷️ Акции", callback_data="promos")],
        [InlineKeyboardButton(LANGS[langs.get(uid, "ru")]["manager"], callback_data="manager")],
        [InlineKeyboardButton(LANGS[langs.get(uid, "ru")]["lang"], callback_data="langs")],
    ]
    for b in root_buttons():
        rows.append([InlineKeyboardButton(b["label"], callback_data=f"custom:{b['id']}")])
    if str(uid) == ADMIN_ID:
        rows.append([InlineKeyboardButton("⚙️ Админ", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    ad = load_broadcast()
    if not ad.get("enabled") or not ad.get("text"):
        return
    for user in load_users().values():
        if user.get("role") in ("admin", "manager"):
            continue
        cid = user.get("chat_id")
        if not cid:
            continue
        try:
            await context.bot.send_message(chat_id=cid, text=ad["text"])
            if ad.get("video"):
                await context.bot.send_video(chat_id=cid, video=ad["video"])
        except Exception as exc:
            log.warning("Broadcast to %s failed: %s", cid, exc)


def schedule_broadcast(application):
    jq = application.job_queue
    if jq is None:
        log.warning("JobQueue is unavailable")
        return
    for job in jq.get_jobs_by_name("vybex_daily_broadcast"):
        job.schedule_removal()
    ad = load_broadcast()
    if not ad.get("enabled"):
        return
    try:
        hh, mm = map(int, ad.get("time", "20:00").split(":"))
        jq.run_daily(daily_broadcast, time=dt_time(hh, mm, tzinfo=TZ), name="vybex_daily_broadcast")
    except Exception:
        log.exception("Broadcast scheduling error")


async def post_init(application):
    schedule_broadcast(application)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled bot error", exc_info=context.error)


if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

app = Application.builder().token(TOKEN).post_init(post_init).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("skip", skip))
app.add_handler(CallbackQueryHandler(cb))
app.add_handler(MessageHandler(filters.PHOTO, photo))
app.add_handler(MessageHandler(filters.VIDEO, video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
app.add_error_handler(error_handler)

app.run_polling()

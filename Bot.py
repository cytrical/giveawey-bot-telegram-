import telebot
from telebot import types
import time, json, os, threading

TOKEN = "AQUI_TU_TOKEN"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "giveaways.json"

# ==================== Helpers ====================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(giveaways, f, indent=2)

giveaways = load_data()

def delete_later(chat_id, msg_id, delay=10):
    def task():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    threading.Thread(target=task, daemon=True).start()

# ==================== /newgift ====================

@bot.message_handler(commands=["newgift"])
def new_gift(message):
    if message.chat.type not in ["supergroup", "group"]:
        return bot.reply_to(message, "⚠️ Usa este comando en un grupo.")

    member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        m = bot.reply_to(message, "❌ No eres admin.")
        delete_later(message.chat.id, m.message_id)
        return

    gid = str(message.chat.id) + "_" + str(int(time.time()))
    giveaways[gid] = {
        "group": message.chat.id,
        "creator": message.from_user.id,
        "title": None,
        "desc": None,
        "image": None,
        "participants": [],
        "active": False,
        "msg_id": None,
        "end_time": None,
        "member_goal": None,
        "early_start": None,
        "setup_msg": None,
        "creator_msg": message.message_id,
        "published": False
    }
    save_data()

    markup = types.InlineKeyboardMarkup()
    bot_username = bot.get_me().username
    markup.add(types.InlineKeyboardButton("⚙️ Configurar sorteo", url=f"https://t.me/{bot_username}?start={gid}"))
    sent = bot.send_message(message.chat.id, "👉 Configura el sorteo en privado:", reply_markup=markup)
    giveaways[gid]["setup_msg"] = sent.message_id
    save_data()

# ==================== /start con parámetro ====================

@bot.message_handler(commands=["start"])
def start_cmd(message):
    args = message.text.split()
    if len(args) > 1:
        gid = args[1]
        g = giveaways.get(gid)
        if not g:
            return bot.send_message(message.chat.id, "❌ Sorteo no encontrado.")
        if message.from_user.id != g["creator"]:
            return bot.send_message(message.chat.id, "❌ No eres el creador de este sorteo.")
        msg = bot.send_message(message.chat.id, "✏️ Ingresa el TÍTULO del sorteo:")
        bot.register_next_step_handler(msg, set_title, gid)
    else:
        bot.send_message(message.chat.id, "Hola 👋 Usa /newgift en un grupo para crear un sorteo.")

# ==================== setup en privado ====================

def set_title(message, gid):
    giveaways[gid]["title"] = message.text
    save_data()
    msg = bot.send_message(message.chat.id, "📝 Ingresa la DESCRIPCIÓN (puedes usar HTML):")
    bot.register_next_step_handler(msg, set_desc, gid)

def set_desc(message, gid):
    giveaways[gid]["desc"] = message.text
    save_data()
    msg = bot.send_message(message.chat.id, "📷 Envía una IMAGEN o escribe 'no' para continuar sin imagen:")
    bot.register_next_step_handler(msg, set_image, gid)

def set_image(message, gid):
    if message.content_type == "photo":
        giveaways[gid]["image"] = message.photo[-1].file_id
    elif message.text.lower() == "no":
        giveaways[gid]["image"] = None
    else:
        msg = bot.send_message(message.chat.id, "❌ Envía una foto válida o escribe 'no'.")
        return bot.register_next_step_handler(msg, set_image, gid)
    save_data()
    msg = bot.send_message(message.chat.id, "⏱️ Ingresa la duración en minutos:")
    bot.register_next_step_handler(msg, set_time, gid)

def set_time(message, gid):
    try:
        minutes = int(message.text)
        giveaways[gid]["end_time"] = minutes * 60  # guardamos duración, no inicio aún
    except:
        return bot.send_message(message.chat.id, "❌ Ingresa un número válido en minutos.")
    save_data()
    msg = bot.send_message(message.chat.id, "👥 Ingresa la META de miembros para iniciar el sorteo (ejemplo: 500):")
    bot.register_next_step_handler(msg, set_goal, gid)

def set_goal(message, gid):
    try:
        goal = int(message.text)
        giveaways[gid]["member_goal"] = goal
    except:
        return bot.send_message(message.chat.id, "❌ Ingresa un número válido.")
    save_data()
    msg = bot.send_message(message.chat.id, "⚡ ¿Quieres inicio anticipado si faltan pocos? (sí/no)")
    bot.register_next_step_handler(msg, set_early, gid)

def set_early(message, gid):
    txt = message.text.lower()
    if txt in ["si", "sí", "yes"]:
        msg = bot.send_message(message.chat.id, "🔢 Ingresa cuántos menos (entre 5 y 25):")
        return bot.register_next_step_handler(msg, set_early_num, gid)
    else:
        giveaways[gid]["early_start"] = None
        save_data()
        return preview(message.chat.id, gid)

def set_early_num(message, gid):
    try:
        n = int(message.text)
        if 5 <= n <= 25:
            giveaways[gid]["early_start"] = n
        else:
            return bot.send_message(message.chat.id, "❌ Debe estar entre 5 y 25.")
    except:
        return bot.send_message(message.chat.id, "❌ Ingresa un número válido.")
    save_data()
    preview(message.chat.id, gid)

# ==================== Preview ====================

def preview(chat_id, gid):
    g = giveaways[gid]
    text = f"🎉 <b>{g['title']}</b>\n\n{g['desc']}\n\n⏱️ Duración: {g['end_time']//60} min\n👥 Meta: {g['member_goal']}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🖼️ Imagen arriba", callback_data=f"prevup_{gid}"))
    markup.add(types.InlineKeyboardButton("🖼️ Imagen abajo", callback_data=f"prevdown_{gid}"))
    markup.add(types.InlineKeyboardButton("📤 Enviar al grupo", callback_data=f"publish_{gid}"))
    markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel_{gid}"))
    sent = bot.send_message(chat_id, "📌 Vista previa:", reply_markup=markup)
    giveaways[gid]["preview_msg"] = sent.message_id
    save_data()
    if g["image"]:
        bot.send_photo(chat_id, g["image"], caption=text, parse_mode="HTML")
    else:
        bot.send_message(chat_id, text, parse_mode="HTML")

# ==================== Preview buttons ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith(("prevup_", "prevdown_")))
def prev_image(call):
    gid = call.data.split("_", 1)[1]
    g = giveaways[gid]
    text = f"🎉 <b>{g['title']}</b>\n\n{g['desc']}\n\n⏱️ Duración: {g['end_time']//60} min\n👥 Meta: {g['member_goal']}"
    if call.data.startswith("prevup_") and g["image"]:
        bot.send_photo(call.from_user.id, g["image"], caption=text, parse_mode="HTML")
    elif call.data.startswith("prevdown_") and g["image"]:
        bot.send_message(call.from_user.id, text, parse_mode="HTML")
        bot.send_photo(call.from_user.id, g["image"])
    bot.answer_callback_query(call.id, "✅ Vista previa enviada.")

# ==================== Publicar ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_"))
def publish(call):
    gid = call.data.split("_", 1)[1]
    g = giveaways[gid]
    g["active"] = True
    g["published"] = True
    g["start_time"] = None  # solo se fija cuando alcance meta
    save_data()
    update_message(gid)

    bot.send_message(call.from_user.id, "✅ Sorteo publicado en el grupo.")

    try: delete_later(g["group"], g["creator_msg"], 3)
    except: pass
    try: delete_later(g["group"], g["setup_msg"], 3)
    except: pass
    try: delete_later(call.from_user.id, g["preview_msg"], 3)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel(call):
    gid = call.data.split("_", 1)[1]
    giveaways.pop(gid, None)
    save_data()
    bot.send_message(call.from_user.id, "❌ Sorteo cancelado.")

# ==================== Actualizar mensaje ====================

def update_message(gid):
    g = giveaways.get(gid)
    if not g or not g["published"]: return

    # contar miembros reales del grupo
    try:
        members_count = bot.get_chat_members_count(g["group"])
    except:
        members_count = 0

    goal = g["member_goal"]
    early = g["early_start"] or 0
    joined = len(g["participants"])
    percent = int((joined/goal)*100) if goal else 0

    text = ""
    markup = types.InlineKeyboardMarkup()

    # Caso 1: Muy lejos de la meta
    if members_count < goal - early:
        text = (
            f"🚫 UN SORTEO EMPEZARÁ CUANDO SEAMOS {goal} PERSONAS\n"
            f"⏳ Esperando más participantes...\n\n"
            f"Somos {members_count}/{goal}"
        )
        markup.add(types.InlineKeyboardButton("⏳ Aún no disponible", callback_data="wait"))

    # Caso 2: Inicio anticipado (pero aún no en meta)
    elif members_count < goal:
        text = (
            f"🎉 <b>{g['title']}</b>\n\n"
            f"{g['desc']}\n\n"
            f"👥 {members_count}/{goal}\n"
            f"⏳ Esperando más participantes..."
        )
        markup.add(types.InlineKeyboardButton("⏳ Aún no disponible", callback_data="wait"))

    # Caso 3: Ya alcanzamos meta → empieza de verdad
    else:
        if not g.get("start_time"):
            g["start_time"] = time.time()
            g["end_real"] = g["start_time"] + g["end_time"]
        remain = max(0, int(g["end_real"] - time.time()))
        mins, secs = divmod(remain, 60)

        text = (
            f"🎉 <b>{g['title']}</b>\n\n"
            f"{g['desc']}\n\n"
            f"⏱️ Termina a las {time.strftime('%H:%M:%S', time.localtime(g['end_real']))}\n"
            f"⏳ Faltan {mins:02d}:{secs:02d}\n"
            f"👥 {joined}/{goal} ({percent}%)\n"
            f"Pulsa en Unirse para participar."
        )
        markup.add(types.InlineKeyboardButton(f"🎁 Unirse ({joined})", callback_data=f"join_{gid}"))

    try:
        if g["msg_id"]:
            if g["image"]:
                bot.edit_message_caption(
                    caption=text,
                    chat_id=g["group"],
                    message_id=g["msg_id"],
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            else:
                bot.edit_message_text(
                    text,
                    g["group"], g["msg_id"],
                    reply_markup=markup,
                    parse_mode="HTML"
                )
        else:
            if g["image"]:
                sent = bot.send_photo(g["group"], g["image"], caption=text, reply_markup=markup, parse_mode="HTML")
            else:
                sent = bot.send_message(g["group"], text, reply_markup=markup, parse_mode="HTML")
            g["msg_id"] = sent.message_id
    except:
        pass
    save_data()

# ==================== Unirse ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("join_"))
def join(call):
    gid = call.data.split("_", 1)[1]
    g = giveaways[gid]
    if not g["active"]:
        return bot.answer_callback_query(call.id, "⏳ El sorteo no está activo.")
    if call.from_user.id in g["participants"]:
        return bot.answer_callback_query(call.id, "Ya estás participando.")
    g["participants"].append(call.from_user.id)
    save_data()
    update_message(gid)
    bot.answer_callback_query(call.id, "✅ Te uniste al sorteo.")

# ==================== End ====================

@bot.message_handler(commands=["end"])
def end_cmd(message):
    for gid, g in list(giveaways.items()):
        if g["creator"] == message.from_user.id and g["active"]:
            finish_giveaway(gid)

def finish_giveaway(gid):
    g = giveaways[gid]
    g["active"] = False
    if g["participants"]:
        winner_id = g["participants"][0]
        bot.send_message(g["group"], f"🎉 El ganador es: <a href='tg://user?id={winner_id}'>Ganador</a> 🎉", parse_mode="HTML")
    else:
        bot.send_message(g["group"], "❌ Nadie participó en el sorteo.")
    save_data()

# ==================== Loop ====================

def check_giveaways():
    while True:
        now = time.time()
        for gid, g in list(giveaways.items()):
            if g["active"] and g.get("start_time") and now >= g["end_real"]:
                finish_giveaway(gid)
            elif g["active"]:
                update_message(gid)
        time.sleep(30)

threading.Thread(target=check_giveaways, daemon=True).start()

print("🤖 Bot corriendo...")
bot.infinity_polling()

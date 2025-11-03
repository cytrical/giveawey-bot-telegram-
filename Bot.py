import telebot
from telebot import types
import time, json, os, threading, random
from datetime import datetime

# ---------------- Configuration ----------------
TOKEN = "8341113292:AAGwYYmTWNcISpX0ZyhrCS3Z5eqJxaoSgsQ"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "giveaways.json"   # sorteos y estado
USERS_FILE = "users.json"      # puntos/estadísticas
BACKUP_DIR = "backups"         # backups automáticos

# ---------------- Helpers ----------------

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

giveaways = load_json(DATA_FILE)
users = load_json(USERS_FILE)

def save_data():
    save_json(DATA_FILE, giveaways)

def save_users():
    save_json(USERS_FILE, users)

def ensure_user(u):
    su = str(u)
    if su not in users:
        users[su] = {"points": 0, "wins": 0, "joined": 0}
        save_users()
    return users[su]

def backup_data():
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        save_json(os.path.join(BACKUP_DIR, f"giveaways_{ts}.json"), giveaways)
        save_json(os.path.join(BACKUP_DIR, f"users_{ts}.json"), users)
    except Exception as e:
        print("Backup error:", e)

def delete_later(chat_id, msg_id, delay=10):
    def task():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    threading.Thread(target=task, daemon=True).start()

# ---------------- Utility display ----------------

def format_duration(seconds):
    if not seconds or seconds <= 0:
        return "0s"
    parts = []
    weeks, seconds = divmod(int(seconds), 604800)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if weeks:
        parts.append(f"{weeks}w")
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts)

def parse_duration(text):
    if not isinstance(text, str) or not text.strip():
        return None
    text = text.strip().lower()
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    if text[-1] in units:
        try:
            value = float(text[:-1])
            return int(value * units[text[-1]])
        except:
            return None
    else:
        try:
            # If no unit, assume minutes (as original script seemed to expect)
            return int(float(text) * 60)
        except:
            return None

def user_display(uid):
    try:
        u = bot.get_chat(uid)
        return f"@{u.username}" if getattr(u, "username", None) else (getattr(u, "first_name", None) or str(uid))
    except:
        return str(uid)

# ---------------- Levels ----------------

LEVELS = [
    (0, "Novato 🪶"),
    (51, "Afortunado 💫"),
    (151, "Leyenda 👑")
]

def get_level(points):
    level = LEVELS[0][1]
    for threshold, name in LEVELS:
        if points >= threshold:
            level = name
    return level

# ---------------- Core commands ----------------

@bot.message_handler(commands=["help"])
def help_cmd(message):
    text = (
        "📘 *Comandos disponibles*\n\n"
        "👥 *Usuarios:*\n"
        "/help - Muestra este mensaje\n"
        "/stats - Ver tus puntos y victorias\n"
        "/top - Ver ranking por puntos\n\n"
        "🔧 *Administradores (en grupos):*\n"
        "/newgift - Crear un nuevo sorteo (usa en el grupo)\n"
        "/end - Finalizar manualmente un sorteo que creaste\n\n"
        "Si necesitas más ayuda, contacta al creador del bot."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    u = ensure_user(message.from_user.id)
    text = (
        f"📊 *Tus estadísticas*\n\n"
        f"• Puntos: {u.get('points',0)}\n"
        f"• Victorias: {u.get('wins',0)}\n"
        f"• Participaciones totales: {u.get('joined',0)}\n"
        f"• Nivel: {get_level(u.get('points',0))}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["top"])
def top_cmd(message):
    top = sorted(users.items(), key=lambda i: i[1].get("points",0), reverse=True)[:10]
    lines = ["🏆 Top usuarios por puntos:"]
    for uid, data in top:
        lines.append(f"{user_display(int(uid))}: {data.get('points',0)} pts • {data.get('wins',0)} wins")
    bot.send_message(message.chat.id, "\n".join(lines))

# ---------------- /newgift ----------------

@bot.message_handler(commands=["newgift"])
def new_gift(message):
    if message.chat.type not in ["supergroup", "group"]:
        return bot.reply_to(message, "⚠️ Este comando sólo funciona en grupos o supergrupos.")

    member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        m = bot.reply_to(message, "❌ Necesitas ser administrador para crear sorteos.")
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
        "published": False,
        "num_winners": 1,
        "reminders_sent": []
    }
    save_data()

    markup = types.InlineKeyboardMarkup()
    bot_username = bot.get_me().username
    markup.add(types.InlineKeyboardButton("⚙️ Configurar sorteo", url=f"https://t.me/{bot_username}?start={gid}"))
    sent = bot.send_message(message.chat.id, "👉 Configura el sorteo en privado:", reply_markup=markup)
    giveaways[gid]["setup_msg"] = sent.message_id
    save_data()

# ---------------- Setup in private ----------------

@bot.message_handler(commands=["start"])
def start_cmd(message):
    args = message.text.split()
    if len(args) > 1:
        gid = args[1]
        g = giveaways.get(gid)
        if not g:
            return bot.send_message(message.chat.id, "❌ Sorteo no encontrado.")
        if message.from_user.id != g["creator"]:
            return bot.send_message(message.chat.id, "❌ Solo el creador puede configurar este sorteo.")
        msg = bot.send_message(message.chat.id, "✏️ Ingresa el TÍTULO del sorteo:")
        bot.register_next_step_handler(msg, set_title, gid)
    else:
        bot.send_message(message.chat.id, "Hola 👋 Usa /newgift en el grupo para iniciar la creación del sorteo.")

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
    elif message.text and message.text.lower() == "no":
        giveaways[gid]["image"] = None
    else:
        msg = bot.send_message(message.chat.id, "❌ Envía una foto válida o escribe 'no'.")
        return bot.register_next_step_handler(msg, set_image, gid)
    save_data()
    msg = bot.send_message(message.chat.id, "⏱️ Ingresa la DURACIÓN (ej: 30s, 5m, 1h, 2d, 1w):")
    bot.register_next_step_handler(msg, set_time, gid)

def set_time(message, gid):
    duration = parse_duration(message.text)
    if duration is None or duration < 1:
        return bot.send_message(message.chat.id, "❌ Duración inválida. Ejemplos válidos: 30s, 5m, 1h, 2d, 1w.")

    giveaways[gid]["end_time"] = duration
    save_data()
    msg = bot.send_message(message.chat.id, "🏆 ¿Cuántos ganadores deseas? (escribe un número, por defecto 1):")
    bot.register_next_step_handler(msg, set_num_winners, gid)

def set_num_winners(message, gid):
    try:
        n = int(message.text)
        giveaways[gid]["num_winners"] = max(1, n)
    except:
        giveaways[gid]["num_winners"] = 1
    save_data()
    msg = bot.send_message(message.chat.id, "👥 Ingresa la META de miembros para iniciar el sorteo (ejemplo: 500):")
    bot.register_next_step_handler(msg, set_goal, gid)

def set_goal(message, gid):
    try:
        goal = int(message.text)
        giveaways[gid]["member_goal"] = goal
    except:
        return bot.send_message(message.chat.id, "❌ Ingresa un número válido para la meta de miembros.")
    save_data()
    msg = bot.send_message(message.chat.id, "⚡ ¿Quieres inicio anticipado si faltan pocos? (sí/no)")
    bot.register_next_step_handler(msg, set_early, gid)

def set_early(message, gid):
    txt = (message.text or "").lower()
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

# ---------------- Preview ----------------

def preview(chat_id, gid):
    g = giveaways[gid]
    duration_display = format_duration(g.get("end_time", 0))
    text = (f"🍷✨ <b>{g.get('title','Sorteo')}</b>\n\n"
            f"{g.get('desc','')}\n\n"
            f"⏱️ Duración: {duration_display}\n"
            f"👥 Meta: {g.get('member_goal')}\n"
            f"👑 Ganadores: {g.get('num_winners',1)}")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🖼️ Imagen arriba", callback_data=f"prevup_{gid}"))
    markup.add(types.InlineKeyboardButton("🖼️ Imagen abajo", callback_data=f"prevdown_{gid}"))
    # Admin panel in preview (only creator will see control via private chat)
    markup.add(types.InlineKeyboardButton("📤 Enviar al grupo", callback_data=f"publish_{gid}"))
    markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel_{gid}"))
    sent = bot.send_message(chat_id, "📌 Vista previa:", reply_markup=markup)
    giveaways[gid]["preview_msg"] = sent.message_id
    save_data()
    if g.get("image"):
        bot.send_photo(chat_id, g["image"], caption=text, parse_mode="HTML")
    else:
        bot.send_message(chat_id, text, parse_mode="HTML")

# ---------------- Preview buttons ----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith(("prevup_", "prevdown_")))
def prev_image(call):
    gid = call.data.split("_", 1)[1]
    g = giveaways.get(gid)
    duration_display = format_duration(g.get("end_time", 0))
    text = (f"🍷✨ <b>{g.get('title','Sorteo')}</b>\n\n"
            f"{g.get('desc','')}\n\n"
            f"⏱️ Duración: {duration_display}\n"
            f"👥 Meta: {g.get('member_goal')}\n"
            f"👑 Ganadores: {g.get('num_winners',1)}")
    if call.data.startswith("prevup_") and g.get("image"):
        bot.send_photo(call.from_user.id, g["image"], caption=text, parse_mode="HTML")
    elif call.data.startswith("prevdown_") and g.get("image"):
        bot.send_message(call.from_user.id, text, parse_mode="HTML")
        bot.send_photo(call.from_user.id, g["image"])
    bot.answer_callback_query(call.id, "✅ Vista previa enviada.")

# ---------------- Publicar ----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_"))
def publish(call):
    gid = call.data.split("_", 1)[1]
    g = giveaways.get(gid)
    # only creator can publish
    if call.from_user.id != g.get("creator"):
        return bot.answer_callback_query(call.id, "❌ Solo el creador puede publicar este sorteo.")

    g["active"] = True
    g["published"] = True
    g["start_time"] = time.time()  # marca inicio real del sorteo
    g["end_real"] = g["start_time"] + g.get("end_time", 0)  # calcula cuándo termina
    g["reminders_sent"] = []
    g["last_remain"] = None
    g["last_participants"] = None
    save_data()
    # post the giveaway message in the group
    update_message(gid)
    bot.send_message(call.from_user.id, "✅ Sorteo publicado en el grupo. Puedes gestionarlo desde el mensaje del sorteo.")

    try: delete_later(g["group"], g["creator_msg"], 3)
    except: pass
    try: delete_later(g["group"], g["setup_msg"], 3)
    except: pass
    try: delete_later(call.from_user.id, g.get("preview_msg"), 3)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel(call):
    gid = call.data.split("_", 1)[1]
    g = giveaways.get(gid)
    if call.from_user.id != g.get("creator"):
        return bot.answer_callback_query(call.id, "❌ Solo el creador puede cancelar.")
    giveaways.pop(gid, None)
    save_data()
    bot.send_message(call.from_user.id, "❌ Sorteo cancelado.")

# ---------------- Update message (with admin panel) ----------------

def build_markup_admin(gid, g):
    markup = types.InlineKeyboardMarkup()
    # join button visible to all
    markup.add(types.InlineKeyboardButton(f"🎁 Unirse ({len(g.get('participants',[]))})", callback_data=f"join_{gid}"))
    # admin controls (only visible if pressed by admin via callback handling check)
    # We'll include buttons that trigger callbacks; callback handlers will check permissions.
    row = [
        types.InlineKeyboardButton("🛑 Finalizar", callback_data=f"force_end_{gid}"),
        types.InlineKeyboardButton("🔄 Reiniciar", callback_data=f"force_restart_{gid}"),
        types.InlineKeyboardButton("📊 Estado", callback_data=f"view_status_{gid}")
    ]
    markup.row(*row)
    return markup

def update_message(gid):
    g = giveaways.get(gid)
    if not g or not g.get("published"):
        return

    try:
        # telebot older/newer method differences handled
        try:
            members_count = bot.get_chat_members_count(g["group"])
        except:
            members_count = bot.get_chat_member_count(g["group"])
    except:
        members_count = 0

    goal = g.get("member_goal") or 0
    early = g.get("early_start") or 0
    joined = len(g.get("participants", []))
    percent = int((joined/goal)*100) if goal else 0

    if members_count < goal - early:
        text = (f"🚫 Sorteo pendiente: se requiere {goal} miembros para iniciar.\n\n"
                f"Somos {members_count}/{goal}.")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⏳ Aún no disponible", callback_data="wait"))
    elif members_count < goal:
        text = (f"🍷✨ <b>{g.get('title','Sorteo')}</b>\n\n"
                f"{g.get('desc','')}\n\n"
                f"👥 {members_count}/{goal} — esperando más integrantes...")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⏳ Aún no disponible", callback_data="wait"))
    else:
        remain = max(0, int(g.get("end_real", time.time()) - time.time()))
        mins, secs = divmod(remain, 60)
        text = (f"🍷✨ <b>{g.get('title','Sorteo')}</b>\n\n"
                f"{g.get('desc','')}\n\n"
                f"⏱️ Termina a las {time.strftime('%H:%M:%S', time.localtime(g.get('end_real', time.time())))}\n"
                f"⏳ Faltan {mins:02d}:{secs:02d}\n"
                f"👥 {joined}/{goal} ({percent}%)\n"
                f"👑 Ganadores: {g.get('num_winners',1)}\n\n"
                f"Pulsa en <b>Unirse</b> para participar.")
        markup = build_markup_admin(gid, g)

    try:
        if g.get("msg_id"):
            if g.get("image"):
                # edit_message_caption signature: chat_id, message_id, caption=...
                bot.edit_message_caption(chat_id=g["group"], message_id=g["msg_id"], caption=text, reply_markup=markup, parse_mode="HTML")
            else:
                bot.edit_message_text(text, g["group"], g["msg_id"], reply_markup=markup, parse_mode="HTML")
        else:
            if g.get("image"):
                sent = bot.send_photo(g["group"], g["image"], caption=text, reply_markup=markup, parse_mode="HTML")
            else:
                sent = bot.send_message(g["group"], text, reply_markup=markup, parse_mode="HTML")
            g["msg_id"] = sent.message_id
    except Exception as e:
        # reduce spam for rate limits
        err = str(e)
        if "Too Many Requests" in err:
            # keep quiet and let check loop handle retry timing
            pass
        else:
            print("update_message error:", e)
    save_data()

# ---------------- Callback handlers: join and admin ----------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("join_"))
def join_callback(call):
    gid = call.data.split("_", 1)[1]
    g = giveaways.get(gid)
    if not g or not g.get("active"):
        return bot.answer_callback_query(call.id, "⏳ El sorteo no está activo.")
    if call.from_user.id in g.get("participants", []):
        return bot.answer_callback_query(call.id, "Ya estás participando.")
    g.setdefault("participants", []).append(call.from_user.id)
    ensure_user(call.from_user.id)
    users[str(call.from_user.id)]["points"] = users[str(call.from_user.id)].get("points", 0) + 1
    users[str(call.from_user.id)]["joined"] = users[str(call.from_user.id)].get("joined",0) + 1
    save_users()
    save_data()
    update_message(gid)
    # transient join message (deleted after 5s)
    try:
        m = bot.send_message(g["group"], f"✨ {user_display(call.from_user.id)} se ha unido al sorteo. ¡Suerte!", reply_to_message_id=g.get("msg_id"))
        delete_later(g["group"], m.message_id, 5)
    except:
        pass
    bot.answer_callback_query(call.id, "✅ Te has unido al sorteo.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("force_end_", "force_restart_", "view_status_")))
def admin_controls(call):
    data = call.data.split("_",2)
    action = data[0]
    gid = data[-1]
    g = giveaways.get(gid)
    # only allow creator or group admin to use these buttons
    try:
        member = bot.get_chat_member(g["group"], call.from_user.id)
        is_admin = member.status in ["administrator","creator"] or call.from_user.id == g.get("creator")
    except:
        is_admin = False
    if not is_admin:
        return bot.answer_callback_query(call.id, "❌ Solo administradores pueden usar este botón.")

    if call.data.startswith("force_end_"):
        finish_giveaway(gid)
        bot.answer_callback_query(call.id, "🛑 Sorteo finalizado por administrador.")
    elif call.data.startswith("force_restart_"):
        # reset participants and timers but keep configuration
        g["participants"] = []
        g["start_time"] = time.time()
        g["end_real"] = g["start_time"] + g.get("end_time",0)
        g["reminders_sent"] = []
        g["last_remain"] = None
        g["last_participants"] = None
        save_data()
        update_message(gid)
        bot.answer_callback_query(call.id, "🔄 Sorteo reiniciado por administrador.")
    elif call.data.startswith("view_status_"):
        joined = len(g.get("participants",[]))
        text = (f"📊 Estado del sorteo:\n\n"
                f"• Título: {g.get('title')}\n"
                f"• Participantes: {joined}\n"
                f"• Ganadores: {g.get('num_winners')}\n"
                f"• Creator: {user_display(g.get('creator'))}\n"
                f"• Mensaje original: https://t.me/c/{str(g.get('group'))[4:]}/{g.get('msg_id') if g.get('msg_id') else 'N/A'}")
        bot.send_message(call.from_user.id, text)
        bot.answer_callback_query(call.id, "📬 Te envié el estado por privado.")

# ---------------- End command ----------------

@bot.message_handler(commands=["end"])
def end_cmd(message):
    for gid, g in list(giveaways.items()):
        if g.get("creator") == message.from_user.id and g.get("active"):
            finish_giveaway(gid)

# ---------------- Finish giveaway ----------------

def finish_giveaway(gid):
    g = giveaways.get(gid)
    if not g:
        return
    g["active"] = False

    valid_participants = [p for p in g.get("participants", []) if p != g.get("creator")]

    winners = []
    if valid_participants:
        # weighted entries: 1 + floor(points/5)
        entries = []
        for p in valid_participants:
            pts = users.get(str(p), {}).get("points",0)
            tickets = 1 + (pts // 5)
            entries.extend([p]*tickets)

        n = min(g.get("num_winners",1), len(valid_participants))
        winners = []
        while len(winners) < n and entries:
            pick = random.choice(entries)
            if pick not in winners:
                winners.append(pick)
            # remove all occurrences of picked user from entries
            entries = [e for e in entries if e != pick]

        # animated announcement
        try:
            bot.send_message(g["group"], "🎲 Seleccionando ganador(es)...", reply_to_message_id=g.get("msg_id"))
            time.sleep(1)
            bot.send_message(g["group"], "🌀 Girando la ruleta...", reply_to_message_id=g.get("msg_id"))
            time.sleep(1)
            bot.send_message(g["group"], "✨ Preparando resultado final...", reply_to_message_id=g.get("msg_id"))
            time.sleep(1)
        except:
            pass

        # Build winners text and update user stats / notify winners
        winners_text = []
        for w in winners:
            try:
                uchat = bot.get_chat(w)
                if getattr(uchat, "username", None):
                    name = f"@{uchat.username}"
                elif getattr(uchat, "first_name", None):
                    safe = telebot.util.escape(uchat.first_name)
                    name = f"<a href='tg://user?id={w}'>{safe}</a>"
                else:
                    name = f"<a href='tg://user?id={w}'>Usuario</a>"
            except:
                name = f"<a href='tg://user?id={w}'>Usuario</a>"
            winners_text.append(name)

            ensure_user(w)
            users[str(w)]["wins"] = users[str(w)].get("wins", 0) + 1
            users[str(w)]["points"] = users[str(w)].get("points", 0) + 5
            save_users()
            # send DM to winner (try, ignore errors)
            try:
                bot.send_message(w, f"🎉 ¡Felicidades! Has ganado el sorteo «{g.get('title')}» en el grupo {g.get('group')}. Contacta al creador para reclamar tu premio.")
            except:
                pass

        final_text = "👑🍷 ¡Ganador(es)! 🍷👑\n\n" + "\n".join([f"• {t}" for t in winners_text])
        try:
            bot.send_message(g["group"], final_text, parse_mode="HTML", reply_to_message_id=g.get("msg_id"))
        except:
            bot.send_message(g["group"], "🎉 ¡Tenemos ganador(es)!", reply_to_message_id=g.get("msg_id"))

        # summary message
        summary = (f"📋 Resumen del sorteo:\n\n"
                   f"• Título: {g.get('title')}\n"
                   f"• Duración: {format_duration(g.get('end_time',0))}\n"
                   f"• Participantes: {len(g.get('participants',[]))}\n"
                   f"• Ganadores: {', '.join([user_display(w) for w in winners])}\n"
                   f"• Creator: {user_display(g.get('creator'))}")
        try:
            bot.send_message(g["group"], summary)
        except:
            pass
    else:
        try:
            bot.send_message(g.get("group"), "❌ No hubo participantes válidos en el sorteo.", reply_to_message_id=g.get("msg_id"))
        except:
            pass

    save_data()
    backup_data()

# ---------------- Loop: reminders and smart updates ----------------

def check_giveaways():
    while True:
        now = time.time()
        for gid, g in list(giveaways.items()):
            if g.get("active") and g.get("start_time"):
                remain = g.get("end_real", 0) - now

                # reminders 10m,5m,1m
                try:
                    rs = g.get("reminders_sent", [])
                    if remain <= 600 and "10m" not in rs:
                        bot.send_message(g["group"], "⏰ Recordatorio: faltan 10 minutos para que termine el sorteo.", reply_to_message_id=g.get("msg_id"))
                        rs.append("10m")
                    if remain <= 300 and "5m" not in rs:
                        bot.send_message(g["group"], "⏰ Recordatorio: faltan 5 minutos para que termine el sorteo.", reply_to_message_id=g.get("msg_id"))
                        rs.append("5m")
                    if remain <= 60 and "1m" not in rs:
                        bot.send_message(g["group"], "⏰ Recordatorio: faltan 1 minuto para que termine el sorteo.", reply_to_message_id=g.get("msg_id"))
                        rs.append("1m")
                    g["reminders_sent"] = rs
                    save_data()
                except:
                    pass

                # final countdown (<=5s)
                if 0 < remain <= 5:
                    sec = int(remain)
                    try:
                        bot.send_message(g["group"], f"{sec}...", reply_to_message_id=g.get("msg_id"))
                    except:
                        pass
                    time.sleep(1)
                    if sec == 1:
                        finish_giveaway(gid)
                        continue

                elif remain <= 0:
                    finish_giveaway(gid)
                    continue
                else:
                    # smart real-time update: update only if remain or participants changed
                    remain_new = int(g.get("end_real", 0) - now)
                    last_remain = g.get("last_remain", None)
                    last_participants = g.get("last_participants", None)
                    current_participants = len(g.get("participants", []))

                    if last_remain != remain_new or last_participants != current_participants:
                        g["last_remain"] = remain_new
                        g["last_participants"] = current_participants
                        update_message(gid)
                        save_data()

                    time.sleep(1)

            elif g.get("active"):
                update_message(gid)

        time.sleep(1)

# ---------------- Start background loop and bot ----------------

threading.Thread(target=check_giveaways, daemon=True).start()

print("🤖 Bot pro elite corriendo... 🍷✨👑")
bot.infinity_polling()

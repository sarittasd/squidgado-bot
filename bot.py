import os, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class _Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

threading.Thread(
    target=lambda: HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), _Ping).serve_forever(),
    daemon=True,
).start()

from collections import defaultdict, deque
import re
import time
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = "8841703241:AAFog3IQUzPKh51ZaJw8p5kWGL-Bb7XsByY"
BOT_USERNAME = "squidgado_bot"

MAX_ADVERTENCIAS = 3
FLOOD_MAX_MENSAJES = 5
FLOOD_VENTANA_SEGUNDOS = 6
MINUTOS_SILENCIO_FLOOD = 10

DOMINIOS_SOSPECHOSOS = (
    "bit.ly",
    "tinyurl.com",
    "t.me/joinchat_fake",
    "free-nitro",
    "claim-reward",
    "crypto-giveaway",
    "pornhub.com",
    "xvideos.com",
    "xnxx.com",
)

historial_mensajes = defaultdict(lambda: deque(maxlen=20))
advertencias = defaultdict(int)
usuarios_conocidos = set()


async def es_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    chat = update.effective_chat
    if not chat or chat.type == "private":
        return False
    miembro = await context.bot.get_chat_member(chat.id, user_id)
    return miembro.status in ("administrator", "creator")


def contiene_enlace_sospechoso(texto: str) -> bool:
    texto_bajo = texto.lower()
    if any(dominio in texto_bajo for dominio in DOMINIOS_SOSPECHOSOS):
        return True
    if re.search(r"https?://[^\s]+", texto_bajo) and re.search(
        r"(gratis|premio|regalo|cripto|bonus|xxx|nsfw|onlyfans)", texto_bajo
    ):
        return True
    return False

import re, time
from collections import defaultdict, deque
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = "8841703241:AAFog3IQUzPKh51ZaJw8p5kWGL-Bb7XsByY"
BOT_USERNAME = "squidgado_bot"
BAD_DOMAINS = ("bit.ly", "tinyurl.com", "free-nitro", "claim-reward", "crypto-giveaway", "pornhub.com", "xvideos.com", "xnxx.com")

msgs = defaultdict(lambda: deque(maxlen=20))
warns = defaultdict(int)
known = set()

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int) -> bool:
    chat = update.effective_chat
    if not chat or chat.type == "private":
        return False
    m = await context.bot.get_chat_member(chat.id, uid)
    return m.status in ("administrator", "creator")

def bad_link(text: str) -> bool:
    t = text.lower()
    if any(d in t for d in BAD_DOMAINS):
        return True
    return bool(re.search(r"https?://[^\s]+", t) and re.search(r"(gratis|premio|regalo|cripto|bonus|xxx|nsfw|onlyfans)", t))

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for m in update.message.new_chat_members:
        if m.is_bot:
            continue
        if m.is_deleted:
            await context.bot.ban_chat_member(chat.id, m.id)
            await update.message.reply_text("Cuenta fantasma eliminada. Aquí no entran espectros.")
            continue
        known.add(m.id)
        context.bot_data[f"pend_{m.id}"] = chat.id
        await context.bot.restrict_chat_member(chat.id, m.id, ChatPermissions(can_send_messages=False))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("PULSA AQUÍ · IR A CONTROL", url=f"https://t.me/{BOT_USERNAME}?start=control")]])
        await update.message.reply_text(f"Bienvenido/a, {m.first_name}. Pulsa aquí abajo para abrir mi privado y poder entrar en regla. Sin pasar por control no hablas.", reply_markup=kb)

async def left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.message.left_chat_member
    if m and not m.is_bot and m.id in known:
        try:
            await context.bot.send_message(m.id, f"Has salido del grupo, {m.first_name}. Tu registro queda cerrado. Si vuelves, tendrás que pasar por control otra vez.")
        except Exception:
            pass

async def start_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    u = update.effective_user
    known.add(u.id)
    await update.message.reply_text(f"Bienvenido/a, {u.first_name}. Soy el encargado de máscara cuadrada.\n\n1. Nada de flood ni spam.\n2. Prohibidos enlaces fraudulentos o contenido explícito.\n3. A las 3 advertencias, fuera.")
    gid = context.bot_data.pop(f"pend_{u.id}", None)
    if gid:
        await context.bot.restrict_chat_member(gid, u.id, ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_other_messages=True, can_add_web_page_previews=True))

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, name: str, reason: str):
    cid = update.effective_chat.id
    warns[(cid, uid)] += 1
    total = warns[(cid, uid)]
    if total >= 3:
        warns[(cid, uid)] = 0
        await context.bot.ban_chat_member(cid, uid)
        await update.message.reply_text(f"{name} ha acumulado 3 advertencias ({reason}). Expulsado.")
    else:
        await update.message.reply_text(f"Advertencia {total}/3 para {name}. Motivo: {reason}.")

async def cmd_advertir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not await is_admin(update, context, update.effective_user.id):
        return
    t = update.message.reply_to_message.from_user
    await warn_user(update, context, t.id, t.first_name, " ".join(context.args) or "incumplir normas")

async def cmd_silenciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not await is_admin(update, context, update.effective_user.id):
        return
    t = update.message.reply_to_message.from_user
    mins = int(context.args[0]) if context.args and context.args[0].isdigit() else 15
    await context.bot.restrict_chat_member(update.effective_chat.id, t.id, ChatPermissions(can_send_messages=False), until_date=int(time.time()) + mins * 60)
    await update.message.reply_text(f"{t.first_name} silenciado {mins} minutos.")

async def cmd_expulsar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not await is_admin(update, context, update.effective_user.id):
        return
    t = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, t.id)
    await update.message.reply_text(f"{t.first_name} fuera del grupo.")

async def cmd_fijar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not await is_admin(update, context, update.effective_user.id):
        return
    await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id, disable_notification=True)
    await update.message.reply_text("Aviso fijado.")

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, chat, u = update.message, update.effective_chat, update.effective_user
    if not msg or not u or u.is_bot or chat.type == "private":
        return
    known.add(u.id)
    text = msg.text or msg.caption or ""
    if text and bad_link(text):
        await msg.delete()
        await warn_user(update, context, u.id, u.first_name, "enlace no permitido")
        return
    now = time.time()
    q = msgs[(chat.id, u.id)]
    q.append(now)
    if len([x for x in q if now - x <= 6]) >= 5:
        q.clear()
        await context.bot.restrict_chat_member(chat.id, u.id, ChatPermissions(can_send_messages=False), until_date=int(now) + 600)
        await msg.reply_text(f"Baja el ritmo, {u.first_name}. Flood detectado: 10 minutos callado.")
        return
    if any(k in text.lower() for k in (f"@{BOT_USERNAME.lower()}", "encargado", "reglas")):
        await msg.reply_text("Yo vigilo el orden y aplico las normas. Para juegos o música busca otro; aquí se respeta el turno.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member))
    app.add_handler(CommandHandler("start", start_dm))
    app.add_handler(CommandHandler("advertir", cmd_advertir))
    app.add_handler(CommandHandler("silenciar", cmd_silenciar))
    app.add_handler(CommandHandler("expulsar", cmd_expulsar))
    app.add_handler(CommandHandler("fijar", cmd_fijar))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, watch))
    app.run_polling()

if __name__ == "__main__":
    main()

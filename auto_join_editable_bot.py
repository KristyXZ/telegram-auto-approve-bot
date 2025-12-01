import json
import os
import sqlite3
import threading
import time
import requests
from datetime import datetime
from telegram import Update, ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ==================== DATABASE SETUP ====================
conn = sqlite3.connect("public_bot.db", check_mode=0.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS settings (
             chat_id INTEGER PRIMARY KEY,
             welcome_text TEXT,
             photo TEXT,
             buttons TEXT,
             enabled INTEGER DEFAULT 1)''')
c.execute('''CREATE TABLE IF NOT EXISTS stats (
             chat_id INTEGER PRIMARY KEY,
             total INTEGER DEFAULT 0,
             today INTEGER DEFAULT 0,
             date TEXT)''')
conn.commit()

# ==================== KEEP ALIVE ====================
def keep_alive():
    url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RAILWAY_STATIC_URL") or "https://your-service.up.railway.app"
    if "none" not in url.lower():
        while True:
            try:
                requests.get(url, timeout=10)
                print(f"Ping → {url}")
            except:
                pass
            time.sleep(100)

if os.getenv("RENDER") or os.getenv("RAILWAY"):
    threading.Thread(target=keep_alive, daemon=True).start()

# ==================== TOKEN ====================
TOKEN = os.getenv("BOT_TOKEN") or "8368848544:AAGBbmWBHs9miGRCen1B14nhd7LQ18mA9hI"  # ← public bot-na change pannu

# ==================== HELPERS ====================
def get_settings(chat_id):
    c.execute("SELECT * FROM settings WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    if row:
        return {
            "text": row[1 or "Hello {name}!\nWelcome to {title}",
            "photo": row[2],
            "buttons": json.loads(row[3]) if row[3] else [],
            "enabled": bool(row[4])
        }
    else:
        default_buttons = [[{"text": "Our Channel", "url": "https://t.me/yourchannel"}]]
        c.execute("INSERT INTO settings (chat_id, welcome_text, buttons) VALUES (?,?,?)",
                  (chat_id, "Hello {name}!\nWelcome to {title}", json.dumps(default_buttons)))
        conn.commit()
        return {"text": "Hello {name}!\nWelcome to {title}", "buttons": default_buttons}

def save_buttons(chat_id, buttons):
    c.execute("UPDATE settings SET buttons=? WHERE chat_id=?", (json.dumps(buttons), chat_id))
    conn.commit()

# ==================== JOIN REQUEST ====================
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    chat = req.chat
    user = req.from_user
    settings = get_settings(chat.id)

    if not settings.get("enabled", True):
        await req.decline()
        return

    # Stats
    today = str(datetime.now().date())
    c.execute("INSERT OR IGNORE INTO stats (chat_id, total, today, date) VALUES (?,?,?,?)",
              (chat.id, 0, 0, today))
    c.execute("UPDATE stats SET total = total + 1, today = today + 1 WHERE chat_id=?", (chat.id,))
    if c.rowcount == 0:
        c.execute("UPDATE stats SET today = 1, date=? WHERE chat_id=?", (today, chat.id))
    conn.commit()

    await req.approve()

    keyboard = [[InlineKeyboardButton(b["text"], url=b["url"]) for b in row] for row in settings["buttons"]]
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard != [[]] else None

    text = settings["text"].format(name=user.first_name, title=chat.title or "our community")

    try:
        if settings["photo"]:
            await context.bot.send_photo(user.id, photo=open(settings["photo"], "rb"),
                                       caption=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(user.id, text, reply_markup=reply_markup,
                                         disable_web_page_preview=True)
    except:
        pass  # user blocked bot

# ==================== SETUP & PANEL ====================
async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    if member.status not in ("administrator", "creator"):
        return

    get_settings(chat.id)  # create entry
    await update.message.reply_text(
        "Bot setup complete!\n\n"
        "Now use /panel to customize welcome message, photo & buttons for this group/channel",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open Panel", callback_data=f"panel_{chat.id}")]])
    )

async def panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split("_")[1])

    member = await context.bot.get_chat_member(chat_id, query.from_user.id)
    if member.status not in ("administrator", "creator"):
        await query.edit_message_text("Only admins can use panel")
        return

    keyboard = [
        [InlineKeyboardButton("Change Text", callback_data=f"text_{chat_id}")],
        [InlineKeyboardButton("Change Photo", callback_data=f"photo_{chat_id}")],
        [InlineKeyboardButton("Edit Buttons", callback_data=f"buttons_{chat_id}")],
        [InlineKeyboardButton("Toggle ON/OFF", callback_data=f"toggle_{chat_id}")],
        [InlineKeyboardButton("Stats", callback_data=f"stats_{chat_id}")],
    ]
    await query.edit_message_text("Welcome Bot Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# Add more callback handlers for text/photo/buttons etc (comment-la solren if full code venum)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Public Premium Auto Join Bot\n\n"
        "Add me to your channel/group as admin → /setup\n"
        "Then customize using /panel\n\n"
        "Supports: Photo + Buttons + Per-chat settings + Stats"
    )

# ==================== RUN ====================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setup", setup))
app.add_handler(ChatJoinRequestHandler(join_request))
app.add_handler(CallbackQueryHandler(panel_button, pattern="panel_"))

print("PUBLIC PREMIUM AUTO JOIN BOT LIVE – Add to any channel/group!") 

app.run_polling(drop_pending_updates=True)

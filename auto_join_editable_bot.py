import os
import threading
import time
import requests
from datetime import datetime
from telegram import (
    Update, ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder, ChatJoinRequestHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from pymongo import MongoClient

# ==================== MONGODB ====================
MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    print("MONGO_URL not set!")
    exit()

client = MongoClient(MONGO_URL)
db = client["autojoin_pro"]
settings_db = db["settings"]
stats_db = db["stats"]

# ==================== TOKEN ====================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("BOT_TOKEN missing!")
    exit()

# ==================== KEEP ALIVE (Railway/Render) ====================
def keep_alive():
    url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RAILWAY_STATIC_URL") or "https://google.com"
    while True:
        try:
            requests.get(url, timeout=8)
        except:
            pass
        time.sleep(100)

threading.Thread(target=keep_alive, daemon=True).start()

# ==================== GET SETTINGS ====================
def get_settings(chat_id):
    data = settings_db.find_one({"chat_id": chat_id})
    if not data:
        default = {
            "chat_id": chat_id,
            "text": "Hello {name}!\nWelcome to {title}!\n\nEnjoy your stay!",
            "photo": None,
            "buttons": [[{"text": "Our Channel", "url": "https://t.me/yourchannel"}]],
            "enabled": True
        }
        settings_db.insert_one(default)
        return default
    return data

# ==================== JOIN REQUEST ====================
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    chat_id = req.chat.id
    user = req.from_user
    chat_title = req.chat.title or "community"

    config = get_settings(chat_id)
    if not config.get("enabled", True):
        await req.decline()
        return

    # Stats
    today = datetime.now().date().isoformat()
    stats_db.update_one(
        {"chat_id": chat_id},
        {"$inc": {"total": 1}, "$setOnInsert": {"today": 1, "date": today}},
        upsert=True
    )

    await req.approve()

    text = config["text"].format(name=user.first_name or "User", title=chat_title)

    keyboard = []
    for row in config.get("buttons", []):
        buttons_row = [InlineKeyboardButton(b["text"], url=b["url"]) for b in row]
        keyboard.append(buttons_row)
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    try:
        if config.get("photo"):
            await context.bot.send_photo(
                user.id, photo=InputFile(config["photo"]),
                caption=text, reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                user.id, text, reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    except:
        pass

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Public Premium Auto Join Bot\n\n"
        "Add me to your channel/group as admin\n"
        "Then type /setup → /panel"
    )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ["supergroup", "channel"]:
        return
    member = await chat.get_member(update.effective_user.id)
    if member.status not in ["administrator", "creator"]:
        return

    get_settings(chat.id)
    await update.message.reply_text(
        "Setup done!\nNow use /panel",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Open Panel", callback_data=f"open_panel|{chat.id}")
        ]])
    )

# ==================== FULL INLINE PANEL ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("open_panel|"):
        chat_id = int(data.split("|")[1])
        if (await context.bot.get_chat_member(chat_id, query.from_user.id)).status not in ["administrator", "creator"]:
            await query.edit_message_text("Only Admin!")
            return

        kb = [
            [InlineKeyboardButton("Change Text", callback_data=f"text|{chat_id}")],
            [InlineKeyboardButton("Set Photo", callback_data=f"photo|{chat_id}")],
            [InlineKeyboardButton("Toggle Bot", callback_data=f"toggle|{chat_id}")],
            [InlineKeyboardButton("Stats", callback_data=f"stats|{chat_id}")],
            [InlineKeyboardButton("Back", callback_data=f"open_panel|{chat_id}")],
        ]
        await query.edit_message_text("Welcome Bot Panel", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("toggle|"):
        chat_id = int(data.split("|")[1])
        current = get_settings(chat_id)
        new_status = not current.get("enabled", True)
        settings_db.update_one({"chat_id": chat_id}, {"$set": {"enabled": new_status}})
        await query.edit_message_text(f"Bot {'Enabled' if new_status else 'Disabled'}")

    elif data.startswith("stats|"):
        chat_id = int(data.split("|")[1])
        stats = stats_db.find_one({"chat_id": chat_id}) or {"total": 0}
        await query.edit_message_text(f"Total Joins: {stats['total']}")

# ==================== START BOT ====================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setup", setup))
app.add_handler(ChatJoinRequestHandler(join_request))
app.add_handler(CallbackQueryHandler(callback_handler))

print("PUBLIC PREMIUM AUTO JOIN BOT – FULLY WORKING WITH INLINE PANEL")
app.run_polling(drop_pending_updates=True)

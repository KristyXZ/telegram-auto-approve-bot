import os
import threading
import time
import requests
from datetime import datetime
from telegram import Update, ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from pymongo import MongoClient

# ==================== MONGODB ATLAS SETUP ====================
MONGO_URL = os.getenv("MONGO_URL")  # Render la podu (mongodb+srv://...)
if not MONGO_URL:
    print("ERROR: MONGO_URL not set!")
    exit()

client = MongoClient(MONGO_URL)
db = client["auto_join_bot"]
settings_col = db["settings"]
stats_col = db["stats"]

# ==================== KEEP ALIVE ====================
def keep_alive():
    url = os.getenv("RENDER_EXTERNAL_URL")
    if url:
        while True:
            try:
                requests.get(url, timeout=10)
                print(f"[{time.strftime('%H:%M:%S')}] Ping → {url}")
            except:
                pass
            time.sleep(110)

if os.getenv("RENDER") == "true":
    threading.Thread(target=keep_alive, daemon=True).start()

# ==================== TOKEN ====================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("BOT_TOKEN missing!")
    exit()

# ==================== HELPERS ====================
def get_settings(chat_id):
    data = settings_col.find_one({"chat_id": chat_id})
    if not data:
        default = {
            "chat_id": chat_id,
            "text": "Hello {name}!\nWelcome to {title}!\n\nEnjoy your stay!",
            "photo": None,
            "buttons": [[{"text": "Our Channel", "url": "https://t.me/yourchannel"}]],
            "enabled": True
        }
        settings_col.insert_one(default)
        return default
    return data

# ==================== JOIN REQUEST ====================
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    chat_id = req.chat.id
    user = req.from_user
    chat_title = req.chat.title or "our community"

    config = get_settings(chat_id)
    if not config.get("enabled", True):
        await req.decline()
        return

    # Update stats
    today = datetime.now().date().isoformat()
    stats_col.update_one(
        {"chat_id": chat_id},
        {"$inc": {"total": 1, "today": 1}, "$set": {"date": today}},
        upsert=True
    )

    await req.approve()

    text = config["text"].format(name=user.first_name or "User", title=chat_title)
    keyboard = [[InlineKeyboardButton(btn["text"], url=btn["url"]) for btn in row] 
                for row in config.get("buttons", [])]
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard != [[]] else None

    try:
        if config.get("photo"):
            with open(config["photo"], "rb") as f:
                await context.bot.send_photo(user.id, photo=f, caption=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(user.id, text, reply_markup=reply_markup, disable_web_page_preview=True)
    except:
        pass  # user blocked bot or privacy mode

# ==================== SETUP & PANEL ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Public Premium Auto Join Bot\n\n"
            "Add me to your Channel/Group as Admin → /setup\n"
            "Then use /panel to customize everything!"
        )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ["channel", "supergroup", "group"]:
        member = await chat.get_member(update.effective_user.id)
        if member.status not in ["administrator", "creator"]:
            return
        get_settings(chat.id)  # create if not exists
        await update.message.reply_text(
            "Setup Complete!\nNow use /panel to customize welcome message, photo & buttons",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Open Panel", callback_data=f"panel_{chat.id}")
            ]])
        )

async def panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("panel_"):
        chat_id = int(data.split("_")[1])
        member = await context.bot.get_chat_member(chat_id, query.from_user.id)
        if member.status not in ["administrator", "creator"]:
            await query.edit_message_text("Only Admins!")
            return

        keyboard = [
            [InlineKeyboardButton("Change Text", callback_data=f"text_{chat_id}")],
            [InlineKeyboardButton("Set Photo", callback_data=f"photo_{chat_id}")],
            [InlineKeyboardButton("Edit Buttons", callback_data=f"buttons_{chat_id}")],
            [InlineKeyboardButton("Toggle ON/OFF", callback_data=f"toggle_{chat_id}")],
            [InlineKeyboardButton("Stats", callback_data=f"stats_{chat_id}")],
        ]
        await query.edit_message_text("Panel – Choose Option:", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== BOT START ====================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setup", setup))
app.add_handler(ChatJoinRequestHandler(join_request))
app.add_handler(CallbackQueryHandler(panel_callback, pattern="^panel_"))

print("PUBLIC PREMIUM AUTO JOIN BOT WITH MONGODB – LIVE 24×7")
app.run_polling(drop_pending_updates=True)

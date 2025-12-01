import json
import os
import threading
import time
import requests
from telegram import Update, ChatJoinRequest, InputFile
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==================== AUTO KEEP-ALIVE FOR RENDER ====================
def keep_alive():
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        print("Not on Render or URL not found → Keep-alive off")
        return
    while True:
        try:
            requests.get(url, timeout=10)
            print(f"[{time.strftime('%H:%M:%S')}] Ping → {url}")
        except:
            print("Ping failed")
        time.sleep(120)

if os.getenv("RENDER") == "true":
    threading.Thread(target=keep_alive, daemon=True).start()

# ==================== TOKEN & CONFIG ====================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("ERROR: BOT_TOKEN not set in Render Environment Variables!")
    exit()

CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        default = {
            "text": "Hello {name}! Welcome to our channel",
            "photo": None,
            "video": None,
            "voice": None
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# ==================== JOIN REQUEST ====================
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    req = update.chat_join_request
    user = req.from_user
    name = user.first_name or "User"

    await req.approve()
    await context.bot.send_message(chat_id=user.id, text=cfg["text"].format(name=name))

    if cfg["photo"]:
        await context.bot.send_photo(chat_id=user.id, photo=InputFile(cfg["photo"]))
    if cfg["video"]:
        await context.bot.send_video(chat_id=user.id, video=InputFile(cfg["video"]))
    if cfg["voice"]:
        await context.bot.send_voice(chat_id=user.id, voice=InputFile(cfg["voice"]))

    print(f"Approved & welcomed → {name}")

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Auto Approve + Welcome Bot Live!\n\n"
        "Commands:\n"
        "/settext Hello {name} machaa!\n"
        "/setphoto → photo with caption /setphoto\n"
        "/setvideo → video with caption /setvideo\n"
        "/setvoice → voice with caption /setvoice"
    )

async def set_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /settext <your message>")
        return
    cfg = load_config()
    cfg["text"] = " ".join(context.args)
    save_config(cfg)
    await update.message.reply_text("Text updated!")

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Send photo with caption /setphoto")
        return
    file = await update.message.photo[-1].get_file()
    await file.download_to_drive("welcome_photo.jpg")
    cfg = load_config()
    cfg["photo"] = "welcome_photo.jpg"
    save_config(cfg)
    await update.message.reply_text("Photo updated!")

async def set_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text("Send video with caption /setvideo")
        return
    file = await update.message.video.get_file()
    await file.download_to_drive("welcome_video.mp4")
    cfg = load_config()
    cfg["video"] = "welcome_video.mp4"
    save_config(cfg)
    await update.message.reply_text("Video updated!")

async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.voice:
        await update.message.reply_text("Send voice with caption /setvoice")
        return
    file = await update.message.voice.get_file()
    await file.download_to_drive("welcome_voice.ogg")
    cfg = load_config()
    cfg["voice"] = "welcome_voice.ogg"
    save_config(cfg)
    await update.message.reply_text("Voice updated!")

# ==================== START BOT ====================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("settext", set_text))
app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r"^/setphoto$"), set_photo))
app.add_handler(MessageHandler(filters.VIDEO & filters.CaptionRegex(r"^/setvideo$"), set_video))
app.add_handler(MessageHandler(filters.VOICE & filters.CaptionRegex(r"^/setvoice$"), set_voice))
app.add_handler(ChatJoinRequestHandler(join_request))

print("Bot is running 24×7 | Auto keep-alive active")
app.run_polling(drop_pending_updates=True)

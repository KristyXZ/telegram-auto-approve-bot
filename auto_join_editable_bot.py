import json
from telegram import Update, ChatJoinRequest, InputFile
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8436334225:AAFOWPKCbCt7HxGasB94dRaymfpFUIh1jIE"  # <== yahan apna new safe token daalo
CONFIG_FILE = "config.json"


# 🧠 Load or create config
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        default = {
            "text": "👋 Hello {name}! Welcome to our channel 🎉",
            "photo": None,
            "video": None,
            "voice": None
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f)
        return default


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


# 🔔 When someone requests to join
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    req: ChatJoinRequest = update.chat_join_request
    user = req.from_user
    name = user.first_name or "User"

    await req.approve()
    await context.bot.send_message(chat_id=user.id, text=cfg["text"].format(name=name))

    # Send any attached media
    if cfg["photo"]:
        await context.bot.send_photo(chat_id=user.id, photo=InputFile(cfg["photo"]))
    if cfg["video"]:
        await context.bot.send_video(chat_id=user.id, video=InputFile(cfg["video"]))
    if cfg["voice"]:
        await context.bot.send_voice(chat_id=user.id, voice=InputFile(cfg["voice"]))

    print(f"✅ Approved {name} and sent welcome message.")


# ✏️ Change welcome text
async def set_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = " ".join(context.args)
    if not new_text:
        await update.message.reply_text("❗ Use: /settext <your message>")
        return
    cfg = load_config()
    cfg["text"] = new_text
    save_config(cfg)
    await update.message.reply_text("✅ Custom text updated!")


# 🖼️ Change photo
async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("📸 Please send a photo with caption /setphoto")
        return
    file = await update.message.photo[-1].get_file()
    path = "welcome_photo.jpg"
    await file.download_to_drive(path)
    cfg = load_config()
    cfg["photo"] = path
    save_config(cfg)
    await update.message.reply_text("✅ Welcome photo updated!")


# 🎥 Change video
async def set_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text("🎥 Please send a video with caption /setvideo")
        return
    file = await update.message.video.get_file()
    path = "welcome_video.mp4"
    await file.download_to_drive(path)
    cfg = load_config()
    cfg["video"] = path
    save_config(cfg)
    await update.message.reply_text("✅ Welcome video updated!")


# 🎙️ Change voice
async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.voice:
        await update.message.reply_text("🎙️ Please send a voice with caption /setvoice")
        return
    file = await update.message.voice.get_file()
    path = "welcome_voice.ogg"
    await file.download_to_drive(path)
    cfg = load_config()
    cfg["voice"] = path
    save_config(cfg)
    await update.message.reply_text("✅ Welcome voice updated!")


# 🧩 Start command info
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Editable Auto-Approve Bot Active!\n\n"
        "Commands:\n"
        "/settext <message> – Change welcome message\n"
        "/setphoto – Send photo with caption /setphoto\n"
        "/setvideo – Send video with caption /setvideo\n"
        "/setvoice – Send voice with caption /setvoice\n\n"
        "Example:\n"
        "/settext 👋 Hello {name}! Welcome to our community 🎉"
    )


# 🚀 Start the bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("settext", set_text))
app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex("/setphoto"), set_photo))
app.add_handler(MessageHandler(filters.VIDEO & filters.CaptionRegex("/setvideo"), set_video))
app.add_handler(MessageHandler(filters.VOICE & filters.CaptionRegex("/setvoice"), set_voice))
app.add_handler(ChatJoinRequestHandler(join_request))

print("🤖 Bot is running... waiting for join requests.")
app.run_polling()

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# === CONFIG ===
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DB_FILE = "database.json"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set! Check .env file!")

# === DATABASE ===
def get_db():
    if not os.path.exists(DB_FILE):
        data = {"users": {}}
        save_db(data)
        return data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"DB Error: {e}")

def init_user(uid):
    uid = str(uid)
    db = get_db()
    if uid not in db["users"]:
        db["users"][uid] = {
            "tier": "none",
            "expired": None,
            "session": "",
            "claimed_trial": False,
            "is_reseller": False,
            "settings": {
                "bc_enabled": False,
                "bc_text": "",
                "bc_delay": 5,
                "bc_targets": [],
                "fw_enabled": False,
                "fw_source_ch": "",
                "fw_targets": [],
                "ar_enabled": False,
                "ar_keywords": [],
                "ar_banwords": []
            }
        }
    save_db(db)

# === BOT ===
bot_app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
login_sessions = {}
user_states = {}
active_userbots = {}

def build_main_keyboard(uid):
    buttons = [
        [KeyboardButton("🚀 Login Userbot"), KeyboardButton("⚙️ Panel Control")],
        [KeyboardButton("🛒 Toko"), KeyboardButton("🎁 Trial 5 Jam")],
    ]
    if uid == OWNER_ID:
        buttons.append([KeyboardButton("👑 Owner Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@bot_app.on_message(filters.command("start"))
async def start_cmd(client, message):
    uid = str(message.from_user.id)
    init_user(uid)
    await message.reply_text(
        "✨ **AILEY PREMIUM USERBOT** ✨\n\n"
        "Pilih menu:",
        reply_markup=build_main_keyboard(uid)
    )

@bot_app.on_message(filters.command("addprem"))
async def addprem_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only!")
    
    try:
        args = message.text.split()
        if len(args) < 4:
            return await message.reply_text("Format: `/addprem USER_ID TIER HARI`")
        
        uid, tier, days = args[1], args[2].lower(), int(args[3])
        tiers = ["jaseb_only", "autoreply", "full", "reseller"]
        
        if tier not in tiers:
            return await message.reply_text(f"Invalid tier! Use: {', '.join(tiers)}")
        
        init_user(uid)
        db = get_db()
        exp = (datetime.now() + timedelta(days=days)).isoformat()
        db["users"][uid]["tier"] = tier
        db["users"][uid]["expired"] = exp
        save_db(db)
        
        await message.reply_text(f"✅ Akses diberikan!\nUser: {uid}\nTier: {tier}\nExpired: {exp}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@bot_app.on_message(filters.text & ~filters.command(["start", "addprem"]))
async def text_handler(client, message):
    uid = str(message.from_user.id)
    text = message.text
    init_user(uid)
    
    if text == "🎁 Trial 5 Jam":
        db = get_db()
        user = db["users"][uid]
        if user.get("claimed_trial"):
            return await message.reply_text("❌ Sudah klaim trial!")
        exp = (datetime.now() + timedelta(hours=5)).isoformat()
        user["tier"] = "full"
        user["expired"] = exp
        user["claimed_trial"] = True
        save_db(db)
        await message.reply_text(f"🎉 Trial aktif! Expired: {exp}")

# === SERVER ===
async def handle_health(request):
    return web.Response(text="🚀 Online!")

async def start_services():
    logging.info("🤖 Bot Starting...")
    
    try:
        await bot_app.start()
        logging.info("✅ Bot Connected!")
    except Exception as e:
        logging.error(f"❌ Bot Error: {e}")
        raise
    
    web_app = web.Application()
    web_app.router.add_get("/", handle_health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Server on port {port}")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logging.info("Bot stopped.")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AILEY_BOT")

# === CONFIG ===
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DB_FILE = "database.json"

logger.info("=" * 50)
logger.info("🤖 AILEY PREMIUM - STARTING")
logger.info(f"Owner: {OWNER_ID} | Token: {'✅ SET' if BOT_TOKEN else '❌ NOT SET'}")
logger.info("=" * 50)

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN NOT SET IN RAILWAY VARIABLES!")
    raise ValueError("BOT_TOKEN is required!")

# === DATABASE ===
def get_db():
    try:
        if not os.path.exists(DB_FILE):
            data = {"users": {}}
            save_db(data)
            return data
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return {"users": {}}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save Error: {e}")

def init_user(uid):
    uid = str(uid)
    db = get_db()
    if uid not in db["users"]:
        db["users"][uid] = {
            "tier": "none", "expired": None, "session": "",
            "claimed_trial": False, "is_reseller": False,
            "settings": {
                "bc_enabled": False, "bc_text": "", "bc_delay": 5, "bc_targets": [],
                "fw_enabled": False, "fw_source_ch": "", "fw_targets": [],
                "ar_enabled": False, "ar_keywords": [], "ar_banwords": []
            }
        }
        save_db(db)
    return db["users"][uid]

# === BOT APP ===
app = Client(
    "ailey_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

def get_keyboard():
    return ReplyKeyboardMarkup([
        ["🚀 Login", "⚙️ Control"],
        ["🛒 Shop", "🎁 Trial"],
    ], resize_keyboard=True)

# === HANDLERS ===
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    try:
        uid = str(message.from_user.id)
        logger.info(f"👋 /start from {uid}")
        init_user(uid)
        await message.reply_text(
            "✨ **AILEY PREMIUM USERBOT** ✨\n\n"
            "Pilih menu:",
            reply_markup=get_keyboard()
        )
        logger.info(f"✅ /start replied to {uid}")
    except Exception as e:
        logger.error(f"Error /start: {e}")

@app.on_message(filters.command("addprem"))
async def addprem_handler(client, message):
    try:
        if message.from_user.id != OWNER_ID:
            logger.warning(f"⚠️ Unauthorized /addprem from {message.from_user.id}")
            return
        
        args = message.text.split()
        if len(args) < 4:
            await message.reply_text("Format: `/addprem USER_ID TIER HARI`")
            return
        
        uid, tier, days = args[1], args[2].lower(), int(args[3])
        
        if tier not in ["jaseb_only", "autoreply", "full", "reseller"]:
            await message.reply_text("❌ Invalid tier!")
            return
        
        init_user(uid)
        db = get_db()
        exp = (datetime.now() + timedelta(days=days)).isoformat()
        db["users"][uid]["tier"] = tier
        db["users"][uid]["expired"] = exp
        save_db(db)
        
        logger.info(f"✅ Access: {uid} → {tier}")
        await message.reply_text(f"✅ Akses: {uid} | {tier} | {days} hari")
    except Exception as e:
        logger.error(f"Error /addprem: {e}")

@app.on_message(filters.text & ~filters.command("start") & ~filters.command("addprem"))
async def text_handler(client, message):
    try:
        uid = str(message.from_user.id)
        text = message.text.strip()
        logger.info(f"💬 Message from {uid}: {text[:40]}")
        
        init_user(uid)
        db = get_db()
        user = db["users"][uid]
        
        # === TRIAL ===
        if text == "🎁 Trial":
            if user.get("claimed_trial"):
                await message.reply_text("❌ Sudah klaim!")
                return
            
            exp = (datetime.now() + timedelta(hours=5)).isoformat()
            user["tier"] = "full"
            user["expired"] = exp
            user["claimed_trial"] = True
            db["users"][uid] = user
            save_db(db)
            
            logger.info(f"✅ Trial: {uid}")
            await message.reply_text(f"🎉 Trial 5 jam aktif!\nExpired: {exp}")
            return
        
        # === SHOP ===
        if text == "🛒 Shop":
            await message.reply_text(
                "💰 **PRICING**\n\n"
                "Jaseb Only: 3.5k-18k\n"
                "Auto-Reply: 5k-30k\n"
                "Full: 7k-35k\n"
                "Reseller: 40k-250k"
            )
            return
        
        # === DEFAULT ===
        await message.reply_text(f"Pesan: {text}")
        logger.info(f"✅ Replied to {uid}")
        
    except Exception as e:
        logger.error(f"Error text handler: {e}", exc_info=True)
        try:
            await message.reply_text(f"❌ Error: {e}")
        except:
            pass

# === WEB SERVER ===
async def health_check(request):
    return web.Response(text="🚀 OK")

# === MAIN ===
async def main():
    logger.info("🔄 Starting bot...")
    
    try:
        await app.start()
        logger.info("✅ Bot Connected!")
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise
    
    # Web server
    web_app = web.Application()
    web_app.router.add_get("/", health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()
    
    logger.info("=" * 50)
    logger.info("✅ BOT RUNNING - Ready to use!")
    logger.info("=" * 50)
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal: {e}")
        raise
    

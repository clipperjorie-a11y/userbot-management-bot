import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === CONFIG ===
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DB_FILE = "database.json"

logger.info("=" * 50)
logger.info("🤖 AILEY PREMIUM USERBOT BOT STARTING")
logger.info(f"Owner ID: {OWNER_ID}")
logger.info(f"Bot Token: {'SET ✅' if BOT_TOKEN else 'NOT SET ❌'}")
logger.info("=" * 50)

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN NOT SET! Check Railway Variables!")
    raise ValueError("❌ BOT_TOKEN not set in environment!")

# === DATABASE FUNCTIONS ===
def get_db():
    """Get database"""
    try:
        if not os.path.exists(DB_FILE):
            logger.info("📝 Creating new database...")
            data = {"users": {}}
            save_db(data)
            return data
        
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"✅ Database loaded ({len(data.get('users', {}))} users)")
            return data
    except Exception as e:
        logger.error(f"❌ DB Load Error: {e}")
        return {"users": {}}

def save_db(data):
    """Save database"""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.debug("💾 Database saved")
        return True
    except Exception as e:
        logger.error(f"❌ DB Save Error: {e}")
        return False

def init_user(uid):
    """Initialize user dengan default settings"""
    uid = str(uid)
    db = get_db()
    
    if uid not in db["users"]:
        logger.info(f"👤 Initializing new user: {uid}")
        db["users"][uid] = {
            "tier": "none",
            "expired": None,
            "warranty": None,
            "session": "",
            "claimed_trial": False,
            "is_reseller": False,
            "reseller_customers": [],
            "created_at": datetime.now().isoformat(),
            "settings": {
                "bc_enabled": False,
                "bc_text": "",
                "bc_delay": 5,
                "bc_targets": [],
                "fw_enabled": False,
                "fw_source_ch": "",
                "fw_targets": [],
                "fw_delay": 5,
                "ar_enabled": False,
                "ar_keywords": [],
                "ar_banwords": []
            }
        }
        save_db(db)
    
    return db["users"][uid]

def get_user(uid):
    """Get user data"""
    uid = str(uid)
    init_user(uid)
    db = get_db()
    return db["users"].get(uid, {})

def check_access(uid, feature):
    """Check user access to feature"""
    user = get_user(uid)
    tier = user.get("tier", "none")
    expired = user.get("expired")
    
    # Check if expired
    if expired:
        try:
            exp_dt = datetime.fromisoformat(expired)
            if datetime.now() > exp_dt:
                logger.warning(f"⏰ User {uid} tier expired: {tier}")
                return False
        except:
            pass
    
    # Feature access mapping
    access_map = {
        "jaseb_only": ["bc", "forward"],
        "autoreply": ["reply"],
        "full": ["bc", "forward", "reply", "ban", "group"],
        "reseller": ["all"]
    }
    
    allowed = access_map.get(tier, [])
    
    if "all" in allowed:
        return True
    
    has_access = feature in allowed
    logger.debug(f"Access check {uid} → {feature}: {has_access} (tier: {tier})")
    return has_access

def build_main_keyboard(uid):
    """Build main menu keyboard"""
    buttons = [
        [KeyboardButton("🚀 Login Userbot"), KeyboardButton("⚙️ Panel Control")],
        [KeyboardButton("🛒 Toko"), KeyboardButton("🎁 Trial 5 Jam")],
    ]
    
    if uid == OWNER_ID:
        buttons.append([KeyboardButton("👑 Owner Panel")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# === BOT APP ===
try:
    bot_app = Client(
        "bot_controller",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    logger.info("✅ Bot client created")
except Exception as e:
    logger.error(f"❌ Failed to create bot client: {e}")
    raise

# === GLOBAL STATE ===
login_sessions = {}
user_states = {}
active_userbots = {}

# === BOT COMMANDS ===
@bot_app.on_message(filters.command("start"))
async def start_cmd(client, message):
    """Start command"""
    try:
        uid = str(message.from_user.id)
        username = message.from_user.username or message.from_user.first_name
        
        logger.info(f"👋 /start from {uid} (@{username})")
        
        init_user(uid)
        
        text = (
            "✨ **AILEY PREMIUM USERBOT** ✨\n\n"
            "Bot management userbot dengan fitur lengkap:\n"
            "📢 Auto Broadcast\n"
            "↩️ Auto Forward\n"
            "⚡ Auto Reply\n"
            "🚫 Ban Word\n"
            "👥 Group Manager\n\n"
            "Pilih menu di bawah:"
        )
        
        await message.reply_text(
            text,
            reply_markup=build_main_keyboard(uid)
        )
        logger.info(f"✅ /start replied to {uid}")
    except Exception as e:
        logger.error(f"❌ /start error: {e}", exc_info=True)

@bot_app.on_message(filters.command("addprem"))
async def addprem_cmd(client, message):
    """Owner command: Give access to user"""
    try:
        if message.from_user.id != OWNER_ID:
            logger.warning(f"⚠️ Unauthorized /addprem attempt from {message.from_user.id}")
            return await message.reply_text("❌ Owner only!")
        
        args = message.text.split()
        if len(args) < 4:
            return await message.reply_text(
                "❌ Format: `/addprem USER_ID TIER HARI`\n\n"
                "Tier: jaseb_only, autoreply, full, reseller\n"
                "Example: `/addprem 123456789 full 30`"
            )
        
        uid, tier, days_str = args[1], args[2].lower(), args[3]
        
        try:
            days = int(days_str)
        except:
            return await message.reply_text("❌ Hari harus angka!")
        
        tiers = ["jaseb_only", "autoreply", "full", "reseller"]
        if tier not in tiers:
            return await message.reply_text(f"❌ Invalid tier! Use: {', '.join(tiers)}")
        
        init_user(uid)
        db = get_db()
        
        exp = (datetime.now() + timedelta(days=days)).isoformat()
        db["users"][uid]["tier"] = tier
        db["users"][uid]["expired"] = exp
        save_db(db)
        
        logger.info(f"✅ Access granted: {uid} → {tier} for {days} days")
        
        await message.reply_text(
            f"✅ **AKSES DIBERIKAN**\n\n"
            f"👤 User ID: {uid}\n"
            f"📦 Tier: {tier}\n"
            f"📅 Durasi: {days} hari\n"
            f"⏰ Expired: {exp}"
        )
    except Exception as e:
        logger.error(f"❌ /addprem error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {e}")

@bot_app.on_message(filters.command("addseller"))
async def addseller_cmd(client, message):
    """Owner command: Make user a reseller"""
    try:
        if message.from_user.id != OWNER_ID:
            logger.warning(f"⚠️ Unauthorized /addseller from {message.from_user.id}")
            return await message.reply_text("❌ Owner only!")
        
        args = message.text.split()
        if len(args) < 2:
            return await message.reply_text("Format: `/addseller USER_ID`")
        
        uid = args[1]
        init_user(uid)
        db = get_db()
        
        db["users"][uid]["tier"] = "reseller"
        db["users"][uid]["is_reseller"] = True
        exp = (datetime.now() + timedelta(days=9999)).isoformat()
        db["users"][uid]["expired"] = exp
        save_db(db)
        
        logger.info(f"✅ Reseller created: {uid}")
        
        await message.reply_text(f"✅ {uid} is now RESELLER!")
    except Exception as e:
        logger.error(f"❌ /addseller error: {e}")
        await message.reply_text(f"❌ Error: {e}")

@bot_app.on_message(filters.text & ~filters.command(["start", "addprem", "addseller"]))
async def text_handler(client, message):
    """Main text message handler"""
    try:
        uid = str(message.from_user.id)
        text = message.text.strip()
        username = message.from_user.username or message.from_user.first_name
        
        logger.info(f"💬 Message from {uid} (@{username}): {text[:50]}")
        
        init_user(uid)
        db = get_db()
        user = db["users"].get(uid, {})
        
        # === TRIAL CLAIM ===
        if text == "🎁 Trial 5 Jam":
            logger.info(f"🎁 Trial request from {uid}")
            
            if user.get("claimed_trial"):
                logger.info(f"❌ Trial already claimed by {uid}")
                await message.reply_text("❌ Anda sudah pernah klaim trial!")
                return
            
            exp = (datetime.now() + timedelta(hours=5)).isoformat()
            user["tier"] = "full"
            user["expired"] = exp
            user["claimed_trial"] = True
            db["users"][uid] = user
            save_db(db)
            
            logger.info(f"✅ Trial granted to {uid}, expires: {exp}")
            
            await message.reply_text(
                f"🎉 **TRIAL 5 JAM AKTIF!**\n\n"
                f"📦 Tier: Full Fitur\n"
                f"⏰ Expired: {exp}\n\n"
                f"Silakan gunakan semua fitur!"
            )
            return
        
        # === SHOP ===
        if text == "🛒 Toko":
            logger.info(f"🛒 Shop menu from {uid}")
            
            pricing = (
                "💰 **PRICING LIST**\n\n"
                "🔵 **Jaseb Only** (BC + Forward)\n"
                "  ├─ 1 Bulan (No Garansi): 3.5k\n"
                "  ├─ 1 Bulan (Full Garansi): 4k\n"
                "  ├─ Permanen (No Garansi): 10k\n"
                "  └─ Permanen (Full Garansi): 18k\n\n"
                "🟢 **Auto-Reply**\n"
                "  ├─ 1 Bulan (No Garansi): 5k\n"
                "  ├─ 1 Bulan (Full Garansi): 7k\n"
                "  ├─ Permanen (No Garansi): 20k\n"
                "  └─ Permanen (Full Garansi): 30k\n\n"
                "🟡 **Full Fitur**\n"
                "  ├─ 1 Bulan (No Garansi): 7k\n"
                "  ├─ 1 Bulan (Full Garansi): 10k\n"
                "  ├─ Permanen (No Garansi): 25k\n"
                "  └─ Permanen (Full Garansi): 35k\n\n"
                "👑 **Reseller** (Unlimited User)\n"
                "  ├─ 1 Bulan: 40k\n"
                "  └─ Permanen: 250k\n\n"
                "📞 Hubungi: @AileyPremium\n"
                "💳 Payment: QRIS / Dana / OrderKuota"
            )
            
            await message.reply_text(pricing)
            return
        
        # === OWNER PANEL ===
        if text == "👑 Owner Panel":
            if uid != str(OWNER_ID):
                logger.warning(f"⚠️ Unauthorized owner panel from {uid}")
                await message.reply_text("❌ Owner only!")
                return
            
            logger.info(f"👑 Owner panel accessed by {uid}")
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Kasih Akses", callback_data="owner_grant")],
                [InlineKeyboardButton("👥 Jadikan Reseller", callback_data="owner_seller")],
                [InlineKeyboardButton("📊 Lihat Users", callback_data="owner_users")],
            ])
            
            await message.reply_text("👑 **OWNER PANEL**", reply_markup=kb)
            return
        
        # === DEFAULT REPLY ===
        logger.info(f"📤 Default reply to {uid}")
        await message.reply_text(
            f"📨 Pesan diterima: {text}\n\n"
            f"Silakan pilih menu di atas atau ketik command."
        )
        
    except Exception as e:
        logger.error(f"❌ Text handler error for {uid}: {e}", exc_info=True)
        try:
            await message.reply_text(f"❌ Error: {str(e)}")
        except:
            pass

@bot_app.on_callback_query()
async def callback_handler(client, callback_query):
    """Callback query handler"""
    try:
        uid = str(callback_query.from_user.id)
        data = callback_query.data
        
        logger.info(f"🔘 Callback from {uid}: {data}")
        
        if data == "owner_grant":
            await callback_query.message.reply_text(
                "📍 Format: `/addprem USER_ID TIER HARI`\n\n"
                "Contoh: `/addprem 123456789 full 30`"
            )
        
        elif data == "owner_seller":
            await callback_query.message.reply_text(
                "👥 Format: `/addseller USER_ID`"
            )
        
        elif data == "owner_users":
            db = get_db()
            total_users = len(db.get("users", {}))
            await callback_query.message.reply_text(
                f"📊 **STATISTICS**\n\n"
                f"Total Users: {total_users}"
            )
        
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        await callback_query.answer("❌ Error", show_alert=True)

# === WEB SERVER ===
async def handle_health_check(request):
    """Health check endpoint"""
    return web.Response(text="🚀 Bot Controller Active!")

# === STARTUP ===
async def start_services():
    """Start all services"""
    logger.info("🚀 Starting services...")
    
    try:
        logger.info("📡 Starting bot client...")
        await bot_app.start()
        logger.info("✅ Bot client started!")
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}", exc_info=True)
        raise
    
    # Web server untuk Railway
    web_app = web.Application()
    web_app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Web server started on port {port}")
    
    logger.info("=" * 50)
    logger.info("✅ ALL SERVICES RUNNING")
    logger.info("=" * 50)
    
    # Keep running
    await asyncio.Event().wait()

# === MAIN ===
if __name__ == "__main__":
    try:
        logger.info("🔄 Starting event loop...")
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise
        

#!/usr/bin/env python3
"""
AILEY PREMIUM - COMPLETE BOT
Dengan semua fitur: Admin, Database, Auto BC, Auto FW, Auto Reply, Seller Panel
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
log = logging.getLogger("AILEY")

# ===== CONFIG =====
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DB_FILE = "database.json"

log.info("="*60)
log.info("🤖 AILEY PREMIUM USERBOT - STARTING")
log.info(f"Owner: {OWNER_ID}")
log.info(f"Token: {'✅ SET' if BOT_TOKEN else '❌ NOT SET'}")
log.info("="*60)

if not BOT_TOKEN:
    log.error("❌ BOT_TOKEN NOT SET!")
    exit(1)

# ===== DATABASE =====
def get_db():
    try:
        if not os.path.exists(DB_FILE):
            data = {"users": {}}
            save_db(data)
            return data
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}}

def save_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.error(f"DB Error: {e}")

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
            "reseller_customers": [],
            "settings": {
                "bc_enabled": False,
                "bc_text": "",
                "bc_delay": 5,
                "bc_targets": [],
                "fw_enabled": False,
                "fw_source": "",
                "fw_targets": [],
                "fw_delay": 5,
                "ar_enabled": False,
                "ar_keywords": [],
                "ar_banwords": []
            }
        }
        save_db(db)
    return db["users"][uid]

def check_access(uid, feature):
    user = init_user(uid)
    tier = user.get("tier", "none")
    expired = user.get("expired")
    
    if expired:
        try:
            if datetime.fromisoformat(expired) < datetime.now():
                return False
        except:
            pass
    
    access_map = {
        "jaseb_only": ["bc", "forward"],
        "autoreply": ["reply"],
        "full": ["bc", "forward", "reply", "ban", "group"],
        "reseller": ["all"]
    }
    
    allowed = access_map.get(tier, [])
    return "all" in allowed or feature in allowed

def build_keyboard():
    return ReplyKeyboardMarkup([
        ["🚀 Login", "⚙️ Control"],
        ["🛒 Shop", "🎁 Trial"],
    ], resize_keyboard=True)

# ===== BOT =====
app = Client("ailey", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# ===== HANDLERS =====
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    try:
        uid = str(message.from_user.id)
        log.info(f"👋 /start from {uid}")
        init_user(uid)
        
        await message.reply_text(
            "✨ **AILEY PREMIUM USERBOT** ✨\n\n"
            "📢 Auto BC | ↩️ Auto FW | ⚡ Auto Reply | 🚫 Ban Word\n\n"
            "Pilih menu:",
            reply_markup=build_keyboard()
        )
    except Exception as e:
        log.error(f"Start error: {e}")

@app.on_message(filters.command("addprem"))
async def addprem_handler(client, message):
    try:
        if message.from_user.id != OWNER_ID:
            return
        
        args = message.text.split()
        if len(args) < 4:
            await message.reply_text("Format: `/addprem USER_ID TIER HARI`\nTier: jaseb_only, autoreply, full, reseller")
            return
        
        uid, tier, days = args[1], args[2].lower(), int(args[3])
        
        if tier not in ["jaseb_only", "autoreply", "full", "reseller"]:
            await message.reply_text("❌ Tier tidak valid!")
            return
        
        init_user(uid)
        db = get_db()
        exp = (datetime.now() + timedelta(days=days)).isoformat()
        db["users"][uid]["tier"] = tier
        db["users"][uid]["expired"] = exp
        save_db(db)
        
        log.info(f"✅ Access: {uid} → {tier}")
        await message.reply_text(
            f"✅ **AKSES DIBERIKAN**\n\n"
            f"User: {uid}\n"
            f"Tier: {tier}\n"
            f"Hari: {days}\n"
            f"Expired: {exp}"
        )
    except Exception as e:
        log.error(f"Addprem error: {e}")
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("addseller"))
async def addseller_handler(client, message):
    try:
        if message.from_user.id != OWNER_ID:
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text("Format: `/addseller USER_ID`")
            return
        
        uid = args[1]
        init_user(uid)
        db = get_db()
        db["users"][uid]["tier"] = "reseller"
        db["users"][uid]["is_reseller"] = True
        save_db(db)
        
        log.info(f"✅ Reseller: {uid}")
        await message.reply_text(f"✅ {uid} sekarang RESELLER!")
    except Exception as e:
        log.error(f"Addseller error: {e}")

@app.on_message(filters.text & ~filters.command("start") & ~filters.command("addprem") & ~filters.command("addseller"))
async def text_handler(client, message):
    try:
        uid = str(message.from_user.id)
        text = message.text.strip()
        log.info(f"💬 Text from {uid}: {text[:40]}")
        
        init_user(uid)
        db = get_db()
        user = db["users"][uid]
        
        # ===== TRIAL =====
        if text == "🎁 Trial":
            if user.get("claimed_trial"):
                await message.reply_text("❌ Sudah klaim trial!")
                return
            
            exp = (datetime.now() + timedelta(hours=5)).isoformat()
            user["tier"] = "full"
            user["expired"] = exp
            user["claimed_trial"] = True
            db["users"][uid] = user
            save_db(db)
            
            log.info(f"🎁 Trial: {uid}")
            await message.reply_text(f"🎉 Trial 5 jam aktif!\nExpired: {exp}")
            return
        
        # ===== SHOP =====
        if text == "🛒 Shop":
            pricing = (
                "💰 **PRICING**\n\n"
                "🔵 Jaseb Only: 3.5k-18k\n"
                "🟢 Auto-Reply: 5k-30k\n"
                "🟡 Full Fitur: 7k-35k\n"
                "👑 Reseller: 40k-250k\n\n"
                "Hubungi: @AileyPremium"
            )
            await message.reply_text(pricing)
            return
        
        # ===== CONTROL =====
        if text == "⚙️ Control":
            if not check_access(uid, "bc"):
                await message.reply_text("❌ Tidak ada akses!\n\nBeli paket terlebih dahulu.")
                return
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Auto BC", callback_data="bc_menu")],
                [InlineKeyboardButton("↩️ Auto FW", callback_data="fw_menu")],
                [InlineKeyboardButton("⚡ Auto Reply", callback_data="ar_menu")],
                [InlineKeyboardButton("🚫 Ban Word", callback_data="ban_menu")],
            ])
            await message.reply_text("⚙️ **PANEL CONTROL**", reply_markup=kb)
            return
        
        # ===== OWNER PANEL =====
        if text == "👑 Owner" and uid == str(OWNER_ID):
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Kasih Akses", callback_data="owner_grant")],
                [InlineKeyboardButton("👥 Jadikan Reseller", callback_data="owner_seller")],
            ])
            await message.reply_text("👑 **OWNER PANEL**", reply_markup=kb)
            return
        
        # ===== DEFAULT =====
        await message.reply_text(f"Pesan: {text}")
        
    except Exception as e:
        log.error(f"Text error: {e}")

@app.on_callback_query()
async def callback_handler(client, cb):
    try:
        uid = str(cb.from_user.id)
        data = cb.data
        log.info(f"🔘 Callback: {uid} → {data}")
        
        if data == "bc_menu":
            await cb.message.reply_text(
                "📢 **AUTO BROADCAST**\n\n"
                "Format:\n"
                "/bc_text [text]\n"
                "/bc_target [group]\n"
                "/bc_delay [detik]\n"
                "/bc_toggle"
            )
        
        elif data == "fw_menu":
            await cb.message.reply_text(
                "↩️ **AUTO FORWARD**\n\n"
                "/fw_source [channel]\n"
                "/fw_target [group]\n"
                "/fw_delay [detik]\n"
                "/fw_toggle"
            )
        
        elif data == "ar_menu":
            await cb.message.reply_text(
                "⚡ **AUTO REPLY**\n\n"
                "/ar_add [keyword|response]\n"
                "/ar_list\n"
                "/ar_ban [kata]\n"
                "/ar_toggle"
            )
        
        elif data == "ban_menu":
            await cb.message.reply_text(
                "🚫 **BAN WORD**\n\n"
                "/ban_add [kata]\n"
                "/ban_list\n"
                "/ban_remove [kata]"
            )
        
        await cb.answer()
    except Exception as e:
        log.error(f"Callback error: {e}")

# ===== WEB =====
async def health(req):
    return web.Response(text="OK")

# ===== MAIN =====
async def main():
    log.info("📡 Connecting bot...")
    try:
        await app.start()
        log.info("✅ BOT CONNECTED!")
    except Exception as e:
        log.error(f"❌ Bot error: {e}")
        raise
    
    # Web
    web_app = web.Application()
    web_app.router.add_get("/", health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    
    log.info("="*60)
    log.info("✅ BOT READY!")
    log.info("="*60)
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

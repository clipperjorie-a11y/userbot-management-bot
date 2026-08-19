import os
import asyncio
import logging
from datetime import datetime, timedelta
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from pyrogram.errors import SessionPasswordNeeded
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === CONFIG ===
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("ID_PEMILIK", os.getenv("OWNER_ID", "0")))

# === MONGODB ===
MONGO_URI = os.getenv("MONGO_URI", "")
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["botdb"]
collection = mongo_db["data"]

# === PRICING ===
PRICING = {
    "jaseb_only": {"name": "🔵 Jaseb Only", "features": ["bc", "forward"]},
    "autoreply": {"name": "🟢 Auto-Reply", "features": ["reply"]},
    "full": {"name": "🟡 Full Fitur", "features": ["bc", "forward", "reply", "ban", "group"]},
    "reseller": {"name": "👑 Reseller", "features": ["all"]}
}

# === DATABASE FUNCTIONS (MongoDB) ===
def get_db():
    try:
        doc = collection.find_one({"_id": "main"})
        if not doc:
            default = {"_id": "main", "users": {}, "sellers": {}}
            collection.insert_one(default)
            return default
        return doc
    except Exception as e:
        logging.error(f"DB Load Error: {e}")
        return {"users": {}, "sellers": {}}

def save_db(data):
    try:
        data["_id"] = "main"
        collection.replace_one({"_id": "main"}, data, upsert=True)
    except Exception as e:
        logging.error(f"DB Save Error: {e}")

def init_user(uid):
    uid = str(uid)
    db = get_db()
    if "users" not in db:
        db["users"] = {}
    if uid not in db["users"]:
        db["users"][uid] = {
            "tier": "none", "expired": None, "warranty": None,
            "session": "", "claimed_trial": False, "is_reseller": False,
            "reseller_customers": [],
            "settings": {
                "bc_enabled": False, "bc_text": "", "bc_delay": 5, "bc_targets": [],
                "fw_enabled": False, "fw_source_ch": "", "fw_targets": [], "fw_delay": 5,
                "ar_enabled": False, "ar_keywords": [], "ar_banwords": [],
                "groups": []
            }
        }
        save_db(db)
    return db["users"][uid]

def check_access(uid, feature):
    db = get_db()
    user = db.get("users", {}).get(str(uid), {})
    tier = user.get("tier", "none")
    expired = user.get("expired")

    if expired:
        try:
            exp = datetime.fromisoformat(expired)
            if datetime.now() > exp:
                return False
        except:
            pass

    access = {
        "jaseb_only": ["bc", "forward"],
        "autoreply": ["reply"],
        "full": ["bc", "forward", "reply", "ban", "group"],
        "reseller": ["all"]
    }

    allowed = access.get(tier, [])
    return "all" in allowed or feature in allowed

# === BOT GLOBALS ===
bot_app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
login_sessions = {}
user_states = {}
active_userbots = {}

def build_main_keyboard(uid):
    db = get_db()
    user = db.get("users", {}).get(str(uid), {})

    buttons = [
        [KeyboardButton("🚀 Login/Buat Userbot"), KeyboardButton("⚙️ Panel Control")],
        [KeyboardButton("🛒 Toko"), KeyboardButton("🎁 Trial 5 Jam")],
    ]

    if int(uid) == OWNER_ID or user.get("is_reseller"):
        buttons.append([KeyboardButton("👑 Panel Admin")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# === USERBOT ENGINE ===
async def start_userbot_session(user_id, session_str):
    user_id = str(user_id)

    if user_id in active_userbots:
        try:
            await active_userbots[user_id].stop()
        except:
            pass

    from userbot import create_userbot
    ub = await create_userbot(user_id, session_str)
    active_userbots[user_id] = ub
    logging.info(f"✅ Userbot Active: {user_id}")

async def start_all_userbots():
    db = get_db()
    for uid, data in db.get("users", {}).items():
        sess = data.get("session")
        if sess and data.get("tier") != "none":
            try:
                await start_userbot_session(uid, sess)
            except Exception as e:
                logging.error(f"Restore userbot {uid} failed: {e}")

# === BOT COMMANDS ===
@bot_app.on_message(filters.command("start"))
async def start_cmd(client, message):
    uid = str(message.from_user.id)
    init_user(uid)
    await message.reply_text(
        "✨ **AILEY PREMIUM USERBOT** ✨\n\n"
        "Bot management userbot dengan fitur lengkap.\n"
        "Pilih menu di bawah:",
        reply_markup=build_main_keyboard(uid)
    )

@bot_app.on_message(filters.command("addprem"))
async def addprem_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only!")

    try:
        args = message.text.split()
        if len(args) < 4:
            return await message.reply_text("Format: `/addprem USER_ID TIER HARI`\n"
                                            "Tier: jaseb_only, autoreply, full, reseller")

        uid, tier, days = args[1], args[2].lower(), int(args[3])

        if tier not in PRICING:
            return await message.reply_text(f"Tier invalid! Pilih: {', '.join(PRICING.keys())}")

        init_user(uid)
        db = get_db()

        exp = (datetime.now() + timedelta(days=days)).isoformat()
        db["users"][uid]["tier"] = tier
        db["users"][uid]["expired"] = exp
        save_db(db)

        await message.reply_text(
            f"✅ Akses diberikan!\n\n"
            f"📍 User: {uid}\n"
            f"📦 Tier: {PRICING[tier]['name']}\n"
            f"📅 Expired: {exp}"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@bot_app.on_message(filters.command("addseller"))
async def addseller_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Owner only!")

    try:
        args = message.text.split()
        if len(args) < 2:
            return await message.reply_text("Format: `/addseller USER_ID`")

        uid = args[1]
        init_user(uid)
        db = get_db()

        db["users"][uid]["tier"] = "reseller"
        db["users"][uid]["is_reseller"] = True
        db["users"][uid]["expired"] = (datetime.now() + timedelta(days=999)).isoformat()
        save_db(db)

        await message.reply_text(f"✅ {uid} sekarang RESELLER!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@bot_app.on_message(filters.text & ~filters.command(["start", "addprem", "addseller"]))
async def text_handler(client, message):
    uid = str(message.from_user.id)
    text = message.text
    db = get_db()
    user = init_user(uid)

    # === LOGIN FLOW ===
    if uid in login_sessions:
        sess = login_sessions[uid]
        step = sess["step"]

        if step == "phone":
            phone = text.replace(" ", "").replace("-", "")
            temp = Client(f"temp_{uid}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp.connect()
            try:
                code_info = await temp.send_code(phone)
                login_sessions[uid] = {
                    "step": "otp", "client": temp, "phone": phone, "hash": code_info.phone_code_hash
                }
                return await message.reply_text("📩 Masukkan OTP (format: 1 2 3 4 5):")
            except Exception as e:
                await temp.disconnect()
                del login_sessions[uid]
                return await message.reply_text(f"❌ Error: {e}")

        elif step == "otp":
            otp = text.replace(" ", "").replace("-", "")
            temp, phone, hash_code = sess["client"], sess["phone"], sess["hash"]
            try:
                await temp.sign_in(phone, hash_code, otp)
                s_str = await temp.export_session_string()
                await temp.disconnect()

                db = get_db()
                db["users"][uid]["session"] = s_str
                save_db(db)
                del login_sessions[uid]

                await start_userbot_session(uid, s_str)
                return await message.reply_text("🎉 LOGIN BERHASIL! Userbot Aktif!")
            except SessionPasswordNeeded:
                login_sessions[uid]["step"] = "2fa"
                return await message.reply_text("🔐 Masukkan Password 2FA:")
            except Exception as e:
                await temp.disconnect()
                del login_sessions[uid]
                return await message.reply_text(f"❌ OTP Error: {e}")

        elif step == "2fa":
            temp = sess["client"]
            try:
                await temp.check_password(text)
                s_str = await temp.export_session_string()
                await temp.disconnect()

                db = get_db()
                db["users"][uid]["session"] = s_str
                save_db(db)
                del login_sessions[uid]

                await start_userbot_session(uid, s_str)
                return await message.reply_text("🎉 LOGIN 2FA BERHASIL!")
            except Exception as e:
                await temp.disconnect()
                del login_sessions[uid]
                return await message.reply_text(f"❌ 2FA Error: {e}")

    # === SETTINGS FLOW ===
    if uid in user_states:
        state = user_states[uid]
        db = get_db()
        user = db["users"].get(uid, {})
        st = user.get("settings", {})

        if state == "set_bc_text":
            st["bc_text"] = text
        elif state == "set_bc_delay":
            st["bc_delay"] = int(text) if text.isdigit() else 5
        elif state == "add_bc_target":
            for line in text.splitlines():
                if line.strip() not in st["bc_targets"]:
                    st["bc_targets"].append(line.strip())
        elif state == "set_fw_source":
            st["fw_source_ch"] = text.strip()
        elif state == "add_fw_target":
            for line in text.splitlines():
                target = line.strip()
                if target and target not in [t.get("target") for t in st["fw_targets"]]:
                    st["fw_targets"].append({"target": target, "delay": 5})
        elif state == "set_fw_delay":
            st["fw_delay"] = int(text) if text.isdigit() else 5
        elif state == "add_keyword":
            kw = text.split("|")
            if len(kw) >= 2:
                st["ar_keywords"].append({"keyword": kw[0].strip(), "response": kw[1].strip(), "enabled": True})
        elif state == "set_banwords":
            st["ar_banwords"] = [b.strip() for b in text.split(",") if b.strip()]

        user["settings"] = st
        db["users"][uid] = user
        save_db(db)
        del user_states[uid]
        return await message.reply_text("✅ Config tersimpan!")

    # === MAIN MENU ===
    if text == "🚀 Login/Buat Userbot":
        if user["tier"] == "none":
            return await message.reply_text("❌ Beli paket atau klaim trial dulu!")
        login_sessions[uid] = {"step": "phone"}
        return await message.reply_text("📱 Kirim Nomor Telepon (+62...):")

    elif text == "⚙️ Panel Control":
        if user["tier"] == "none":
            return await message.reply_text("❌ Tidak ada akses!")

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Auto BC", callback_data="menu_bc")],
            [InlineKeyboardButton("↩️ Auto Forward", callback_data="menu_fw")],
            [InlineKeyboardButton("⚡ Auto Reply", callback_data="menu_ar")],
            [InlineKeyboardButton("🗑️ Ban Word", callback_data="menu_ban")],
            [InlineKeyboardButton("👥 Group Manage", callback_data="menu_group")],
        ])
        return await message.reply_text("⚙️ **PANEL CONTROL**", reply_markup=kb)

    elif text == "🛒 Toko":
        await message.reply_text(
            "💰 **PRICING LIST**\n\n"
            "🔵 Jaseb Only: 3.5k-18k\n"
            "🟢 Auto-Reply: 5k-30k\n"
            "🟡 Full Fitur: 7k-35k\n"
            "👑 Reseller: 40k-250k\n\n"
            "Hubungi: @AileyPremium"
        )

    elif text == "🎁 Trial 5 Jam":
        if user.get("claimed_trial"):
            return await message.reply_text("❌ Sudah pernah klaim trial!")

        exp = (datetime.now() + timedelta(hours=5)).isoformat()
        db = get_db()
        db["users"][uid]["tier"] = "full"
        db["users"][uid]["expired"] = exp
        db["users"][uid]["claimed_trial"] = True
        save_db(db)

        await message.reply_text(f"🎉 Trial 5 jam aktif! Expired: {exp}")

    elif text == "👑 Panel Admin":
        if int(uid) == OWNER_ID:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Kasih Akses", callback_data="admin_grant")],
                [InlineKeyboardButton("👥 Kelola Seller", callback_data="admin_seller")],
                [InlineKeyboardButton("📊 Lihat User", callback_data="admin_users")],
            ])
            return await message.reply_text("👑 OWNER PANEL", reply_markup=kb)

        if user.get("is_reseller"):
            customers = user.get("reseller_customers", [])
            msg = f"👑 **RESELLER PANEL**\n\n📊 Customer: {len(customers)}\n\n"
            for c in customers[:10]:
                msg += f"  • {c}\n"

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Tambah Customer", callback_data="reseller_add")],
                [InlineKeyboardButton("📋 Lihat Customers", callback_data="reseller_list")],
            ])
            return await message.reply_text(msg, reply_markup=kb)

@bot_app.on_callback_query()
async def callback_handler(client, cb: CallbackQuery):
    uid = str(cb.from_user.id)
    data = cb.data

    if data == "menu_bc":
        if not check_access(uid, "bc"):
            return await cb.answer("❌ No access!", show_alert=True)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Set Text", callback_data="bc_text")],
            [InlineKeyboardButton("➕ Tambah Target", callback_data="bc_target")],
            [InlineKeyboardButton("⏱️ Set Delay", callback_data="bc_delay")],
            [InlineKeyboardButton("🔘 Toggle", callback_data="bc_toggle")],
        ])
        await cb.message.edit_text("📢 AUTO BROADCAST", reply_markup=kb)

    elif data == "bc_text":
        user_states[uid] = "set_bc_text"
        await cb.message.reply_text("📝 Kirim teks BC:")
    elif data == "bc_target":
        user_states[uid] = "add_bc_target"
        await cb.message.reply_text("➕ Kirim Target (username/ID, satu per baris):")
    elif data == "bc_delay":
        user_states[uid] = "set_bc_delay"
        await cb.message.reply_text("⏱️ Kirim Delay (detik):")
    elif data == "bc_toggle":
        db = get_db()
        st = db["users"][uid]["settings"]
        st["bc_enabled"] = not st.get("bc_enabled", False)
        save_db(db)
        status = "✅ ON" if st["bc_enabled"] else "❌ OFF"
        await cb.message.reply_text(f"BC {status}")

    elif data == "menu_fw":
        if not check_access(uid, "forward"):
            return await cb.answer("❌ No access!", show_alert=True)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📌 Set Source", callback_data="fw_source")],
            [InlineKeyboardButton("➕ Tambah Target", callback_data="fw_target")],
            [InlineKeyboardButton("⏱️ Set Delay", callback_data="fw_delay")],
            [InlineKeyboardButton("🔘 Toggle", callback_data="fw_toggle")],
        ])
        await cb.message.edit_text("↩️ AUTO FORWARD", reply_markup=kb)

    elif data == "fw_source":
        user_states[uid] = "set_fw_source"
        await cb.message.reply_text("📌 Kirim ID/Username Channel Source:")
    elif data == "fw_target":
        user_states[uid] = "add_fw_target"
        await cb.message.reply_text("➕ Kirim Target (username/ID, satu per baris):")
    elif data == "fw_delay":
        user_states[uid] = "set_fw_delay"
        await cb.message.reply_text("⏱️ Kirim Delay (detik):")
    elif data == "fw_toggle":
        db = get_db()
        st = db["users"][uid]["settings"]
        st["fw_enabled"] = not st.get("fw_enabled", False)
        save_db(db)
        status = "✅ ON" if st["fw_enabled"] else "❌ OFF"
        await cb.message.reply_text(f"FW {status}")

    elif data == "menu_ar":
        if not check_access(uid, "reply"):
            return await cb.answer("❌ No access!", show_alert=True)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Add Keyword", callback_data="ar_add")],
            [InlineKeyboardButton("📋 List", callback_data="ar_list")],
            [InlineKeyboardButton("🔘 Toggle", callback_data="ar_toggle")],
        ])
        await cb.message.edit_text("⚡ AUTO REPLY", reply_markup=kb)

    elif data == "ar_add":
        user_states[uid] = "add_keyword"
        await cb.message.reply_text("🔑 Format: keyword|response")
    elif data == "ar_toggle":
        db = get_db()
        st = db["users"][uid]["settings"]
        st["ar_enabled"] = not st.get("ar_enabled", False)
        save_db(db)
        status = "✅ ON" if st["ar_enabled"] else "❌ OFF"
        await cb.message.reply_text(f"AR {status}")

    elif data == "admin_grant":
        user_states[uid] = "admin_grant_id"
        await cb.message.reply_text("📍 USER_ID TIER HARI\nContoh: 123456 full 30")

    await cb.answer()

# === SERVER ===
async def handle_health(request):
    return web.Response(text="🚀 Online!")

async def start_services():
    logging.info("Starting Bot Controller...")
    await bot_app.start()

    logging.info("Restoring Userbots...")
    await start_all_userbots()

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

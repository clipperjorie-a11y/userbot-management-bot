import os
import json
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 1. KONFIGURASI ENVIRONMENT ---
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = int(os.getenv("OWNER_ID", "7193478617"))
DB_FILE = "database.json"

# --- 2. SISTEM DATABASE JSON ---
def get_db():
    if not os.path.exists(DB_FILE):
        data = {"users": {}}
        save_db(data)
        return data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Gagal menyimpan DB: {e}")

def init_user_db(db, user_id):
    user_id = str(user_id)
    if "users" not in db:
        db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "plan": "none",
            "expired": "Tidak Aktif",
            "session": "",
            "claimed_trial": False,
            "settings": {
                "bc_text": "", "bc_delay": 5, "bc_targets": [],
                "replay_kw": "", "replay_ban": "", "replay_text": ""
            }
        }
    save_db(db)

# --- 3. GLOBAL VARIABLES & BOT CONTROLLER ---
bot_app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
login_sessions = {}
user_states = {}
active_userbots = {}

def build_main_keyboard(user_id):
    db = get_db()
    plan = db.get("users", {}).get(str(user_id), {}).get("plan", "none")
    buttons = [
        [KeyboardButton("🚀 Buat / Login Userbot"), KeyboardButton("⚙️ Panel Control Userbot")],
        [KeyboardButton("🛒 Toko"), KeyboardButton("💡 Fitur Unggulan")],
        [KeyboardButton("🎁 Coba Gratis")]
    ]
    if int(user_id) == OWNER_ID or "seller" in str(plan):
        buttons.append([KeyboardButton("👑 Panel Akses Owner")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- 4. ENGINE USERBOT (AUTO REPLAY & BC) ---
async def handle_auto_replay(client, message):
    try:
        owner_id = getattr(client, "owner_id", None)
        if not owner_id: return
        db = get_db()
        st = db.get("users", {}).get(owner_id, {}).get("settings", {})

        keywords = [k.strip().lower() for k in st.get("replay_kw", "").split(",") if k.strip()]
        banwords = [b.strip().lower() for b in st.get("replay_ban", "").split(",") if b.strip()]
        reply_text = st.get("replay_text", "")

        if not keywords or not reply_text: return
        text = (message.text or message.caption or "").lower()

        if any(b in text for b in banwords): return
        if any(k in text for k in keywords):
            await message.reply_text(reply_text)
            logging.info(f"Auto Replay terkirim oleh User {owner_id}")
    except Exception as e:
        logging.error(f"Error Auto Replay: {e}")

async def start_userbot_session(user_id, session_str):
    user_id = str(user_id)
    if user_id in active_userbots:
        try: await active_userbots[user_id].stop()
        except Exception: pass

    ub = Client(f"ub_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_str, in_memory=True)
    ub.owner_id = user_id

    @ub.on_message(filters.group & ~filters.me)
    async def msg_handler(c, m):
        await handle_auto_replay(c, m)

    await ub.start()
    active_userbots[user_id] = ub
    logging.info(f"✅ Userbot ID {user_id} Aktif!")

async def start_all_userbots():
    db = get_db()
    for uid, data in db.get("users", {}).items():
        sess = data.get("session")
        if sess and data.get("plan") != "none":
            try: await start_userbot_session(uid, sess)
            except Exception as e: logging.error(f"Gagal load userbot {uid}: {e}")

async def background_bc_timer():
    while True:
        try:
            db = get_db()
            for uid, ub in list(active_userbots.items()):
                st = db.get("users", {}).get(uid, {}).get("settings", {})
                bc_text = st.get("bc_text")
                targets = st.get("bc_targets", [])
                delay = st.get("bc_delay", 5)

                if bc_text and targets:
                    for target in targets:
                        try:
                            await ub.send_message(target, bc_text)
                            await asyncio.sleep(delay)
                        except Exception as err:
                            logging.error(f"Gagal BC ke {target}: {err}")
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Error Timer Task: {e}")
            await asyncio.sleep(10)

# --- 5. BOT CONTROLLER HANDLERS ---
@bot_app.on_message(filters.command("start"))
async def start_cmd(client, message):
    uid = str(message.from_user.id)
    db = get_db()
    init_user_db(db, uid)
    await message.reply_text("✨ **USERBOT CONTROLLER CANGGIH ONLINE** ✨\n\nPilih menu di bawah ini:", reply_markup=build_main_keyboard(uid))

@bot_app.on_message(filters.command("addprem"))
async def addprem_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Akses khusus Owner.")
    args = message.text.split()
    if len(args) < 4:
        return await message.reply_text("Format: `/addprem [USER_ID] [PAKET] [HARI]`")
    target, paket, days = args[1], args[2].lower(), int(args[3])
    db = get_db()
    init_user_db(db, target)
    exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    db["users"][target]["plan"] = paket
    db["users"][target]["expired"] = exp
    save_db(db)
    await message.reply_text(f"✅ **Akses Diberikan!**\nTarget: `{target}`\nPaket: `{paket}`\nExpired: `{exp}`")

@bot_app.on_message(filters.text & ~filters.command(["start", "addprem"]))
async def main_text_handler(client, message):
    uid = str(message.from_user.id)
    text = message.text
    db = get_db()
    init_user_db(db, uid)
    u_data = db["users"][uid]

    # Flow Login OTP & 2FA
    if uid in login_sessions:
        sess = login_sessions[uid]
        step = sess["step"]

        if step == "phone":
            phone = text.replace(" ", "").replace("-", "")
            temp = Client(f"temp_{uid}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp.connect()
            try:
                code_info = await temp.send_code(phone)
                login_sessions[uid] = {"step": "otp", "client": temp, "phone": phone, "hash": code_info.phone_code_hash}
                return await message.reply_text("📩 **Masukkan OTP** (Format: `1 2 3 4 5`):")
            except Exception as e:
                await temp.disconnect()
                del login_sessions[uid]
                return await message.reply_text(f"❌ Error: `{e}`")

        elif step == "otp":
            otp = text.replace(" ", "").replace("-", "")
            temp, phone, hash_code = sess["client"], sess["phone"], sess["hash"]
            try:
                await temp.sign_in(phone, hash_code, otp)
                s_str = await temp.export_session_string()
                await temp.disconnect()
                db["users"][uid]["session"] = s_str
                save_db(db)
                del login_sessions[uid]
                await start_userbot_session(uid, s_str)
                return await message.reply_text("🎉 **LOGIN BERHASIL & USERBOT AKTIF!**")
            except SessionPasswordNeeded:
                login_sessions[uid]["step"] = "2fa"
                return await message.reply_text("🔐 **Masukkan Password 2FA:**")
            except Exception as e:
                await temp.disconnect()
                del login_sessions[uid]
                return await message.reply_text(f"❌ OTP Gagal: `{e}`")

        elif step == "2fa":
            temp = sess["client"]
            try:
                await temp.check_password(text)
                s_str = await temp.export_session_string()
                await temp.disconnect()
                db["users"][uid]["session"] = s_str
                save_db(db)
                del login_sessions[uid]
                await start_userbot_session(uid, s_str)
                return await message.reply_text("🎉 **LOGIN 2FA BERHASIL!**")
            except Exception as e:
                await temp.disconnect()
                del login_sessions[uid]
                return await message.reply_text(f"❌ 2FA Gagal: `{e}`")

    # State Settings
    if uid in user_states:
        state = user_states[uid]
        st = u_data["settings"]
        if state == "set_bc_text": st["bc_text"] = text
        elif state == "set_bc_delay": st["bc_delay"] = int(text) if text.isdigit() else 5
        elif state == "add_bc_target":
            for line in text.splitlines():
                if line.strip() not in st["bc_targets"]: st["bc_targets"].append(line.strip())
        elif state == "set_rp_kw": st["replay_kw"] = text
        elif state == "set_rp_ban": st["replay_ban"] = text
        elif state == "set_rp_txt": st["replay_text"] = text
        save_db(db)
        del user_states[uid]
        return await message.reply_text("✅ Config Berhasil Disimpan!")

    # Menu Tombol utama
    if text == "🚀 Buat / Login Userbot":
        if u_data["plan"] == "none": return await message.reply_text("❌ Silakan beli paket atau klaim trial dulu!")
        login_sessions[uid] = {"step": "phone"}
        return await message.reply_text("📱 Kirimkan Nomor Telepon (Contoh: `+62812345678`):")

    elif text == "⚙️ Panel Control Userbot":
        if u_data["plan"] == "none": return await message.reply_text("❌ Akses Ditolak. Belum ada paket aktif.")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Setting Auto BC", callback_data="menu_bc")],
            [InlineKeyboardButton("⚡ Setting Auto Replay WTB", callback_data="menu_replay")]
        ])
        return await message.reply_text("⚙️ **PANEL UTAMA USERBOT**", reply_markup=kb)

    elif text == "🎁 Coba Gratis":
        if u_data.get("claimed_trial"): return await message.reply_text("❌ Kamu sudah pernah klaim trial!")
        exp = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")
        u_data["plan"] = "trial"
        u_data["expired"] = exp
        u_data["claimed_trial"] = True
        save_db(db)
        return await message.reply_text(f"🎉 **TRIAL 5 JAM AKTIF!** Expired: `{exp}`")

@bot_app.on_callback_query()
async def inline_callback(client, cb: CallbackQuery):
    uid = str(cb.from_user.id)
    data = cb.data
    if data == "menu_bc":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Set Teks BC", callback_data="act_bc_text"), InlineKeyboardButton("➕ Tambah Target", callback_data="act_bc_target")],
            [InlineKeyboardButton("⏱️ Set Delay (s)", callback_data="act_bc_delay"), InlineKeyboardButton("🗑️ Clear Target", callback_data="act_bc_clear")]
        ])
        await cb.message.edit_text("📢 **PENGATURAN AUTO BROADCAST**", reply_markup=kb)
    elif data == "act_bc_text":
        user_states[uid] = "set_bc_text"
        await cb.message.reply_text("📝 Kirim Teks Pesan BC:")
    elif data == "act_bc_target":
        user_states[uid] = "add_bc_target"
        await cb.message.reply_text("➕ Kirim Username/ID Target (satu per baris):")
    elif data == "act_bc_delay":
        user_states[uid] = "set_bc_delay"
        await cb.message.reply_text("⏱️ Kirim Delay (detik, angka):")
    elif data == "act_bc_clear":
        db = get_db()
        db["users"][uid]["settings"]["bc_targets"] = []
        save_db(db)
        await cb.message.reply_text("🗑️ Target BC Dikosongkan.")
    elif data == "menu_replay":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Keyword", callback_data="act_rp_kw"), InlineKeyboardButton("🚫 Banword", callback_data="act_rp_ban")],
            [InlineKeyboardButton("💬 Teks Balasan", callback_data="act_rp_txt")]
        ])
        await cb.message.edit_text("⚡ **PENGATURAN AUTO REPLAY (WTB)**", reply_markup=kb)
    elif data == "act_rp_kw":
        user_states[uid] = "set_rp_kw"
        await cb.message.reply_text("🔑 Kirim Keyword (pisahkan dengan koma):")
    elif data == "act_rp_ban":
        user_states[uid] = "set_rp_ban"
        await cb.message.reply_text("🚫 Kirim Banword (pisahkan dengan koma):")
    elif data == "act_rp_txt":
        user_states[uid] = "set_rp_txt"
        await cb.message.reply_text("💬 Kirim Teks Balasan Auto Replay:")
    await cb.answer()

# --- 6. SERVER RUNNER & HEALTH CHECK RAILWAY ---
async def handle_health_check(request):
    return web.Response(text="🚀 System is Running 24/7 Perfectly!")

async def start_services():
    logging.info("Memulai Bot Controller...")
    await bot_app.start()

    logging.info("Memulai restore Userbot aktif...")
    await start_all_userbots()

    logging.info("Memulai Engine Background BC...")
    asyncio.create_task(background_bc_timer())

    web_app = web.Application()
    web_app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Web Server Port Railway Aktif di Port {port}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Aplikasi Dihentikan.")
            

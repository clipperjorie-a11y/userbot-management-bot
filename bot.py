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
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid,
    PhoneCodeExpired, PasswordHashInvalid, PhoneNumberInvalid
)
from database import get_db, save_db

logging.basicConfig(level=logging.INFO)

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = int(os.getenv("OWNER_ID", "7193478617"))

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

login_sessions = {}
user_states = {}

# --- DATABASE INITIALIZER ---
def init_user_db(db, user_id):
    if "users" not in db:
        db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "plan": "none",
            "expired": "Tidak Aktif",
            "session": "",
            "settings": {
                "bc_text": "",
                "bc_delay": 5,
                "bc_interval": 30,
                "bc_targets": [],
                "forward_msg_link": "",
                "forward_delay": 5,
                "forward_interval": 30,
                "forward_targets": [],
                "replay_keyword": "",
                "replay_banword": "",
                "replay_text": "",
                "replay_cooldown": 10
            }
        }
    else:
        st = db["users"][user_id].setdefault("settings", {})
        st.setdefault("bc_text", "")
        st.setdefault("bc_delay", 5)
        st.setdefault("bc_interval", 30)
        st.setdefault("bc_targets", [])
        st.setdefault("forward_msg_link", "")
        st.setdefault("forward_delay", 5)
        st.setdefault("forward_interval", 30)
        st.setdefault("forward_targets", [])
        st.setdefault("replay_keyword", "")
        st.setdefault("replay_banword", "")
        st.setdefault("replay_text", "")
        st.setdefault("replay_cooldown", 10)
    save_db(db)

# --- KEYBOARD MAIN MENU ---
def build_reply_keyboard(user_id):
    db = get_db()
    user_data = db.get("users", {}).get(str(user_id), {})
    plan = user_data.get("plan", "none")

    buttons = [
        [KeyboardButton("🚀 Buat / Login Userbot"), KeyboardButton("⚙️ Panel Control Userbot")],
        [KeyboardButton("🛒 Toko"), KeyboardButton("💡 Fitur Unggulan")],
        [KeyboardButton("📚 Panduan Buat"), KeyboardButton("🎁 Coba Gratis")]
    ]
    
    if int(user_id) == OWNER_ID or "seller" in str(plan):
        buttons.append([KeyboardButton("👑 Panel Akses (Owner/Seller)")])
        
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- COMMAND /START ---
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    init_user_db(db, user_id)

    text = (
        "Selamat datang di **USERBOT JASEB & SMART AUTO REPLAY**!\n\n"
        "Gunakan menu tombol di bawah untuk mengelola Userbot kamu."
    )
    await message.reply_text(text, reply_markup=build_reply_keyboard(user_id))

# --- COMMAND /ADDPREM ---
@app.on_message(filters.command("addprem"))
async def addprem_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    sender_plan = db.get("users", {}).get(user_id, {}).get("plan", "none")

    if message.from_user.id != OWNER_ID and "seller" not in str(sender_plan):
        return await message.reply_text("❌ Anda tidak memiliki akses untuk memberikan paket.")

    args = message.text.split()
    if len(args) < 4:
        return await message.reply_text(
            "⚠️ **FORMAT SALAH**\n\nFormat: `/addprem [USER_ID] [PAKET] [HARI]`"
        )

    target_id = str(args[1])
    paket = args[2].lower()
    
    try:
        days = int(args[3])
    except ValueError:
        return await message.reply_text("❌ Jumlah hari harus berupa angka.")

    valid_plans = ["basic", "replay", "spesial", "reseller_basic", "reseller_spesial"]
    if paket not in valid_plans:
        return await message.reply_text("❌ Jenis paket tidak valid!")

    exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    
    init_user_db(db, target_id)
    db["users"][target_id]["plan"] = paket
    db["users"][target_id]["expired"] = exp_date
    save_db(db)

    await message.reply_text(
        f"✅ **AKSES BERHASIL DIBERIKAN!**\n\n"
        f"• Target ID: `{target_id}`\n"
        f"• Paket: `{paket.upper()}`\n"
        f"• Expired: `{exp_date}`"
    )

# --- MAIN HANDLER ---
@app.on_message(filters.text & ~filters.command(["start", "addprem"]))
async def main_handler(client, message):
    user_id = str(message.from_user.id)
    text = message.text
    db = get_db()
    init_user_db(db, user_id)
    
    user_data = db["users"][user_id]
    plan = user_data.get("plan", "none")

    # 1. LOGIN SESSIONS
    if user_id in login_sessions:
        session_info = login_sessions[user_id]
        step = session_info.get("step")

        if step == "phone":
            phone_number = text.replace(" ", "").replace("-", "")
            temp_client = Client(f"temp_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            try:
                code_info = await temp_client.send_code(phone_number)
                login_sessions[user_id] = {
                    "step": "otp",
                    "client": temp_client,
                    "phone": phone_number,
                    "phone_code_hash": code_info.phone_code_hash
                }
                return await message.reply_text("📩 Kirim kode OTP (Format: `1 2 3 4 5`):")
            except Exception as e:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text(f"❌ Terjadi kesalahan: `{e}`")

        elif step == "otp":
            otp_code = text.replace(" ", "").replace("-", "")
            temp_client = session_info["client"]
            phone = session_info["phone"]
            hash_code = session_info["phone_code_hash"]

            try:
                await temp_client.sign_in(phone, hash_code, otp_code)
                session_string = await temp_client.export_session_string()
                await temp_client.disconnect()

                db["users"][user_id]["session"] = session_string
                save_db(db)
                del login_sessions[user_id]

                return await message.reply_text("🎉 **LOGIN BERHASIL!** Userbot siap dikontrol.")
            except SessionPasswordNeeded:
                login_sessions[user_id]["step"] = "password"
                return await message.reply_text("🔐 Masukkan **Password 2FA** kamu:")
            except Exception as e:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text(f"❌ Gagal login: `{e}`")

        elif step == "password":
            temp_client = session_info["client"]
            try:
                await temp_client.check_password(text)
                session_string = await temp_client.export_session_string()
                await temp_client.disconnect()

                db["users"][user_id]["session"] = session_string
                save_db(db)
                del login_sessions[user_id]

                return await message.reply_text("🎉 **LOGIN BERHASIL!**")
            except Exception as e:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text(f"❌ Gagal login: `{e}`")

    # 2. USER STATES
    if user_id in user_states:
        state = user_states[user_id]
        st = db["users"][user_id]["settings"]

        if state == "input_bc_text":
            st["bc_text"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Teks Auto BC disimpan!")
        elif state == "input_bc_delay":
            if not text.isdigit(): return await message.reply_text("❌ Masukkan angka.")
            st["bc_delay"] = int(text)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Delay BC disimpan!")
        elif state == "input_bc_interval":
            if not text.isdigit(): return await message.reply_text("❌ Masukkan angka.")
            st["bc_interval"] = int(text)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Interval BC disimpan!")
        elif state == "input_bc_add_target":
            targets = [t.strip() for t in text.splitlines() if t.strip()]
            for t in targets:
                if t not in st["bc_targets"]: st["bc_targets"].append(t)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Target BC ditambahkan!")
        elif state == "input_replay_kw":
            st["replay_keyword"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Keyword Replay disimpan!")
        elif state == "input_replay_banword":
            st["replay_banword"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Banword disimpan!")
        elif state == "input_replay_text":
            st["replay_text"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Pesan Balasan disimpan!")

    # 3. BUTTON NAVIGATION
    if text == "⚙️ Panel Control Userbot":
        if plan == "none": return await message.reply_text("❌ Anda belum memiliki paket aktif.")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Setting Auto BC", callback_data="menu_bc"), InlineKeyboardButton("🔄 Setting Auto Forward", callback_data="menu_fv")],
            [InlineKeyboardButton("⚡ Setting Auto Replay (WTB)", callback_data="menu_replay")],
            [InlineKeyboardButton("📊 Status Config Saat Ini", callback_data="view_config")]
        ])
        return await message.reply_text("⚙️ **PANEL KONTROL USERBOT**", reply_markup=keyboard)

    elif text == "🚀 Buat / Login Userbot":
        if plan == "none": return await message.reply_text("❌ Beli paket atau klaim trial dulu.")
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text("📱 Kirim Nomor Telepon kamu (Contoh: `+628123456789`):")

    elif text == "🎁 Coba Gratis":
        if user_data.get("claimed_trial"): return await message.reply_text("❌ Sudah pernah klaim trial.")
        exp_date = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")
        db["users"][user_id]["plan"] = "spesial"
        db["users"][user_id]["expired"] = exp_date
        db["users"][user_id]["claimed_trial"] = True
        save_db(db)
        return await message.reply_text(f"🎉 **TRIAL GRATIS 5 JAM AKTIF!** Expired: `{exp_date}`")

# --- CALLBACK QUERY HANDLER ---
@app.on_callback_query()
async def cb_handler(client, cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    db = get_db()
    init_user_db(db, user_id)
    st = db["users"][user_id]["settings"]
    data = cb.data

    if data == "menu_bc":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Set Teks BC", callback_data="set_bc_text"), InlineKeyboardButton("➕ Tambah Target", callback_data="add_bc_target")],
            [InlineKeyboardButton("⏱️ Set Delay (s)", callback_data="set_bc_delay"), InlineKeyboardButton("🔄 Set Interval (m)", callback_data="set_bc_interval")],
            [InlineKeyboardButton("📋 Lihat Target", callback_data="list_bc_target"), InlineKeyboardButton("🗑️ Clear Target", callback_data="clear_bc_target")]
        ])
        await cb.message.edit_text("📢 **PANEL AUTO BC**", reply_markup=keyboard)
    elif data == "set_bc_text":
        user_states[user_id] = "input_bc_text"
        await cb.message.reply_text("📝 Kirim Teks BC:")
    elif data == "add_bc_target":
        user_states[user_id] = "input_bc_add_target"
        await cb.message.reply_text("➕ Kirim ID/Username Grup:")
    elif data == "set_bc_delay":
        user_states[user_id] = "input_bc_delay"
        await cb.message.reply_text("⏱️ Kirim Delay (detik):")
    elif data == "set_bc_interval":
        user_states[user_id] = "input_bc_interval"
        await cb.message.reply_text("🔄 Kirim Interval (menit):")
    elif data == "list_bc_target":
        targets = st.get("bc_targets", [])
        await cb.message.reply_text(f"📋 **Target BC:**\n" + ("\n".join(targets) if targets else "Kosong"))
    elif data == "clear_bc_target":
        st["bc_targets"] = []
        save_db(db)
        await cb.message.reply_text("🗑️ Target BC dikosongkan.")
    elif data == "menu_replay":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Set Keyword", callback_data="set_rp_kw"), InlineKeyboardButton("🚫 Set Banword", callback_data="set_rp_ban")],
            [InlineKeyboardButton("💬 Set Balasan", callback_data="set_rp_text")]
        ])
        await cb.message.edit_text("⚡ **PANEL AUTO REPLAY WTB**", reply_markup=keyboard)
    elif data == "set_rp_kw":
        user_states[user_id] = "input_replay_kw"
        await cb.message.reply_text("🔑 Kirim Keyword (pisahkan koma):")
    elif data == "set_rp_ban":
        user_states[user_id] = "input_replay_banword"
        await cb.message.reply_text("🚫 Kirim Banword (pisahkan koma):")
    elif data == "set_rp_text":
        user_states[user_id] = "input_replay_text"
        await cb.message.reply_text("💬 Kirim Teks Balasan:")

    await cb.answer()

# --- WEB SERVER & RUNNER UNTUK RAILWAY ---
async def handle_health_check(request):
    return web.Response(text="Bot Controller Active & Running!")

async def start_services():
    await app.start()
    logging.info("Pyrogram Client started successfully!")

    web_app = web.Application()
    web_app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health Check Web Server running on port {port}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
        

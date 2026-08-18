import os
import asyncio
import logging
from datetime import datetime, timedelta
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

# --- HELPER DATABASE INIT ---
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
                "bc_delay": 5,           # Delay antar kirim per grup (detik)
                "bc_interval": 30,       # Jeda per putaran/siklus (menit)
                "bc_targets": [],        # List ID / Username grup target BC
                
                "forward_msg_link": "", # Link pesan / ID pesan asal
                "forward_delay": 5,      # Delay antar forward (detik)
                "forward_interval": 30,  # Jeda per putaran (menit)
                "forward_targets": [],   # List ID / Username grup target Forward
                
                "replay_keyword": "",    # Keyword penyergap WTB
                "replay_banword": "",    # Kata yang dilarang (blacklist)
                "replay_text": "",       # Pesan balasan otomatis
                "replay_cooldown": 10    # Delay aman per rebalas (detik)
            }
        }
    else:
        # Pengecekan skema lama ke baru agar tidak error jika key belum ada
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
        "Gunakan menu tombol di bawah untuk mengelola dan mengonfigurasi Userbot kamu."
    )
    await message.reply_text(text, reply_markup=build_reply_keyboard(user_id))

# --- COMMAND /ADDPREM (OWNER/SELLER) ---
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
            "⚠️ **FORMAT SALAH**\n\n"
            "Gunakan format:\n"
            "`/addprem [USER_ID] [PAKET] [HARI]`\n\n"
            "**Pilihan Paket:**\n"
            "• `basic` | `replay` | `spesial` | `reseller_basic` | `reseller_spesial`"
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
        f"• Durasi: `{days} Hari`\n"
        f"• Expired: `{exp_date}`"
    )

# --- MAIN TEXT & INTERACTION HANDLER ---
@app.on_message(filters.text & ~filters.command(["start", "addprem"]))
async def main_handler(client, message):
    user_id = str(message.from_user.id)
    text = message.text
    db = get_db()
    init_user_db(db, user_id)
    
    user_data = db["users"][user_id]
    plan = user_data.get("plan", "none")

    # 1. ALUR LOGIN TELEGRAM
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
                return await message.reply_text(
                    "📩 Kode OTP telah dikirim oleh Telegram!\n\n"
                    "Gunakan spasi di antara angkanya (Contoh jika `12345` -> `1 2 3 4 5`)."
                )
            except PhoneNumberInvalid:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text("❌ Nomor telepon tidak valid! Klik **🚀 Buat / Login Userbot** lagi.")
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

                return await message.reply_text("🎉 **LOGIN BERHASIL!**\nUserbot kamu sekarang siap dikontrol.")

            except SessionPasswordNeeded:
                login_sessions[user_id]["step"] = "password"
                return await message.reply_text("🔐 Masukkan **Password 2FA** akun Telegram kamu:")
            except (PhoneCodeInvalid, PhoneCodeExpired):
                return await message.reply_text("❌ Kode OTP salah atau expired. Coba lagi:")
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

                return await message.reply_text("🎉 **LOGIN BERHASIL!**\nUserbot kamu siap digunakan.")
            except PasswordHashInvalid:
                return await message.reply_text("❌ Password 2FA salah! Coba masukkan lagi:")
            except Exception as e:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text(f"❌ Gagal login: `{e}`")

    # 2. ALUR INPUT SETTINGAN FITUR (USER STATES)
    if user_id in user_states:
        state = user_states[user_id]
        st = db["users"][user_id]["settings"]

        # AUTO BC STATES
        if state == "input_bc_text":
            st["bc_text"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Teks Pesan Auto BC berhasil disimpan!")

        elif state == "input_bc_delay":
            if not text.isdigit(): return await message.reply_text("❌ Masukkan angka bulat (detik).")
            st["bc_delay"] = int(text)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text(f"✅ Delay kirim BC diset: `{text} detik`")

        elif state == "input_bc_interval":
            if not text.isdigit(): return await message.reply_text("❌ Masukkan angka bulat (menit).")
            st["bc_interval"] = int(text)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text(f"✅ Interval putaran BC diset: `{text} menit`")

        elif state == "input_bc_add_target":
            targets = [t.strip() for t in text.splitlines() if t.strip()]
            added = 0
            for t in targets:
                if t not in st["bc_targets"]:
                    st["bc_targets"].append(t)
                    added += 1
            save_db(db)
            del user_states[user_id]
            return await message.reply_text(f"✅ Berhasil menambahkan `{added}` Grup Target BC baru!")

        # AUTO FORWARD (FP) STATES
        elif state == "input_fv_link":
            st["forward_msg_link"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Target Pesan / Link Forward berhasil disimpan!")

        elif state == "input_fv_delay":
            if not text.isdigit(): return await message.reply_text("❌ Masukkan angka (detik).")
            st["forward_delay"] = int(text)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text(f"✅ Delay Forward diset: `{text} detik`")

        elif state == "input_fv_interval":
            if not text.isdigit(): return await message.reply_text("❌ Masukkan angka (menit).")
            st["forward_interval"] = int(text)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text(f"✅ Interval Forward diset: `{text} menit`")

        elif state == "input_fv_add_target":
            targets = [t.strip() for t in text.splitlines() if t.strip()]
            added = 0
            for t in targets:
                if t not in st["forward_targets"]:
                    st["forward_targets"].append(t)
                    added += 1
            save_db(db)
            del user_states[user_id]
            return await message.reply_text(f"✅ Berhasil menambahkan `{added}` Grup Target Forward baru!")

        # AUTO REPLAY STATES
        elif state == "input_replay_kw":
            st["replay_keyword"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Keyword Auto Replay berhasil disimpan!")

        elif state == "input_replay_banword":
            st["replay_banword"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Banword (Blacklist Keyword) berhasil disimpan!")

        elif state == "input_replay_text":
            st["replay_text"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Pesan Balasan Auto Replay berhasil disimpan!")

        elif state == "input_replay_cooldown":
            if not text.isdigit(): return await message.reply_text("❌ Masukkan angka (detik).")
            st["replay_cooldown"] = int(text)
            save_db(db)
            del user_states[user_id]
            return await message.reply_text(f"✅ Cooldown Auto Replay diset: `{text} detik`")

    # 3. MAIN MENU BUTTONS
    if text == "⚙️ Panel Control Userbot":
        if plan == "none":
            return await message.reply_text("❌ Anda belum memiliki paket aktif.")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Setting Auto BC", callback_data="menu_bc"), InlineKeyboardButton("🔄 Setting Auto Forward", callback_data="menu_fv")],
            [InlineKeyboardButton("⚡ Setting Auto Replay (WTB)", callback_data="menu_replay")],
            [InlineKeyboardButton("📊 Status Config Saat Ini", callback_data="view_config")]
        ])
        return await message.reply_text("⚙️ **PANEL KONTROL USERBOT**\n\nPilih fitur yang ingin Anda kelola:", reply_markup=keyboard)

    elif text == "🚀 Buat / Login Userbot":
        if plan == "none":
            return await message.reply_text("❌ Silakan beli paket atau klaim trial gratis dulu.")
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text("📱 Kirimkan Nomor HP Telegram Anda (Contoh: `+628123456789`):")

    elif text == "🎁 Coba Gratis":
        if user_data.get("claimed_trial"):
            return await message.reply_text("❌ Anda sudah pernah mengambil Trial Gratis.")
        exp_date = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")
        db["users"][user_id]["plan"] = "spesial"
        db["users"][user_id]["expired"] = exp_date
        db["users"][user_id]["claimed_trial"] = True
        save_db(db)
        return await message.reply_text(f"🎉 **TRIAL GRATIS 5 JAM AKTIF!**\nExpired: `{exp_date}`\nSilakan klik **🚀 Buat / Login Userbot**.")

    elif text == "💡 Fitur Unggulan":
        return await message.reply_text(
            "🔥 **FITUR UNGGULAN USERBOT JASEB & AUTO REPLAY** 🔥\n\n"
            "📢 **Auto BC & Auto Forward Smart System**\n"
            "• Atur Delay per pesan & Interval per siklus/putaran.\n"
            "• Custom daftar grup target sesuka hati.\n\n"
            "⚡ **Smart Auto Replay WTB**\n"
            "• **Keyword Target:** Tangkap pesan pembeli secara otomatis.\n"
            "• **Banword Filter:** Hindari salah balas pesan/promosi lawan.\n"
            "• **Anti-Spam Cooldown:** Aman dari batasan Telegram."
        )

# --- CALLBACK QUERY HANDLER (INLINE NAVIGATION) ---
@app.on_callback_query()
async def cb_handler(client, cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    db = get_db()
    init_user_db(db, user_id)
    st = db["users"][user_id]["settings"]
    data = cb.data

    # --- MAIN SUB-MENUS ---
    if data == "menu_bc":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Set Teks BC", callback_data="set_bc_text"), InlineKeyboardButton("➕ Tambah Target Grup", callback_data="add_bc_target")],
            [InlineKeyboardButton("⏱️ Set Delay (Detik)", callback_data="set_bc_delay"), InlineKeyboardButton("🔄 Set Interval (Menit)", callback_data="set_bc_interval")],
            [InlineKeyboardButton("📋 Lihat Target Grup", callback_data="list_bc_target"), InlineKeyboardButton("🗑️ Clear Target", callback_data="clear_bc_target")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="menu_main")]
        ])
        await cb.message.edit_text("📢 **PANEL PENGATURAN AUTO BC**\n\nSilakan atur parameter broadcast kamu di bawah ini:", reply_markup=keyboard)

    elif data == "menu_fv":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Set Target/Link Forward", callback_data="set_fv_link"), InlineKeyboardButton("➕ Tambah Target Grup", callback_data="add_fv_target")],
            [InlineKeyboardButton("⏱️ Set Delay (Detik)", callback_data="set_fv_delay"), InlineKeyboardButton("🔄 Set Interval (Menit)", callback_data="set_fv_interval")],
            [InlineKeyboardButton("📋 Lihat Target Grup", callback_data="list_fv_target"), InlineKeyboardButton("🗑️ Clear Target", callback_data="clear_fv_target")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="menu_main")]
        ])
        await cb.message.edit_text("🔄 **PANEL PENGATURAN AUTO FORWARD (FP)**\n\nSilakan atur parameter auto forward kamu di bawah ini:", reply_markup=keyboard)

    elif data == "menu_replay":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Set Keyword WTB", callback_data="set_rp_kw"), InlineKeyboardButton("🚫 Set Banword Filter", callback_data="set_rp_ban")],
            [InlineKeyboardButton("💬 Set Pesan Balasan", callback_data="set_rp_text"), InlineKeyboardButton("⏱️ Set Cooldown Delay", callback_data="set_rp_cd")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="menu_main")]
        ])
        await cb.message.edit_text("⚡ **PANEL AUTO REPLAY WTB (SMART SYSTEM)**\n\nAtur keyword, pesan balasan, serta filter kata terlarang (banword) di sini:", reply_markup=keyboard)

    elif data == "menu_main":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Setting Auto BC", callback_data="menu_bc"), InlineKeyboardButton("🔄 Setting Auto Forward", callback_data="menu_fv")],
            [InlineKeyboardButton("⚡ Setting Auto Replay (WTB)", callback_data="menu_replay")],
            [InlineKeyboardButton("📊 Status Config Saat Ini", callback_data="view_config")]
        ])
        await cb.message.edit_text("⚙️ **PANEL KONTROL USERBOT**\n\nPilih fitur yang ingin Anda kelola:", reply_markup=keyboard)

    # --- AUTO BC TRIGGERS ---
    elif data == "set_bc_text":
        user_states[user_id] = "input_bc_text"
        await cb.message.reply_text("📝 **SETTING TEKS BC**\n\nKirimkan Teks / Pesan Promosi yang ingin di-Broadcast:")
    elif data == "set_bc_delay":
        user_states[user_id] = "input_bc_delay"
        await cb.message.reply_text("⏱️ **SETTING DELAY KIRIM BC**\n\nKirimkan angka **delay per pesan/grup** (dalam detik).\nContoh: `5`")
    elif data == "set_bc_interval":
        user_states[user_id] = "input_bc_interval"
        await cb.message.reply_text("🔄 **SETTING INTERVAL PUTARAN BC**\n\nKirimkan angka **jeda antar putaran BC** (dalam menit).\nContoh: `30`")
    elif data == "add_bc_target":
        user_states[user_id] = "input_bc_add_target"
        await cb.message.reply_text("➕ **TAMBAH TARGET GRUP BC**\n\nKirimkan ID atau Username grup (bisa banyak pisahkan dengan garis baru/enter):\n\nContoh:\n`@grup_lpm1`\n`@grup_lpm2`\n`-100123456789`")
    elif data == "list_bc_target":
        targets = st.get("bc_targets", [])
        list_str = "\n".join([f"• `{t}`" for t in targets]) if targets else "Belum ada grup yang ditambahkan."
        await cb.message.reply_text(f"📋 **DAFTAR GRUP

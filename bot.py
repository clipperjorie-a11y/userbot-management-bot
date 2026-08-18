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

# Aktifkan logging agar aktivitas bot terlihat di terminal/console
logging.basicConfig(level=logging.INFO)

# --- CONFIGURATION ---
# Ambil dari environment variable atau gunakan nilai default jika tidak diset
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = int(os.getenv("OWNER_ID", "7193478617"))

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Penyimpanan sementara dalam memori (RAM)
login_sessions = {}
user_states = {}

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
    
    # Menu Tambahan untuk Owner / Reseller
    if int(user_id) == OWNER_ID or "seller" in str(plan):
        buttons.append([KeyboardButton("👑 Panel Akses (Owner/Seller)")])
        
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- COMMAND /START ---
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    
    if "users" not in db: 
        db["users"] = {}
        
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "plan": "none",
            "expired": "Tidak Aktif",
            "session": "",
            "settings": {
                "bc_text": "",
                "bc_delay": 60,
                "replay_keyword": "",
                "replay_text": "",
                "forward_target": ""
            }
        }
        save_db(db)

    text = (
        "Selamat datang di **USERBOT JASEB OTOMATIS & AUTOREPLAY**!\n\n"
        "Gunakan menu tombol di bawah untuk mengelola Userbot kamu."
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
    
    if "users" not in db: db["users"] = {}
    if target_id not in db["users"]: db["users"][target_id] = {"settings": {}}

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
    if "users" not in db: db["users"] = {}
    user_data = db.get("users", {}).get(user_id, {})
    plan = user_data.get("plan", "none")

    # -------------------------------------------------------------
    # 1. ALUR LOGIN TELEGRAM (Nomor HP -> OTP -> Password 2FA)
    # -------------------------------------------------------------
    if user_id in login_sessions:
        session_info = login_sessions[user_id]
        step = session_info.get("step")

        # Step A: Terima Nomor Telepon
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
                    "Silakan kirim kode OTP dengan **spasi di antara angkanya** agar tidak diblokir Telegram.\n"
                    "Contoh jika kode `12345`, kirim: `1 2 3 4 5`"
                )
            except PhoneNumberInvalid:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text("❌ Nomor telepon tidak valid! Silakan klik **🚀 Buat / Login Userbot** lagi.")
            except Exception as e:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text(f"❌ Terjadi kesalahan: `{e}`")

        # Step B: Terima OTP
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

                return await message.reply_text("🎉 **LOGIN BERHASIL!**\nUserbot kamu sekarang siap digunakan dan diatur lewat Panel Control.")

            except SessionPasswordNeeded:
                login_sessions[user_id]["step"] = "password"
                return await message.reply_text("🔐 Akun kamu menggunakan Verifikasi 2-Langkah (2FA).\nSilakan kirim **Password 2FA** akun Telegram kamu:")
            except (PhoneCodeInvalid, PhoneCodeExpired):
                return await message.reply_text("❌ Kode OTP salah atau expired. Coba masukkan lagi dengan benar:")
            except Exception as e:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text(f"❌ Gagal login: `{e}`")

        # Step C: Terima Password 2FA
        elif step == "password":
            temp_client = session_info["client"]
            try:
                await temp_client.check_password(text)
                session_string = await temp_client.export_session_string()
                await temp_client.disconnect()

                db["users"][user_id]["session"] = session_string
                save_db(db)
                del login_sessions[user_id]

                return await message.reply_text("🎉 **LOGIN BERHASIL!**\nUserbot kamu sekarang siap digunakan.")
            except PasswordHashInvalid:
                return await message.reply_text("❌ Password 2FA salah! Masukkan lagi password yang benar:")
            except Exception as e:
                await temp_client.disconnect()
                del login_sessions[user_id]
                return await message.reply_text(f"❌ Gagal login: `{e}`")

    # -------------------------------------------------------------
    # 2. ALUR SETTING (STATE INPUT USER)
    # -------------------------------------------------------------
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == "input_bc_text":
            db["users"][user_id]["settings"]["bc_text"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Pesan Auto BC berhasil disimpan!")

        elif state == "input_replay_kw":
            db["users"][user_id]["settings"]["replay_keyword"] = text
            user_states[user_id] = "input_replay_text"
            return await message.reply_text("✅ Keyword disimpan!\n\nSekarang kirimkan **Pesan Balasan Otomatis** jika keyword tersebut terdeteksi:")

        elif state == "input_replay_text":
            db["users"][user_id]["settings"]["replay_text"] = text
            save_db(db)
            del user_states[user_id]
            return await message.reply_text("✅ Auto Replay berhasil dikonfigurasi dan aktif!")

    # -------------------------------------------------------------
    # 3. TOMBOL MENU UTAMA (REPLY KEYBOARD)
    # -------------------------------------------------------------
    if text == "⚙️ Panel Control Userbot":
        if plan == "none":
            return await message.reply_text("❌ Anda belum memiliki paket aktif.")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Setting Auto BC", callback_data="set_bc"), InlineKeyboardButton("🔄 Setting Auto Forward", callback_data="set_fv")],
            [InlineKeyboardButton("🤖 Setting Auto Replay (WTB)", callback_data="set_replay")],
            [InlineKeyboardButton("📊 Status & Config Saat Ini", callback_data="view_config")]
        ])
        return await message.reply_text("⚙️ **PANEL KONTROL USERBOT**\n\nSilakan pilih fitur yang ingin Anda atur:", reply_markup=keyboard)

    elif text == "🚀 Buat / Login Userbot":
        if plan == "none":
            return await message.reply_text("❌ Silakan beli paket atau klaim trial gratis dulu.")
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text("📱 Kirimkan Nomor HP Telegram Anda beserta kode negara (Contoh: `+628123456789`):")

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
            "🔥 **KEUNGGULAN USERBOT JASEB & AUTO REPLAY** 🔥\n\n"
            "📢 **Auto BC & Forward Super Cepat**\n*Promosi ke ribuan grup LPM secara otomatis.*\n\n"
            "⚡ **Auto Replay WTB / Keyword Smart System**\n*Penyergap pesan paling cerdas! Tangkap pesan calon pembeli di grup secara otomatis.*"
        )

# --- CALLBACK QUERY HANDLER (INLINE BUTTONS) ---
@app.on_callback_query()
async def cb_handler(client, cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    db = get_db()
    user_settings = db.get("users", {}).get(user_id, {}).get("settings", {})

    if cb.data == "set_bc":
        user_states[user_id] = "input_bc_text"
        await cb.message.reply_text("📝 **SETTING AUTO BC**\n\nSilakan kirimkan Teks/Pesan Promosi yang ingin di-Broadcast secara otomatis:")
        await cb.answer()

    elif cb.data == "set_replay":
        user_states[user_id] = "input_replay_kw"
        await cb.message.reply_text("🤖 **SETTING AUTO REPLAY (WTB)**\n\nKirimkan **Kata Kunci / Keyword** yang ingin ditangkap (pisahkan dengan koma).\nContoh: `wtb, cari, butuh, buy`")
        await cb.answer()

    elif cb.data == "view_config":
        bc_msg = user_settings.get("bc_text", "Belum Diatur")
        kw = user_settings.get("replay_keyword", "Belum Diatur")
        rp_msg = user_settings.get("replay_text", "Belum Diatur")
        
        await cb.message.reply_text(
            f"📊 **KONFIGURASI USERBOT SAAT INI:**\n\n"
            f"📢 **Pesan Auto BC:**\n`{bc_msg}`\n\n"
            f"🔑 **Keyword Auto Replay:** `{kw}`\n"
            f"💬 **Balasan Auto Replay:** `{rp_msg}`"
        )
        await cb.answer()

if __name__ == "__main__":
    app.run()
    

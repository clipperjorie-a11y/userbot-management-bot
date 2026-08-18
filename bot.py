import os, requests, asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from datetime import datetime, timedelta
from database import get_db, save_db

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = int(os.getenv("OWNER_ID", "7193478617"))
CS_USERNAME = "cThatchers"

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Sesi login OTP sementara
login_sessions = {}

# --- KEYBOARD ---
def build_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🚀 Buat Userbot")],
            [KeyboardButton("🔄 Perbarui"), KeyboardButton("🔴 Matikan"), KeyboardButton("⌛ Restart")],
            [KeyboardButton("📋 Daftar Userbot"), KeyboardButton("🛠️ Daftar Command")]
        ],
        resize_keyboard=True
    )

# --- COMMAND /START ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    if "users" not in db:
        db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "plan": "none",
            "expired": "Tidak Aktif",
            "target_groups": {},
            "session": ""
        }
        save_db(db)

    text = (
        "Selamat datang di USERBOT JASEB OTOMATIS & AUTOREPLAY!\n"
        "Saya dapat membuat Userbot secara instan.\n\n"
        "Ads: Channel Resmi 🔥"
    )
    await message.reply_text(text, reply_markup=build_reply_keyboard())

# --- COMMAND /CEKSTATUS ---
@app.on_message(filters.command("cekstatus") & filters.private)
async def cekstatus_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    user_data = db.get("users", {}).get(user_id, {})
    
    plan = user_data.get("plan", "none")
    exp = user_data.get("expired", "Tidak Aktif")
    
    await message.reply_text(
        f"🔍 **STATUS AKUN ANDA:**\n"
        f"• ID: `{user_id}`\n"
        f"• Paket: `{plan}`\n"
        f"• Status Akses: `{'✅ Aktif' if plan != 'none' else '❌ Belum Aktif'}`\n"
        f"• Masa Berlaku: `{exp}`"
    )

# --- COMMAND /ADDPREM (OWNER ONLY) ---
@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Perintah ini hanya untuk Owner.")
    
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text(
            "⚠️ **Format Salah!**\n"
            "Gunakan: `/addprem [USER_ID] [DURASI_HARI]`\n"
            "Contoh: `/addprem 123456789 30`"
        )
    
    target_id = str(args[1])
    try:
        days = int(args[2])
    except ValueError:
        days = 30

    db = get_db()
    if "users" not in db:
        db["users"] = {}
    
    exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    
    if target_id not in db["users"]:
        db["users"][target_id] = {}
    
    db["users"][target_id]["plan"] = "vip"
    db["users"][target_id]["expired"] = exp_date
    save_db(db)
    
    await message.reply_text(
        f"✅ **BERHASIL MEMBERIKAN AKSES!**\n\n"
        f"• Target ID: `{target_id}`\n"
        f"• Paket: `VIP`\n"
        f"• Durasi: `{days} Hari`\n"
        f"• Expired: `{exp_date}`\n\n"
        f"Akun tersebut sekarang sudah bisa menekan tombol **🚀 Buat Userbot**."
    )

# --- HANDLER TOMBOL & TEKS ---
@app.on_message(filters.private & filters.text & ~filters.command(["start", "addprem", "cekstatus"]))
async def message_handler(client, message):
    user_id = str(message.from_user.id)
    text = message.text
    db = get_db()
    
    # Ambil data user
    user_data = db.get("users", {}).get(user_id, {})
    user_plan = str(user_data.get("plan", "none")).lower()

    # 1. Tombol "🚀 Buat Userbot"
    if text == "🚀 Buat Userbot":
        # Jika bukan owner DAN paketnya masih 'none'
        if message.from_user.id != OWNER_ID and (user_plan == "none" or not user_plan):
            return await message.reply_text(
                "❌ **AKSES DITOLAK**\n\n"
                "Anda belum memiliki akses/paket aktif.\n"
                "Silakan hubungi Owner untuk mendapatkan akses.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Hubungi Owner / CS", url=f"https://t.me/{CS_USERNAME}")]
                ])
            )
        
        # Jika sudah berakses (atau owner) -> Langsung masuk proses Login
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text(
            "📱 **LOGIN USERBOT VIA OTP**\n\n"
            "Silakan kirimkan Nomor HP Anda yang terhubung dengan akun Telegram.\n"
            "Format: `+628xxxxxxxxxx`"
        )

    # 2. Alur Input Login OTP
    if user_id in login_sessions:
        step = login_sessions[user_id].get("step")
        
        if step == "phone":
            phone = text.replace(" ", "")
            login_sessions[user_id]["phone"] = phone
            login_sessions[user_id]["step"] = "otp"
            return await message.reply_text(
                f"⏳ Menghubungkan ke nomor `{phone}`...\n"
                "Silakan kirimkan **Kode OTP** yang Anda terima dari Telegram."
            )
        
        elif step == "otp":
            otp_code = text.replace(" ", "")
            login_sessions.pop(user_id, None)
            return await message.reply_text("✅ Login berhasil diproses!")

    # 3. Handling Tombol Keyboard Lainnya
    if text == "🔄 Perbarui":
        await message.reply_text("🔄 Sistem berhasil diperbarui.")
    elif text == "🔴 Matikan":
        await message.reply_text("🔴 Userbot telah dimatikan.")
    elif text == "⌛ Restart":
        await message.reply_text("⌛ Sedang me-restart sistem...")
    elif text == "📋 Daftar Userbot":
        status = "Aktif" if user_plan != "none" else "Tidak Aktif"
        await message.reply_text(f"📋 **STATUS USERBOT:**\n• Status: `{status}`")
    elif text == "🛠️ Daftar Command":
        await message.reply_text("🛠️ **DAFTAR COMMAND OWNER:**\n`/addprem [ID] [HARI]` - Beri Akses User\n`/cekstatus` - Cek Status Akses")

# --- EXECUTION ---
if __name__ == "__main__":
    print("Bot Controller berjalan...")
    app.run()
        

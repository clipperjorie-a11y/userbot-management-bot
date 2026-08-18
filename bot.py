import os
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from database import get_db, save_db

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Penyimpanan status login user
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
    name = message.from_user.first_name
    text = (
        f"👋 Halo, {name}.\n\n"
        "Selamat datang di USERBOT JASEB OTOMATIS & AUTOREPLAY JORIE! "
        "Saya dapat membuat Userbot secara instan.\n\n"
        "Ads: Channel Resmi Joriie 🔥"
    )
    await message.reply_text(text, reply_markup=build_reply_keyboard())

# --- HANDLER TOMBOL & INPUT ---
@app.on_message(filters.private & filters.text & ~filters.command(["start", "addprem", "addseller"]))
async def message_handler(client, message):
    user_id = str(message.from_user.id)
    text = message.text
    db = get_db()
    user_data = db.get("users", {}).get(user_id, {"plan": "none"})

    # 1. Handle Klik Tombol "🚀 Buat Userbot"
    if text == "🚀 Buat Userbot":
        if user_data.get("plan") == "none":
            return await message.reply_text("❌ Anda belum memiliki paket aktif! Silakan hubungi Owner untuk pembelian.")
        
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text("📱 **LOGIN USERBOT**\nSilakan kirimkan nomor HP Anda dengan format internasional (Contoh: +6281234567890)")

    # 2. Handle Flow Login OTP (Jika user sedang dalam proses login)
    if user_id in login_sessions:
        step = login_sessions[user_id].get("step")
        
        if step == "phone":
            phone = text.replace(" ", "")
            # (Integrasi dengan login logic seperti sebelumnya)
            await message.reply_text("⏳ Menghubungkan ke Telegram... Silakan tunggu kode OTP.")
            # Di sini tambahkan logika request code Pyrogram
            login_sessions[user_id]["step"] = "otp"
            return

    # 3. Handle Tombol Lainnya
    if text == "🔄 Perbarui":
        await message.reply_text("🔄 Sistem sedang menyegarkan data...")
    elif text == "🔴 Matikan":
        await message.reply_text("🔴 Userbot dimatikan.")
    elif text == "⌛ Restart":
        await message.reply_text("⌛ Restarting...")
    elif text == "📋 Daftar Userbot":
        await message.reply_text("📋 Daftar userbot aktif: 0")
    elif text == "🛠️ Daftar Command":
        await message.reply_text("🛠️ Gunakan /addprem untuk memberi akses.")

# --- ADMIN COMMANDS ---
@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    # Logika addprem sama seperti sebelumnya
    await message.reply_text("✅ Akses diberikan.")

# --- RUN BOT ---
if __name__ == "__main__":
    print("Bot sedang berjalan...")
    app.run()
    

import os
from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database import get_db, save_db

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = int(os.getenv("OWNER_ID", "7193478617"))
CS_USERNAME = "cThatchers"

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

login_sessions = {}

# --- KEYBOARD ---
def build_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🚀 Buat Userbot"), KeyboardButton("🛒 Toko"), KeyboardButton("💡 Fitur Unggulan")],
            [KeyboardButton("📚 Panduan Buat"), KeyboardButton("🎁 Coba Gratis")],
            [KeyboardButton("🔑 Klaim Token")]
        ],
        resize_keyboard=True
    )

# --- COMMAND /START ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    text = (
        "Selamat datang di USERBOT JASEB OTOMATIS & AUTOREPLAY!\n"
        "Saya dapat membuat Userbot secara instan.\n\n"
        "Ads: Channel Resmi 🔥"
    )
    await message.reply_text(text, reply_markup=build_reply_keyboard())

# --- MESSAGE HANDLER ---
@app.on_message(filters.private & filters.text & ~filters.command(["start", "addprem", "cekstatus"]))
async def message_handler(client, message):
    user_id = str(message.from_user.id)
    text = message.text
    db = get_db()
    user_data = db.get("users", {}).get(user_id, {})
    user_plan = str(user_data.get("plan", "none")).lower()

    # 1. Logic Tombol "🚀 Buat Userbot"
    if text == "🚀 Buat Userbot":
        if message.from_user.id != OWNER_ID and (user_plan == "none" or not user_plan):
            return await message.reply_text(
                "❌ **AKSES DITOLAK**\n\n"
                "Anda belum memiliki akses/paket aktif.\n"
                "Silakan pilih paket di menu **🛒 Toko** atau hubungi Owner.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Hubungi Owner / CS", url=f"https://t.me/{CS_USERNAME}")]])
            )
        
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text("📱 **LOGIN VIA OTP**\nSilakan kirimkan Nomor HP Anda (+628xxxxxxxxxx):")

    # 2. Logic Tombol "🛒 Toko" (Price List 4 Katalog)
    elif text == "🛒 Toko":
        pricelist_text = (
            "🛒 **DAFTAR HARGA & PRICELIST USERBOT**\n\n"
            "───────────────\n"
            "🔹 **1. KATALOG BASIC**\n"
            "*(Akses: Auto BC + Auto Forward)*\n"
            "• 1 Hari : Rp1.000\n"
            "• 1 Minggu : Rp3.000\n"
            "• 1 Bulan : Rp3.500\n"
            "• Permanen : Rp18.000\n\n"
            "───────────────\n"
            "🔹 **2. KATALOG AUTO REPLAY / WTB**\n"
            "*(Akses: Auto Replay / Auto WTB)*\n"
            "• 1 Hari : Rp2.000\n"
            "• 1 Minggu : Rp3.000\n"
            "• 1 Bulan : Rp5.000\n"
            "• Permanen : Rp20.000\n\n"
            "───────────────\n"
            "⭐ **3. KATALOG SPESIAL**\n"
            "*(Akses: Auto BC + Auto Forward + Auto Replay)*\n"
            "• 1 Hari : Rp3.000\n"
            "• 1 Minggu : Rp4.000\n"
            "• 1 Bulan : Rp7.000\n"
            "• Permanen : Rp35.000\n\n"
            "───────────────\n"
            "💼 **4. KATALOG RESELLER**\n\n"
            "• **Basic Seller** *(Khusus Akses Basic)*:\n"
            "  └ 1 Bulan : Rp35.000\n\n"
            "• **Auto Replay Seller** *(Khusus Akses Auto Replay)*:\n"
            "  └ 1 Bulan : Rp35.000\n\n"
            "• **Spesial Seller** *(Akses Auto BC + Auto Forward + Spesial)*:\n"
            "  └ 1 Bulan : Rp50.000\n"
            "  └ Permanen : Rp250.000\n"
            "───────────────\n\n"
            "Untuk melakukan pemesanan, silakan klik tombol di bawah untuk beli via Owner/CS:"
        )
        return await message.reply_text(
            pricelist_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Beli / Hubungi CS", url=f"https://t.me/{CS_USERNAME}")]
            ])
        )

    # 3. Logic Tombol Keyboard Lainnya
    elif text == "💡 Fitur Unggulan":
        fitur_text = (
            "✨ **FITUR UNGGULAN USERBOT:**\n\n"
            "• 📢 **Auto BC & Auto Forward:** Kirim pesan otomatis ke grup LPM secara teratur.\n"
            "• 🤖 **Auto Replay / WTB:** Balas & tangkap kata kunci pesan secara instan.\n"
            "• ⭐ **Paket Spesial:** Kombinasi lengkap seluruh fitur dalam satu akun.\n"
            "• 💼 **Lisensi Reseller:** Buka usaha sewa userbot dengan panel sendiri."
        )
        await message.reply_text(fitur_text)

    elif text == "📚 Panduan Buat":
        await message.reply_text(
            "📚 **PANDUAN PEMBUATAN USERBOT:**\n\n"
            "1. Pilih paket pilihanmu di menu **🛒 Toko**.\n"
            "2. Lakukan pembayaran ke CS/Owner.\n"
            "3. Setelah akses diaktifkan, tekan tombol **🚀 Buat Userbot**.\n"
            "4. Kirim nomor HP Telegram dan masukkan kode OTP.\n"
            "5. Userbot langsung aktif dan siap digunakan!"
        )

    elif text == "🎁 Coba Gratis":
        await message.reply_text(
            "🎁 **TRIAL GRATIS**\n\n"
            "Ingin mencoba keunggulan fitur Userbot?\n"
            "Silakan hubungi Admin/CS untuk klaim sesi trial gratis.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Klaim Trial ke CS", url=f"https://t.me/{CS_USERNAME}")]])
        )

    elif text == "🔑 Klaim Token":
        await message.reply_text("🔑 **KLAIM TOKEN AKSES**\n\nSilakan masukkan kode token Anda:")

    # 4. Handle Input OTP
    if user_id in login_sessions:
        if login_sessions[user_id]["step"] == "phone":
            login_sessions[user_id]["step"] = "otp"
            await message.reply_text("⏳ Menghubungkan ke server Telegram... Silakan kirimkan **Kode OTP** yang Anda terima:")

# --- COMMAND ADDPREM (OWNER ONLY) ---
@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Perintah ini hanya untuk Owner.")
    
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("⚠️ Format: `/addprem [USER_ID] [HARI]`")
    
    target_id = str(args[1])
    try:
        days = int(args[2])
    except ValueError:
        days = 30

    db = get_db()
    if "users" not in db: db["users"] = {}
    if target_id not in db["users"]: db["users"][target_id] = {}
    
    db["users"][target_id]["plan"] = "vip"
    save_db(db)
    await message.reply_text(f"✅ Berhasil memberikan akses ke ID `{target_id}` selama {days} hari.")

if __name__ == "__main__":
    print("Bot Controller berjalan...")
    app.run()
    

import os, requests, asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from datetime import datetime, timedelta
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
    if "users" not in db: db["users"] = {}
    
    user_data = db.get("users", {}).get(user_id, {})
    user_plan = str(user_data.get("plan", "none")).lower()

    # Cek apakah paket expired (untuk Trial/Regular)
    exp_str = user_data.get("expired", "")
    if exp_str and exp_str != "Permanen":
        try:
            exp_time = datetime.strptime(exp_str, "%Y-%m-%d %H:%M")
            if datetime.now() > exp_time:
                user_plan = "none"
                db["users"][user_id]["plan"] = "none"
                save_db(db)
        except:
            pass

    # 1. Tombol "🚀 Buat Userbot"
    if text == "🚀 Buat Userbot":
        if message.from_user.id != OWNER_ID and (user_plan == "none" or not user_plan):
            return await message.reply_text(
                "❌ **AKSES DITOLAK**\n\n"
                "Anda belum memiliki akses aktif.\n"
                "Silakan klaim **🎁 Coba Gratis** (5 Jam) atau beli paket di **🛒 Toko**!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Hubungi Owner / CS", url=f"https://t.me/{CS_USERNAME}")]])
            )
        
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text("📱 **LOGIN USERBOT VIA OTP**\nSilakan kirimkan Nomor HP Anda (+628xxxxxxxxxx):")

    # 2. Tombol "🎁 Coba Gratis" (OTOMATIS 5 JAM TANPA IZIN OWNER)
    elif text == "🎁 Coba Gratis":
        # Cek jika user sudah pernah klaim trial
        if user_data.get("claimed_trial"):
            return await message.reply_text("❌ Anda sudah pernah mengambil Trial Gratis 5 Jam sebelumnya.")

        # Set Akses Gratis 5 Jam
        exp_date = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")
        
        if user_id not in db["users"]: db["users"][user_id] = {}
        db["users"][user_id]["plan"] = "trial"
        db["users"][user_id]["expired"] = exp_date
        db["users"][user_id]["claimed_trial"] = True
        save_db(db)

        # Langsung tawarkan login
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text(
            "🎉 **TRIAL GRATIS 5 JAM BERHASIL DIAKTIFKAN!**\n\n"
            "Akses Userbot Anda aktif selama **5 Jam** tanpa perlu izin Owner.\n"
            f"• Masa Berlaku s/d: `{exp_date}`\n\n"
            "📱 **LANGSUNG BUAT USERBOT:**\n"
            "Silakan kirimkan Nomor HP Telegram Anda sekarang (+628xxxxxxxxxx):"
        )

    # 3. Tombol "🛒 Toko" (Pricelist 4 Katalog)
    elif text == "🛒 Toko":
        pricelist_text = (
            "🛒 **DAFTAR HARGA & PRICELIST USERBOT**\n\n"
            "🔹 **1. KATALOG BASIC** *(Auto BC + Auto Forward)*\n"
            "• 1 Hari : Rp1.000 | 1 Minggu : Rp3.000\n"
            "• 1 Bulan : Rp3.500 | Permanen : Rp18.000\n\n"
            "🔹 **2. KATALOG AUTO REPLAY** *(Auto Replay / WTB)*\n"
            "• 1 Hari : Rp2.000 | 1 Minggu : Rp3.000\n"
            "• 1 Bulan : Rp5.000 | Permanen : Rp20.000\n\n"
            "⭐ **3. KATALOG SPESIAL** *(Auto BC + Forward + Replay)*\n"
            "• 1 Hari : Rp3.000 | 1 Minggu : Rp4.000\n"
            "• 1 Bulan : Rp7.000 | Permanen : Rp35.000\n\n"
            "💼 **4. KATALOG RESELLER**\n"
            "• Basic Seller : Rp35.000/bln\n"
            "• Auto Replay Seller : Rp35.000/bln\n"
            "• Spesial Seller : Rp50.000/bln | Rp250.000/perm\n"
        )
        return await message.reply_text(
            pricelist_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Beli / Hubungi CS", url=f"https://t.me/{CS_USERNAME}")]
            ])
        )

    # 4. Tombol "💡 Fitur Unggulan" (Sangat Menarik & Khusus Userbot)
    elif text == "💡 Fitur Unggulan":
        fitur_text = (
            "🔥 **KEUNGGULAN USERBOT JASEB & AUTO REPLAY** 🔥\n\n"
            "📢 **Auto BC & Forward Super Cepat**\n"
            "   *Promosikan jualanmu ke ribuan grup LPM secara otomatis tanpa henti. Hemat waktu, tenaga, dan tingkatkan omzet jutaan rupiah!*\n\n"
            "⚡ **Auto Replay WTB / Keyword Smart System**\n"
            "   *Penyergap pesan paling cerdas! Tangkap pesan calon pembeli yang cari barang (WTB) di grup-grup dan langsung balas detik itu juga sebelum keduluan kompetitor.*\n\n"
            "🛡️ **Sistem Anti-Banned & Proteksi Tinggi**\n"
            "   *Dibuat dengan sistem delay dan proteksi pintar agar akun Telegram kamu tetap aman dan nyaman digunakan untuk promosi harian.*\n\n"
            "🎮 **Kontrol Praktis Lewat Bot**\n"
            "   *Tidak perlu ribet ngoding! Semua settingan pesan, kata kunci, dan tujuan grup bisa kamu atur sendiri dalam hitungan detik lewa bot ini.*"
        )
        await message.reply_text(fitur_text)

    # 5. Tombol Lainnya
    elif text == "📚 Panduan Buat":
        await message.reply_text(
            "📚 **PANDUAN PEMBUATAN USERBOT:**\n\n"
            "1. Coba gratis via menu **🎁 Coba Gratis** atau beli paket di **🛒 Toko**.\n"
            "2. Klik tombol **🚀 Buat Userbot**.\n"
            "3. Kirimkan nomor HP Telegram (+62...).\n"
            "4. Masukkan kode OTP Telegram yang masuk.\n"
            "5. Userbot kamu langsung aktif & siap menebar promosi!"
        )

    elif text == "🔑 Klaim Token":
        await message.reply_text("🔑 **KLAIM TOKEN AKSES**\n\nSilakan masukkan kode token unik kamu:")

    # 6. Alur Input Login (OTP)
    if user_id in login_sessions:
        if login_sessions[user_id]["step"] == "phone":
            login_sessions[user_id]["step"] = "otp"
            await message.reply_text("⏳ Menghubungkan ke server Telegram... Silakan masukkan **Kode OTP** yang dikirimkan Telegram:")

if __name__ == "__main__":
    print("Bot Controller Userbot Berjalan...")
    app.run()
    

import os, requests, asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid,
    PhoneCodeExpired, PasswordHashInvalid
)
from datetime import datetime, timedelta
from database import get_db, save_db

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = int(os.getenv("OWNER_ID", "7193478617"))
CS_USERNAME = os.getenv("CS_USERNAME", "cThatchers")

# Gateway QRIS (Orkut / Orderkuota)
ORKUT_AUTH_TOKEN = os.getenv("ORKUT_AUTH_TOKEN", "")
ORKUT_MERCHANT_ID = os.getenv("ORKUT_MERCHANT_ID", "")

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Sesi Login Telegram sementara
login_sessions = {}

# --- GATEWAY PAYMENT AUTOMATION ---
def generate_qris(amount):
    if not ORKUT_AUTH_TOKEN or not ORKUT_MERCHANT_ID:
        return None, None
    url = f"https://qris.orderkuota.com/api/create_qris?token={ORKUT_AUTH_TOKEN}&merchant={ORKUT_MERCHANT_ID}&amount={amount}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("status") == "success":
            return res.get("qris_url"), res.get("trx_id")
    except:
        pass
    return None, None

def check_qris_status(trx_id, amount):
    if not ORKUT_AUTH_TOKEN or not ORKUT_MERCHANT_ID:
        return False
    url = f"https://qris.orderkuota.com/api/check_status?token={ORKUT_AUTH_TOKEN}&merchant={ORKUT_MERCHANT_ID}&trx_id={trx_id}&amount={amount}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("status") == "PAID" or res.get("data", {}).get("status") == "PAID":
            return True
    except:
        pass
    return False

# --- KEYBOARD MAIN MENU ---
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
    has_session = "✅ Terhubung" if user_data.get("session") else "❌ Belum Login"
    
    await message.reply_text(
        f"🔍 **STATUS USERBOT ANDA:**\n\n"
        f"• ID Account: `{user_id}`\n"
        f"• Paket Active: `{plan.upper()}`\n"
        f"• Masa Berlaku: `{exp}`\n"
        f"• Status Userbot: `{has_session}`"
    )

# --- COMMAND /ADDPREM (OWNER ONLY) ---
@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Perintah khusus Owner.")
    
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("⚠️ Format: `/addprem [USER_ID] [HARI]`")
    
    target_id = str(args[1])
    try:
        days = int(args[2])
    except:
        days = 30

    db = get_db()
    if "users" not in db: db["users"] = {}
    if target_id not in db["users"]: db["users"][target_id] = {}
    
    exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    db["users"][target_id]["plan"] = "vip"
    db["users"][target_id]["expired"] = exp_date
    save_db(db)
    
    await message.reply_text(
        f"✅ **AKSES VIP BERHASIL DIBERIKAN!**\n\n"
        f"• Target ID: `{target_id}`\n"
        f"• Durasi: `{days} Hari`\n"
        f"• Expired: `{exp_date}`\n\n"
        f"User tersebut sekarang bisa langsung menekan tombol **🚀 Buat Userbot**."
    )

# --- HANDLER TEKS UTAMA & ALUR OTP ---
@app.on_message(filters.private & filters.text & ~filters.command(["start", "addprem", "cekstatus"]))
async def message_handler(client, message):
    user_id = str(message.from_user.id)
    text = message.text
    db = get_db()
    if "users" not in db: db["users"] = {}
    
    user_data = db.get("users", {}).get(user_id, {})
    user_plan = str(user_data.get("plan", "none")).lower()

    # Pengecekan Masa Kedaluwarsa Paket
    exp_str = user_data.get("expired", "")
    if exp_str and exp_str not in ["Tidak Aktif", "Permanen"]:
        try:
            exp_time = datetime.strptime(exp_str, "%Y-%m-%d %H:%M")
            if datetime.now() > exp_time:
                user_plan = "none"
                db["users"][user_id]["plan"] = "none"
                db["users"][user_id]["expired"] = "Expired"
                save_db(db)
        except:
            pass

    # 1. TOMBOL "🚀 Buat Userbot"
    if text == "🚀 Buat Userbot":
        if message.from_user.id != OWNER_ID and (user_plan == "none" or not user_plan):
            return await message.reply_text(
                "❌ **AKSES DITOLAK**\n\n"
                "Anda belum memiliki paket/akses aktif.\n"
                "Silakan klaim **🎁 Coba Gratis** (5 Jam) atau beli paket di **🛒 Toko**!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Hubungi CS", url=f"https://t.me/{CS_USERNAME}")]])
            )
        
        # Mulai Proses Login OTP
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text(
            "📱 **LOGIN USERBOT VIA OTP**\n\n"
            "Silakan kirimkan Nomor HP Telegram Anda yang terhubung.\n"
            "Format: `+628xxxxxxxxxx`"
        )

    # 2. ALUR PROSES INPUT NOMOR HP, KODE OTP & PASSWORD 2FA
    if user_id in login_sessions:
        step = login_sessions[user_id].get("step")
        
        # Step A: Input Phone
        if step == "phone":
            phone_number = text.replace(" ", "").replace("-", "")
            msg = await message.reply_text("⏳ Connecting ke Telegram Server...")
            
            # Buat client Pyrogram sementara untuk request OTP
            temp_client = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            try:
                await temp_client.connect()
                code_hash = await temp_client.send_code(phone_number)
                
                login_sessions[user_id] = {
                    "step": "otp",
                    "phone": phone_number,
                    "phone_code_hash": code_hash.phone_code_hash,
                    "client": temp_client
                }
                return await msg.edit_text(
                    f"✅ **KODE OTP TERKIRIM!**\n\n"
                    f"Kode OTP telah dikirim ke Telegram nomor `{phone_number}`.\n"
                    f"Silakan ketik/kirimkan **Kode OTP** di sini:"
                )
            except Exception as e:
                await temp_client.disconnect()
                login_sessions.pop(user_id, None)
                return await msg.edit_text(f"❌ **Gagal Mengirim OTP:** {str(e)}\nSilakan coba lagi.")

        # Step B: Input Kode OTP
        elif step == "otp":
            otp_code = text.replace(" ", "").replace("-", "")
            temp_data = login_sessions[user_id]
            temp_client = temp_data["client"]
            
            msg = await message.reply_text("⏳ Verifikasi Kode OTP...")
            try:
                # Login dengan OTP
                await temp_client.sign_in(
                    phone_number=temp_data["phone"],
                    phone_code_hash=temp_data["phone_code_hash"],
                    phone_code=otp_code
                )
                
                # Export String Session setelah berhasil login
                session_string = await temp_client.export_session_string()
                await temp_client.disconnect()
                
                # Simpan Session ke Database
                db["users"][user_id]["session"] = session_string
                save_db(db)
                login_sessions.pop(user_id, None)
                
                return await msg.edit_text(
                    "🎉 **USERBOT BERHASIL DIAKTIFKAN!**\n\n"
                    "Userbot Anda sudah aktif dan siap digunakan secara otomatis.\n"
                    "Gunakan perintah `/cekstatus` untuk melihat status aktif Anda."
                )
            except SessionPasswordNeeded:
                login_sessions[user_id]["step"] = "2fa"
                return await msg.edit_text("🔐 **VERIFIKASI 2-STEP (2FA)**\nAkun Anda menggunakan Verifikasi 2 Langkah.\nSilakan masukkan Password Verifikasi Anda:")
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                return await msg.edit_text("❌ Kode OTP Salah atau Expired. Silakan coba klik **🚀 Buat Userbot** lagi.")
            except Exception as e:
                await temp_client.disconnect()
                login_sessions.pop(user_id, None)
                return await msg.edit_text(f"❌ Error: {str(e)}")

        # Step C: Input 2FA Password
        elif step == "2fa":
            password = text
            temp_data = login_sessions[user_id]
            temp_client = temp_data["client"]
            msg = await message.reply_text("⏳ Verifikasi Password...")
            
            try:
                await temp_client.check_password(password)
                session_string = await temp_client.export_session_string()
                await temp_client.disconnect()
                
                db["users"][user_id]["session"] = session_string
                save_db(db)
                login_sessions.pop(user_id, None)
                
                return await msg.edit_text("🎉 **USERBOT BERHASIL DIAKTIFKAN!**\nUserbot Anda sudah aktif sepenuhnya.")
            except PasswordHashInvalid:
                return await msg.edit_text("❌ Password 2FA Salah. Silakan masukkan password yang benar:")
            except Exception as e:
                await temp_client.disconnect()
                login_sessions.pop(user_id, None)
                return await msg.edit_text(f"❌ Error: {str(e)}")

    # 3. TOMBOL "🎁 Coba Gratis" (5 Jam Auto Trial)
    elif text == "🎁 Coba Gratis":
        if user_data.get("claimed_trial"):
            return await message.reply_text("❌ Anda sudah pernah mengambil Trial Gratis 5 Jam sebelumnya.")

        exp_date = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")
        
        if user_id not in db["users"]: db["users"][user_id] = {}
        db["users"][user_id]["plan"] = "trial"
        db["users"][user_id]["expired"] = exp_date
        db["users"][user_id]["claimed_trial"] = True
        save_db(db)

        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text(
            "🎉 **TRIAL GRATIS 5 JAM DIAKTIFKAN!**\n\n"
            f"• Expired pada: `{exp_date}`\n\n"
            "📱 **LANGSUNG BUAT USERBOT:**\n"
            "Silakan kirimkan Nomor HP Telegram Anda sekarang (+628xxxxxxxxxx):"
        )

    # 4. TOMBOL "🛒 Toko" (Pricelist & Beli)
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
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Beli Otomatis (QRIS)", callback_data="buy_qris")],
            [InlineKeyboardButton("💬 Hubungi CS / Manual", url=f"https://t.me/{CS_USERNAME}")]
        ])
        return await message.reply_text(pricelist_text, reply_markup=keyboard)

    # 5. TOMBOL "💡 Fitur Unggulan"
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
            "   *Tidak perlu ribet ngoding! Semua settingan pesan, kata kunci, dan tujuan grup bisa kamu atur sendiri dalam hitungan detik lewat bot ini.*"
        )
        await message.reply_text(fitur_text)

    # 6. TOMBOL "📚 Panduan Buat"
    elif text == "📚 Panduan Buat":
        await message.reply_text(
            "📚 **PANDUAN PEMBUATAN USERBOT:**\n\n"
            "1. Coba gratis via menu **🎁 Coba Gratis** atau beli paket di **🛒 Toko**.\n"
            "2. Tekan tombol **🚀 Buat Userbot**.\n"
            "3. Kirimkan nomor HP Telegram (+62...).\n"
            "4. Masukkan kode OTP Telegram yang masuk.\n"
            "5. Userbot kamu langsung aktif & siap menebar promosi!"
        )

    # 7. TOMBOL "🔑 Klaim Token"
    elif text == "🔑 Klaim Token":
        await message.reply_text("🔑 **KLAIM TOKEN AKSES**\n\nSilakan masukkan kode token unik kamu:")

# --- CALLBACK QUERY HANDLER (PAYMENT QRIS) ---
@app.on_callback_query()
async def callback_handler(client, cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    await cb.answer()

    if cb.data == "buy_qris":
        # Contoh nominal Paket Spesial 1 Bulan (Rp7.000)
        amount = 7000
        qris_url, trx_id = generate_qris(amount)
        
        if not qris_url:
            return await cb.message.reply_text(f"❌ Otomatisasi QRIS sedang maintenance. Silakan hubungi CS: @{CS_USERNAME}")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Cek Pembayaran", callback_data=f"check_{trx_id}_{amount}")]
        ])
        
        await cb.message.reply_photo(
            photo=qris_url,
            caption=(
                f"💳 **PEMBAYARAN QRIS OTOMATIS**\n\n"
                f"Total Pembayaran: **Rp{amount:,}**\n"
                f"TRX ID: `{trx_id}`\n\n"
                f"Silakan scan QRIS di atas via GoPay, OVO, Dana, ShopeePay, atau Mobile Banking.\n"
                f"Setelah transfer, tekan tombol **Cek Pembayaran** di bawah."
            ),
            reply_markup=keyboard
        )

    elif cb.data.startswith("check_"):
        _, trx_id, amount = cb.data.split("_")
        is_paid = check_qris_status(trx_id, amount)
        
        if is_paid:
            db = get_db()
            exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
            if user_id not in db["users"]: db["users"][user_id] = {}
            
            db["users"][user_id]["plan"] = "vip"
            db["users"][user_id]["expired"] = exp_date
            save_db(db)

            await cb.message.edit_caption("🎉 **PEMBAYARAN BERHASIL!** Akses Paket Spesial (30 Hari) telah diaktifkan.\n\nSilakan tekan tombol **🚀 Buat Userbot** untuk memulai.")
        else:
            await cb.answer("❌ Pembayaran belum terdeteksi. Silakan selesaikan pembayaran terlebih dahulu.", show_alert=True)

# --- RUN EXECUTION ---
if __name__ == "__main__":
    print("Bot Controller Final Versi Siap Berjalan...")
    app.run()
                

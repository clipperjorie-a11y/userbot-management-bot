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

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

login_sessions = {}
user_states = {} # Untuk menangkap input setting pesan/keyword

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
    
    # Tambahkan menu khusus jika user adalah Owner / Reseller
    if int(user_id) == OWNER_ID or "seller" in plan:
        buttons.append([KeyboardButton("👑 Panel Akses (Owner/Seller)")])
        
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- COMMAND /START ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    if "users" not in db: db["users"] = {}
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
        "Selamat datang di USERBOT JASEB OTOMATIS & AUTOREPLAY!\n"
        "Gunakan menu di bawah untuk mengelola Userbot kamu."
    )
    await message.reply_text(text, reply_markup=build_reply_keyboard(user_id))

# --- SYSTEM MANAGEMENT AKSES (OWNER & RESELLER) ---
# Format Owner: /addprem [USER_ID] [PAKET] [HARI]
# Paket: basic | replay | spesial | reseller_basic | reseller_spesial
@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    sender_plan = db.get("users", {}).get(user_id, {}).get("plan", "none")

    # Cek Wewenang
    if message.from_user.id != OWNER_ID and "seller" not in sender_plan:
        return await message.reply_text("❌ Anda tidak memiliki akses untuk memberikan paket.")

    args = message.text.split()
    if len(args) < 4:
        return await message.reply_text(
            "⚠️ **FORMAT SALAH**\n\n"
            "Gunakan format:\n"
            "`/addprem [USER_ID] [PAKET] [HARI]`\n\n"
            "**Pilihan Paket:**\n"
            "• `basic` (Auto BC + Forward)\n"
            "• `replay` (Auto Replay/WTB)\n"
            "• `spesial` (Semua Fitur)\n"
            "• `reseller_basic` (Akses Seller)\n"
            "• `reseller_spesial` (Akses Seller Full)"
        )

    target_id = str(args[1])
    paket = args[2].lower()
    
    try:
        days = int(args[3])
    except:
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
        f"• Jenis Paket: `{paket.upper()}`\n"
        f"• Durasi: `{days} Hari`\n"
        f"• Expired: `{exp_date}`"
    )

# --- PANEL CONTROL USERBOT (SETTING FITUR) ---
@app.on_message(filters.private & filters.text & ~filters.command(["start", "addprem"]))
async def main_handler(client, message):
    user_id = str(message.from_user.id)
    text = message.text
    db = get_db()
    if "users" not in db: db["users"] = {}
    
    user_data = db.get("users", {}).get(user_id, {})
    plan = user_data.get("plan", "none")

    # 1. PANEL CONTROL (Pengaturan Fitur Userbot)
    if text == "⚙️ Panel Control Userbot":
        if plan == "none":
            return await message.reply_text("❌ Anda belum memiliki paket aktif.")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Setting Auto BC", callback_data="set_bc"), InlineKeyboardButton("🔄 Setting Auto Forward", callback_data="set_fv")],
            [InlineKeyboardButton("🤖 Setting Auto Replay (WTB)", callback_data="set_replay")],
            [InlineKeyboardButton("📊 Status & Config Saat Ini", callback_data="view_config")]
        ])
        return await message.reply_text("⚙️ **PANEL KONTROL USERBOT**\n\nSilakan pilih fitur yang ingin Anda atur:", reply_markup=keyboard)

    # 2. PROSES INPUT SETTINGAN (STATE HANDLER)
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

    # 3. FITUR LAINNYA
    elif text == "🚀 Buat / Login Userbot":
        if plan == "none":
            return await message.reply_text("❌ Silakan beli paket atau klaim trial gratis dulu.")
        login_sessions[user_id] = {"step": "phone"}
        return await message.reply_text("📱 Kirimkan Nomor HP Telegram Anda (+628xxxxxxxxxx):")

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

# --- CALLBACK QUERY HANDLER (PANEL CONTROL) ---
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
    

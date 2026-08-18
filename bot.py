import os, requests, asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton
)
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from datetime import datetime, timedelta
from database import get_db, save_db

# --- CONFIGURATION ---
API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = 7193478617
CS_USERNAME = "cThatchers"

ORKUT_AUTH_TOKEN = os.getenv("ORKUT_AUTH_TOKEN", "")
ORKUT_MERCHANT_ID = os.getenv("ORKUT_MERCHANT_ID", "")

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Penyimpanan sementara session login (akan reset jika bot restart)
login_sessions = {}

# --- GATEWAY PAYMENT ---
def generate_qris(amount):
    if not ORKUT_AUTH_TOKEN or not ORKUT_MERCHANT_ID: return None, None
    url = f"https://qris.orderkuota.com/api/create_qris?token={ORKUT_AUTH_TOKEN}&merchant={ORKUT_MERCHANT_ID}&amount={amount}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("status") == "success": return res.get("qris_url"), res.get("trx_id")
    except: pass
    return None, None

def check_qris_status(trx_id, amount):
    if not ORKUT_AUTH_TOKEN or not ORKUT_MERCHANT_ID: return False
    url = f"https://qris.orderkuota.com/api/check_status?token={ORKUT_AUTH_TOKEN}&merchant={ORKUT_MERCHANT_ID}&trx_id={trx_id}&amount={amount}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("status") == "PAID" or res.get("data", {}).get("status") == "PAID": return True
    except: pass
    return False

# --- KEYBOARDS ---
def build_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🚀 Buat Userbot")],
            [KeyboardButton("🔄 Perbarui"), KeyboardButton("🔴 Matikan"), KeyboardButton("⌛ Restart")],
            [KeyboardButton("📋 Daftar Userbot"), KeyboardButton("🛠️ Daftar Command")]
        ],
        resize_keyboard=True
    )

def build_main_keyboard(user_data):
    keyboard = []
    if not user_data.get("session"):
        keyboard.append([InlineKeyboardButton("🔑 Login Userbot (OTP)", callback_data="login_otp")])
    else:
        keyboard.append([InlineKeyboardButton("🚪 Logout Userbot", callback_data="logout_ubot")])

    keyboard.append([
        InlineKeyboardButton("📢 Setting Jaseb", callback_data="menu_groups"),
        InlineKeyboardButton("🎯 Setting WTB", callback_data="menu_groups")
    ])
    keyboard.append([
        InlineKeyboardButton("💳 Beli Paket (QRIS)", callback_data="buy_menu"),
        InlineKeyboardButton("💬 Bantuan / CS", url=f"https://t.me/{CS_USERNAME}")
    ])
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERS ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    if "users" not in db: db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {"plan": "none", "expired": "Tidak Aktif", "target_groups": {}, "session": ""}
        save_db(db)
    
    user_data = db["users"][user_id]
    await message.reply_text("🤖 **USERBOT CONTROL PANEL**\n\nSilakan gunakan tombol menu di bawah.", reply_markup=build_reply_keyboard())
    await message.reply_text("Pilih opsi pengaturan:", reply_markup=build_main_keyboard(user_data))

@app.on_callback_query()
async def callback_handler(client, cb: CallbackQuery):
    print(f"DEBUG: Tombol ditekan -> {cb.data}") # Cek log ini di Railway
    user_id = str(cb.from_user.id)
    db = get_db()
    user_data = db.get("users", {}).get(user_id, {"plan": "none", "expired": "Tidak Aktif", "target_groups": {}, "session": ""})
    
    await cb.answer() 

    if cb.data == "login_otp":
        if user_data.get("plan") == "none":
            return await cb.message.reply_text("❌ Anda belum memiliki paket aktif!")
        login_sessions[user_id] = {"step": "phone"}
        await cb.message.edit_text("📱 **LOGIN VIA OTP**\nKirimkan nomor HP Anda (format: +62...):")

    elif cb.data == "logout_ubot":
        db["users"][user_id]["session"] = ""
        save_db(db)
        await cb.message.edit_text("✅ Berhasil Logout.", reply_markup=build_main_keyboard(db["users"][user_id]))

    elif cb.data == "buy_menu":
        keyboard = [
            [InlineKeyboardButton("📢 Basic Jaseb — Rp3.500", callback_data="buy_jaseb_30")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back_main")]
        ]
        await cb.message.edit_text("🛒 **PILIH PAKET:**", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif cb.data == "back_main":
        await cb.message.edit_text("Menu Utama:", reply_markup=build_main_keyboard(user_data))

@app.on_message(filters.private & filters.text & ~filters.command(["start", "addprem", "addseller", "cancel"]))
async def message_handler(client, message):
    user_id = str(message.from_user.id)
    
    # Handle Reply Keyboard (Tombol Bawah)
    if message.text == "🚀 Buat Userbot":
        return await message.reply_text("Silakan klik tombol **🔑 Login Userbot (OTP)** di pesan panel atas.")
    
    # Handle Login Flow
    if user_id in login_sessions:
        step = login_sessions[user_id].get("step")
        if step == "phone":
            # (Tambahkan logika input OTP yang sama dengan versi sebelumnya di sini)
            await message.reply_text("Proses login dimulai...")
            login_sessions[user_id]["step"] = "otp"
            # ... tambahkan logika kirim OTP di sini ...

@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 4: return await message.reply_text("Format: /addprem [ID] [plan] [durasi]")
    # (Logika addprem sama seperti sebelumnya)
    await message.reply_text("✅ Akses diberikan.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("Bot sedang berjalan...")
    app.run()
            

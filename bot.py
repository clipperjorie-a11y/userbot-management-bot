import os, requests, asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from datetime import datetime, timedelta
from database import get_db, save_db

API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8")
OWNER_ID = 7193478617

ORKUT_AUTH_TOKEN = os.getenv("ORKUT_AUTH_TOKEN", "")
ORKUT_MERCHANT_ID = os.getenv("ORKUT_MERCHANT_ID", "")

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

login_sessions = {}

# --- FUNGSI GATEWAY ORDERKUOTA / OKECONNECT ---
def generate_qris(amount):
    if not ORKUT_AUTH_TOKEN or not ORKUT_MERCHANT_ID:
        return None, None
    url = f"https://qris.orderkuota.com/api/create_qris?token={ORKUT_AUTH_TOKEN}&merchant={ORKUT_MERCHANT_ID}&amount={amount}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("status") == "success":
            return res.get("qris_url"), res.get("trx_id")
    except Exception:
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
    except Exception:
        pass
    return False

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
        InlineKeyboardButton("💬 Bantuan / CS", url=f"tg://user?id={OWNER_ID}")
    ])
    return InlineKeyboardMarkup(keyboard)

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    user_data = db.get("users", {}).get(user_id, {"plan": "none", "expired": "Tidak Aktif", "target_groups": {}, "session": ""})
    
    is_logged_in = "✅ Terhubung" if user_data.get("session") else "❌ Belum Login"
    plan_status = user_data.get("plan", "none").upper()

    text = (
        f"🤖 **USERBOT CONTROL PANEL**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ID Telegram:** `{user_id}`\n"
        f"📱 **Status Login:** **{is_logged_in}**\n"
        f"📦 **Paket Aktif:** **{plan_status}**\n"
        f"⏳ **Masa Aktif:** `{user_data.get('expired', 'Tidak Aktif')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Silakan pilih menu pengaturan di bawah ini:"
    )
    
    await message.reply_text(text, reply_markup=build_main_keyboard(user_data))

@app.on_callback_query()
async def callback_handler(client, cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    data = cb.data
    db = get_db()
    
    await cb.answer()

    if "users" not in db:
        db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {"plan": "none", "expired": "Tidak Aktif", "target_groups": {}, "session": ""}

    user_data = db["users"][user_id]

    if data == "login_otp":
        if user_data.get("plan") == "none":
            return await cb.answer("❌ Anda belum memiliki paket aktif! Silakan beli paket terlebih dahulu.", show_alert=True)
        
        login_sessions[user_id] = {"step": "phone"}
        await cb.message.edit_text(
            "📱 **LOGIN USERBOT VIA OTP**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Silakan kirimkan **Nomor Telepon** akun Telegram Anda.\n"
            "Gunakan format internasional (Contoh: `+6281234567890`).\n\n"
            "*(Ketik /cancel jika ingin membatalkan)*"
        )

    elif data == "logout_ubot":
        db["users"][user_id]["session"] = ""
        save_db(db)
        await cb.answer("✅ Berhasil Logout dari akun Userbot!", show_alert=True)
        await cb.message.edit_text("✅ Anda telah logout.", reply_markup=build_main_keyboard(db["users"][user_id]))

    elif data == "buy_menu":
        text = (
            "🛒 **PILIH PAKET SEWA USERBOT**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Pilih daftar paket yang tersedia di bawah ini:"
        )
        keyboard = [
            [InlineKeyboardButton("📢 Basic Jaseb — Rp3.500/Bln", callback_data="buy_jaseb_30")],
            [InlineKeyboardButton("🎯 Auto Reply WTB — Rp5.000/Bln", callback_data="buy_wtb_30")],
            [InlineKeyboardButton("⚡ Full Spesial — Rp7.000/Bln", callback_data="buy_spesial_30")],
            [InlineKeyboardButton("👑 Full Permanen — Rp35.000", callback_data="buy_spesial_perm")],
            [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="back_main")]
        ]
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("buy_"):
        _, plan, dur = data.split("_")
        price_map = {"jaseb_30": 3500, "wtb_30": 5000, "spesial_30": 7000, "spesial_perm": 35000}
        amount = price_map.get(f"{plan}_{dur}", 5000)
        
        qris_url, trx_id = generate_qris(amount)
        if qris_url:
            if "payments" not in db:
                db["payments"] = {}
            db["payments"][trx_id] = {
                "user_id": user_id, 
                "plan": plan, 
                "dur": dur, 
                "amount": amount,
                "status": "pending"
            }
            save_db(db)

            # Kirim gambar QRIS ke chat
            await cb.message.delete()
            await client.send_photo(
                chat_id=user_id,
                photo=qris_url,
                caption=(
                    f"💳 **PEMBAYARAN QRIS OTOMATIS**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 Paket: **{plan.upper()}**\n"
                    f"💰 Total Biaya: **Rp{amount:,}**\n\n"
                    f"Silakan Scan QRIS di atas menggunakan E-Wallet / M-Banking Anda.\n"
                    f"Setelah membayar, klik tombol **'Cek Status Pembayaran'** di bawah."
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Cek Status Pembayaran", callback_data=f"check_{trx_id}")],
                    [InlineKeyboardButton("⬅️ Batal / Kembali", callback_data="buy_menu")]
                ])
            )
        else:
            await cb.message.edit_text(
                f"💳 **PEMBAYARAN MANUAL**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Sistem QRIS OrderKuota belum terkonfigurasi di Railway.\n"
                f"Silakan transfer sebesar **Rp{amount:,}** ke Owner (`{OWNER_ID}`).",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="buy_menu")]])
            )

    elif data.startswith("check_"):
        trx_id = data.replace("check_", "")
        payments = db.get("payments", {})
        
        if trx_id not in payments:
            return await cb.answer("❌ Transaksi tidak ditemukan!", show_alert=True)
        
        pay_info = payments[trx_id]
        if pay_info.get("status") == "success":
            return await cb.answer("✅ Pembayaran ini sudah sukses dan paket telah aktif!", show_alert=True)
            
        amount = pay_info.get("amount")
        is_paid = check_qris_status(trx_id, amount)

        if is_paid:
            pay_plan = pay_info.get("plan")
            pay_dur = pay_info.get("dur")
            
            exp_days = 180 if pay_dur in ["perm", "permanen"] else 30
            exp_date = (datetime.now() + timedelta(days=exp_days)).strftime("%Y-%m-%d")

            db["users"][user_id]["plan"] = pay_plan
            db["users"][user_id]["expired"] = exp_date
            db["payments"][trx_id]["status"] = "success"
            save_db(db)

            await cb.answer("🎉 Pembayaran Berhasil Terverifikasi!", show_alert=True)
            await cb.message.delete()
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 **PEMBAYARAN BERHASIL!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Paket **{pay_plan.upper()}** Anda telah aktif hingga `{exp_date}`.\n\n"
                    f"Silakan klik tombol **'🔑 Login Userbot (OTP)'** untuk menghubungkan akun Telegram Anda."
                ),
                reply_markup=build_main_keyboard(db["users"][user_id])
            )
        else:
            await cb.answer("⏳ Pembayaran belum terdeteksi. Silakan selesaikan pembayaran lalu coba tekan tombol ini lagi.", show_alert=True)

    elif data == "menu_groups":
        text = (
            "📋 **PENGATURAN GRUP TARGET WORK**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Klik nama grup di bawah untuk mengaktifkan [✅] atau mematikan [❌] fitur auto-forward/reply:"
        )
        target_dict = user_data.get("target_groups", {})
        keyboard = []

        if target_dict:
            for chat_id, chat_info in target_dict.items():
                is_active = chat_info.get("active", False)
                status_icon = "✅" if is_active else "❌"
                keyboard.append([InlineKeyboardButton(f"{status_icon} {chat_info.get('name', chat_id)}", callback_data=f"toggle_grp_{chat_id}")])
        else:
            text += "\n\n*(Belum ada grup terdeteksi. Silakan Login akun dan pastikan akun bergabung di grup LPM)*"

        keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_main")])
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("toggle_grp_"):
        chat_id = data.replace("toggle_grp_", "")
        target_dict = user_data.get("target_groups", {})
        
        if chat_id in target_dict:
            current_status = target_dict[chat_id].get("active", False)
            target_dict[chat_id]["active"] = not current_status
            db["users"][user_id]["target_groups"] = target_dict
            save_db(db)
            
            keyboard = []
            for c_id, c_info in target_dict.items():
                status_icon = "✅" if c_info.get("active", False) else "❌"
                keyboard.append([InlineKeyboardButton(f"{status_icon} {c_info.get('name', c_id)}", callback_data=f"toggle_grp_{c_id}")])
            keyboard.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_main")])
            
            await cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_main":
        is_logged_in = "✅ Terhubung" if user_data.get("session") else "❌ Belum Login"
        plan_status = user_data.get("plan", "none").upper()
        text = (
            f"🤖 **USERBOT CONTROL PANEL**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **ID Telegram:** `{user_id}`\n"
            f"📱 **Status Login:** **{is_logged_in}**\n"
            f"📦 **Paket Aktif:** **{plan_status}**\n"
            f"⏳ **Masa Aktif:** `{user_data.get('expired', 'Tidak Aktif')}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Silakan pilih menu pengaturan di bawah ini:"
        )
        await cb.message.edit_text(text, reply_markup=build_main_keyboard(user_data))

@app.on_message(filters.private & filters.text & ~filters.command(["start", "addprem", "addseller", "cancel"]))
async def login_input_handler(client, message):
    user_id = str(message.from_user.id)
    if user_id not in login_sessions:
        return

    session_info = login_sessions[user_id]
    step = session_info.get("step")
    text = message.text.strip()

    if step == "phone":
        phone_number = text.replace(" ", "")
        temp_client = Client(f"temp_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await temp_client.connect()
        try:
            code_info = await temp_client.send_code(phone_number)
            login_sessions[user_id] = {
                "step": "otp",
                "phone": phone_number,
                "phone_code_hash": code_info.phone_code_hash,
                "client": temp_client
            }
            await message.reply_text(
                "📩 **KODE OTP TERKIRIM!**\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "Masukkan kode OTP yang dikirim oleh Telegram.\n\n"
                "⚠️ **PENTING:** Format kirim kode harus menggunakan spasi!\n"
                "Contoh: jika kode `12345`, kirimkan: `1 2 3 4 5`"
            )
        except Exception as e:
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            del login_sessions[user_id]
            await message.reply_text(f"❌ Gagal mengirim OTP: `{e}`\nSilakan coba lagi dari menu /start.")

    elif step == "otp":
        otp_code = text.replace(" ", "").replace("-", "")
        temp_client = session_info["client"]
        phone = session_info["phone"]
        code_hash = session_info["phone_code_hash"]

        try:
            await temp_client.sign_in(phone, code_hash, otp_code)
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()

            db = get_db()
            if "users" not in db:
                db["users"] = {}
            if user_id not in db["users"]:
                db["users"][user_id] = {"plan": "none", "expired": "Tidak Aktif", "target_groups": {}}
            
            db["users"][user_id]["session"] = string_session
            save_db(db)

            del login_sessions[user_id]
            await message.reply_text("🎉 **LOGIN BERHASIL!**\nAkun Userbot Anda telah aktif dan terhubung ke sistem.")

        except SessionPasswordNeeded:
            login_sessions[user_id]["step"] = "2fa"
            await message.reply_text("🔐 Akun Anda menggunakan Verifikasi 2-Langkah (2FA).\nSilakan masukkan **Password 2FA** Anda:")

        except (PhoneCodeInvalid, PhoneCodeExpired) as e:
            await message.reply_text("❌ Kode OTP salah/kadaluarsa. Silakan ulang proses login.")
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            del login_sessions[user_id]

        except Exception as e:
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            del login_sessions[user_id]
            await message.reply_text(f"❌ Terjadi kesalahan: `{e}`")

    elif step == "2fa":
        temp_client = session_info["client"]
        password = text
        try:
            await temp_client.check_password(password)
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()

            db = get_db()
            db["users"][user_id]["session"] = string_session
            save_db(db)

            del login_sessions[user_id]
            await message.reply_text("🎉 **LOGIN BERHASIL!**\nAkun Userbot Anda telah terhubung.")
        except Exception as e:
            await message.reply_text(f"❌ Password 2FA Salah/Gagal: `{e}`")

@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    actor_id = message.from_user.id
    args = message.text.split()
    if len(args) < 4:
        return await message.reply_text("⚠️ Format: `/addprem [ID_User] [jaseb|wtb|spesial] [durasi]`")

    target_id, plan, duration = args[1], args[2].lower(), args[3].lower()
    db = get_db()
    is_owner = (actor_id == OWNER_ID)
    seller_role = db.get("sellers", {}).get(str(actor_id))

    if not is_owner and not seller_role:
        return await message.reply_text("❌ Akses ditolak!")

    exp_date = (datetime.now() + timedelta(days=180 if duration in ["perm", "permanen"] else int(''.join(filter(str.isdigit, duration)) or 30))).strftime("%Y-%m-%d")
    
    if "users" not in db:
        db["users"] = {}
    if target_id not in db["users"]:
        db["users"][target_id] = {"target_groups": {}, "session": ""}
        
    db["users"][target_id]["plan"] = plan
    db["users"][target_id]["expired"] = exp_date
    save_db(db)
    await message.reply_text(f"✅ Akses **{plan.upper()}** diberikan ke `{target_id}` hingga `{exp_date}`.")

@app.on_message(filters.command("addseller") & filters.private)
async def addseller_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Khusus Owner!")
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("⚠️ Format: `/addseller [ID_User] [seller_jaseb|seller_wtb|seller_spesial]`")

    target_id, seller_type = args[1], args[2].lower()
    db = get_db()
    if "sellers" not in db:
        db["sellers"] = {}
    db["sellers"][target_id] = seller_type
    save_db(db)
    await message.reply_text(f"✅ User `{target_id}` diangkat menjadi **{seller_type.upper()}**!")
        

import os, requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta
from database import get_db, save_db

API_ID = int(os.getenv("API_ID", "21727751"))
API_HASH = os.getenv("API_HASH", "b4430e30489aa8ee83c16a3e110c7104")
BOT_TOKEN = "8806476092:AAEQflCwvylPWCThNEHS33dc9OW65WDODK8"
OWNER_ID = 7193478617

ORKUT_AUTH_TOKEN = os.getenv("ORKUT_AUTH_TOKEN", "")
ORKUT_MERCHANT_ID = os.getenv("ORKUT_MERCHANT_ID", "")

app = Client("bot_controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = str(message.from_user.id)
    db = get_db()
    user_data = db["users"].get(user_id, {"plan": "none", "expired": "Tidak Aktif", "target_groups": {}})
    
    text = (
        f"🤖 **Userbot Control Panel**\n\n"
        f"🆔 **ID Anda:** `{user_id}`\n"
        f"📦 **Status Paket:** **{user_data['plan'].upper()}**\n"
        f"⏳ **Masa Aktif:** `{user_data.get('expired', 'Tidak Aktif')}`\n\n"
        f"Kelola fitur dan daftar grup target Anda di bawah ini:"
    )
    
    keyboard = []
    if user_data["plan"] in ["jaseb", "spesial"]:
        keyboard.append([InlineKeyboardButton("📢 Setting Grup Jaseb (Auto BC)", callback_data="menu_groups")])
    if user_data["plan"] in ["wtb", "spesial"]:
        keyboard.append([InlineKeyboardButton("🎯 Setting Grup WTB (Auto Reply)", callback_data="menu_groups")])
    keyboard.append([InlineKeyboardButton("💳 Beli Paket (Payment QRIS)", callback_data="buy_menu")])
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

@app.on_callback_query()
async def callback_handler(client, cb: CallbackQuery):
    user_id = str(cb.from_user.id)
    data = cb.data
    db = get_db()
    user_data = db["users"].get(user_id, {"plan": "none", "target_groups": {}})

    if data == "buy_menu":
        text = "🛒 **PILIH PAKET USERBOT**\n\nSilakan pilih paket:"
        keyboard = [
            [InlineKeyboardButton("Basic / Jaseb (Rp3.500/Bln)", callback_data="buy_jaseb_30")],
            [InlineKeyboardButton("Auto Reply WTB (Rp5.000/Bln)", callback_data="buy_wtb_30")],
            [InlineKeyboardButton("Full Fitur Spesial (Rp7.000/Bln)", callback_data="buy_spesial_30")],
            [InlineKeyboardButton("Full Fitur Permanen (Rp35.000)", callback_data="buy_spesial_perm")],
        ]
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("buy_"):
        _, plan, dur = data.split("_")
        price_map = {"jaseb_30": 3500, "wtb_30": 5000, "spesial_30": 7000, "spesial_perm": 35000}
        amount = price_map.get(f"{plan}_{dur}", 5000)
        
        qris_url, trx_id = generate_qris(amount)
        if qris_url:
            db["payments"][trx_id] = {"user_id": user_id, "plan": plan, "dur": dur, "status": "pending"}
            save_db(db)
            await cb.message.edit_text(
                f"💳 **PEMBAYARAN QRIS OTOMATIS**\n\nPaket: **{plan.upper()}**\nTotal: **Rp{amount:,}**\n\nScan QRIS untuk bayar:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cek Status Pembayaran", callback_data=f"check_{trx_id}")]])
            )
        else:
            await cb.message.edit_text(f"💳 **PEMBAYARAN MANUAL**\n\nTransfer Rp{amount:,} ke Owner (`{OWNER_ID}`).")

    elif data == "menu_groups":
        # MINTA ENGINE USERBOT MENGAMBIL DAFTAR GRUP SIKC
        text = "📋 **PILIH GRUP TARGET WORK USERBOT**\n\nKlik tombol grup di bawah untuk mengaktifkan [✅] atau mematikan [❌] akses kerja userbot pada grup tersebut:"
        
        target_dict = user_data.get("target_groups", {})
        keyboard = []

        # Tampilkan Tombol Interaktif Sesuai Status Aktif/Nonaktif
        if target_dict:
            for chat_id, chat_name in target_dict.items():
                is_active = target_dict[chat_id].get("active", False)
                status_icon = "✅" if is_active else "❌"
                keyboard.append([InlineKeyboardButton(f"{status_icon} {chat_name}", callback_data=f"toggle_grp_{chat_id}")])
        else:
            text += "\n\n*(Belum ada grup terdeteksi. Silakan tambah akun userbot ke grup LPM/Target Anda terlebih dahulu)*"

        keyboard.append([InlineKeyboardButton("🔄 Refresh Daftar Grup", callback_data="refresh_groups")])
        keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back_main")])
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("toggle_grp_"):
        chat_id = data.replace("toggle_grp_", "")
        target_dict = user_data.get("target_groups", {})
        
        if chat_id in target_dict:
            current_status = target_dict[chat_id].get("active", False)
            target_dict[chat_id]["active"] = not current_status
            db["users"][user_id]["target_groups"] = target_dict
            save_db(db)
            await cb.answer(f"Status grup diperbarui ke: {'AKTIF' if not current_status else 'NONAKTIF'}", show_alert=True)
            
            # Auto Reload Menu
            await callback_handler(client, cb)

    elif data == "back_main":
        await start_cmd(client, cb.message)

@app.on_message(filters.command("addprem") & filters.private)
async def addprem_cmd(client, message):
    actor_id = message.from_user.id
    args = message.text.split()
    if len(args) < 4:
        return await message.reply_text("⚠️ Format: `/addprem [ID_User] [jaseb|wtb|spesial] [durasi]`")

    target_id, plan, duration = args[1], args[2].lower(), args[3].lower()
    db = get_db()
    is_owner = (actor_id == OWNER_ID)
    seller_role = db["sellers"].get(str(actor_id))

    if not is_owner and not seller_role:
        return await message.reply_text("❌ Akses ditolak! Anda bukan Seller atau Owner.")

    if not is_owner:
        if seller_role == "seller_jaseb" and plan != "jaseb":
            return await message.reply_text("❌ Lisensi Anda hanya untuk paket Jaseb.")
        elif seller_role == "seller_wtb" and plan != "wtb":
            return await message.reply_text("❌ Lisensi Anda hanya untuk paket WTB.")

    exp_date = (datetime.now() + timedelta(days=180 if duration in ["perm", "permanen"] else int(''.join(filter(str.isdigit, duration)) or 30))).strftime("%Y-%m-%d")
    
    if target_id not in db["users"]:
        db["users"][target_id] = {"target_groups": {}}
        
    db["users"][target_id]["plan"] = plan
    db["users"][target_id]["expired"] = exp_date
    save_db(db)
    await message.reply_text(f"✅ Akses **{plan.upper()}** berhasil diberikan ke `{target_id}` hingga `{exp_date}`.")

@app.on_message(filters.command("addseller") & filters.private)
async def addseller_cmd(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("❌ Khusus Owner!")
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("⚠️ Format: `/addseller [ID_User] [seller_jaseb|seller_wtb|seller_spesial]`")

    target_id, seller_type = args[1], args[2].lower()
    db = get_db()
    db["sellers"][target_id] = seller_type
    save_db(db)
    await message.reply_text(f"✅ User `{target_id}` diangkat menjadi **{seller_type.upper()}**!")
      

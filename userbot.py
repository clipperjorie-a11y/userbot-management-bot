import os, asyncio
from pyrogram import Client, filters
from database import get_db, save_db

API_ID = int(os.getenv("API_ID", "21727751"))
API_HASH = os.getenv("API_HASH", "b4430e30489aa8ee83c16a3e110c7104")
SESSION_STRING = os.getenv("SESSION_STRING", "")

app = Client("ubot_engine", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- FUNGSI DETEKSI DAN SINKRONISASI GRUP OTOMATIS ---
async def sync_user_dialogs():
    await asyncio.sleep(5) # Tunggu koneksi stabil
    try:
        db = get_db()
        me = await app.get_me()
        user_id = str(me.id)

        if user_id in db["users"]:
            target_dict = db["users"][user_id].get("target_groups", {})
            
            # Ambil semua obrolan/grup tempat userbot bergabung
            async for dialog in app.get_dialogs():
                if dialog.chat.type.value in ["group", "supergroup"]:
                    chat_id = str(dialog.chat.id)
                    chat_title = dialog.chat.title
                    
                    if chat_id not in target_dict:
                        target_dict[chat_id] = {"name": chat_title, "active": False}
                    else:
                        target_dict[chat_id]["name"] = chat_title

            db["users"][user_id]["target_groups"] = target_dict
            save_db(db)
    except Exception as e:
        print(f"Sync error: {e}")

# --- 1. FITUR AUTO REPLY (WTB) DENGEN CEK TOGGLE GRUP ---
@app.on_message(filters.group & filters.text)
async def wtb_auto_reply(client, message):
    db = get_db()
    user_id = str(message.from_user.id)
    user_data = db["users"].get(user_id)
    
    if not user_data:
        return

    plan = user_data.get("plan", "none")
    target_dict = user_data.get("target_groups", {})
    chat_id = str(message.chat.id)

    # Hanya merespon jika paket WTB/Spesial DAN grup sudah di-toggle [✅] Aktif oleh User
    if plan in ["wtb", "spesial"]:
        if chat_id in target_dict and target_dict[chat_id].get("active", False):
            keywords = ["cari", "wtb", "butuh", "buy"]
            if any(word in message.text.lower() for word in keywords):
                if not message.from_user.is_self:
                    await message.reply_text("✅ Halo! Saya ada stok yang Anda cari. Silakan PM / Chat langsung ya.")

# --- 2. FITUR AUTO FORWARD (JASEB) DENGAN CEK TOGGLE GRUP ---
@app.on_message(filters.group & filters.text)
async def jaseb_auto_forward(client, message):
    db = get_db()
    user_id = str(message.from_user.id)
    user_data = db["users"].get(user_id)

    if not user_data:
        return

    plan = user_data.get("plan", "none")
    target_dict = user_data.get("target_groups", {})
    chat_id = str(message.chat.id)

    # Hanya merespon jika paket Jaseb/Spesial DAN grup sudah di-toggle [✅] Aktif
    if plan in ["jaseb", "spesial"]:
        if chat_id in target_dict and target_dict[chat_id].get("active", False):
            try:
                await message.forward("me")
            except Exception:
                pass

# --- TASK TIMER & BACKGROUND ---
async def timer_task():
    await sync_user_dialogs()
    while True:
        await asyncio.sleep(3600)

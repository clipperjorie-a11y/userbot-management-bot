import os, asyncio
from pyrogram import Client, filters
from database import get_db, save_db

API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")

active_clients = {}

async def start_userbot_sessions():
    db = get_db()
    users = db.get("users", {})

    for user_id, data in users.items():
        session_str = data.get("session")
        if session_str and user_id not in active_clients:
            try:
                cli = Client(f"ubot_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_str)
                register_handlers(cli, user_id)
                await cli.start()
                active_clients[user_id] = cli
                print(f"✅ Userbot Customer ID {user_id} berhasil diaktifkan.")
            except Exception as e:
                print(f"❌ Gagal memuat userbot {user_id}: {e}")

def register_handlers(cli: Client, user_id: str):
    @cli.on_message(filters.group & filters.text)
    async def handler(client, message):
        db = get_db()
        user_data = db["users"].get(user_id)
        if not user_data:
            return

        plan = user_data.get("plan", "none")
        target_dict = user_data.get("target_groups", {})
        chat_id = str(message.chat.id)

        # 1. AUTO REPLY WTB
        if plan in ["wtb", "spesial"]:
            if chat_id in target_dict and target_dict[chat_id].get("active", False):
                keywords = ["cari", "wtb", "butuh", "buy"]
                if any(word in message.text.lower() for word in keywords):
                    if not message.from_user.is_self:
                        await message.reply_text("✅ Halo! Saya ada stok yang Anda cari. Silakan PM / Chat langsung ya.")

        # 2. AUTO FORWARD JASEB
        if plan in ["jaseb", "spesial"]:
            if chat_id in target_dict and target_dict[chat_id].get("active", False):
                try:
                    await message.forward("me")
                except Exception:
                    pass

async def sync_all_dialogs():
    db = get_db()
    for user_id, cli in list(active_clients.items()):
        try:
            target_dict = db["users"][user_id].get("target_groups", {})
            async for dialog in cli.get_dialogs():
                if dialog.chat.type.value in ["group", "supergroup"]:
                    chat_id = str(dialog.chat.id)
                    chat_title = dialog.chat.title
                    if chat_id not in target_dict:
                        target_dict[chat_id] = {"name": chat_title, "active": False}
                    else:
                        target_dict[chat_id]["name"] = chat_title

            db["users"][user_id]["target_groups"] = target_dict
            save_db(db)
        except Exception:
            pass

async def timer_task():
    while True:
        await start_userbot_sessions()
        await sync_all_dialogs()
        await asyncio.sleep(30)
        

import os
import asyncio
import logging
from pyrogram import Client, filters
from database import get_db

logging.basicConfig(level=logging.INFO)

API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d"))

active_userbots = {}

async def handle_auto_replay(client, message):
    try:
        user_id = getattr(client, "owner_id", None)
        if not user_id: return
        db = get_db()
        st = db.get("users", {}).get(user_id, {}).get("settings", {})

        keywords = [k.strip().lower() for k in st.get("replay_kw", "").split(",") if k.strip()]
        banwords = [b.strip().lower() for b in st.get("replay_ban", "").split(",") if b.strip()]
        reply_text = st.get("replay_text", "")

        if not keywords or not reply_text: return

        text = (message.text or message.caption or "").lower()

        if any(b in text for b in banwords): return
        if any(k in text for k in keywords):
            await message.reply_text(reply_text)
            logging.info(f"Auto Replay sent by user {user_id}")
    except Exception as e:
        logging.error(f"Error Auto Replay: {e}")

async def start_userbot_session(user_id, session_str):
    if user_id in active_userbots:
        try: await active_userbots[user_id].stop()
        except Exception: pass

    ub = Client(f"ub_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_str, in_memory=True)
    ub.owner_id = str(user_id)

    @ub.on_message(filters.group & ~filters.me)
    async def msg_handler(c, m):
        await handle_auto_replay(c, m)

    await ub.start()
    active_userbots[user_id] = ub
    logging.info(f"✅ Userbot Active for User ID {user_id}")

async def start_all_userbots():
    db = get_db()
    for uid, data in db.get("users", {}).items():
        sess = data.get("session")
        if sess and data.get("plan") != "none":
            try:
                await start_userbot_session(uid, sess)
            except Exception as e:
                logging.error(f"Gagal restore userbot {uid}: {e}")

async def timer_task():
    while True:
        try:
            db = get_db()
            for uid, ub in list(active_userbots.items()):
                st = db.get("users", {}).get(uid, {}).get("settings", {})
                bc_text = st.get("bc_text")
                targets = st.get("bc_targets", [])
                delay = st.get("bc_delay", 5)

                if bc_text and targets:
                    for target in targets:
                        try:
                            await ub.send_message(target, bc_text)
                            await asyncio.sleep(delay)
                        except Exception as err:
                            logging.error(f"Gagal BC ke {target}: {err}")
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Error pada loop timer_task: {e}")
            await asyncio.sleep(10)
                                

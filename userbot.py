import os
import asyncio
import logging
from pyrogram import Client, filters
from datetime import datetime

logging.basicConfig(level=logging.INFO)

API_ID = int(os.getenv("API_ID", "36488953"))
API_HASH = os.getenv("API_HASH", "9ff7f56335f9859c5979a2a64cc5de7d")

active_userbots = {}

# === AUTO REPLY ENGINE ===
async def handle_auto_reply(client, message):
    """Handle Auto Reply dengan keyword matching"""
    try:
        user_id = getattr(client, "owner_id", None)
        if not user_id: return
        
        from database import get_db
        db = get_db()
        user = db.get("users", {}).get(str(user_id), {})
        st = user.get("settings", {})
        
        if not st.get("ar_enabled", False): return
        
        # Check ban words
        banwords = st.get("ar_banwords", [])
        text = (message.text or message.caption or "").lower()
        if any(b.strip().lower() in text for b in banwords if b.strip()):
            return
        
        # Check keywords
        keywords_list = st.get("ar_keywords", [])
        for kw_item in keywords_list:
            if not kw_item.get("enabled", True): continue
            
            keyword = kw_item.get("keyword", "").lower().strip()
            response = kw_item.get("response", "").strip()
            
            if keyword and keyword in text and response:
                try:
                    await message.reply_text(response)
                    logging.info(f"✅ AR sent: keyword={keyword}")
                except Exception as e:
                    logging.error(f"AR reply error: {e}")
                break
    except Exception as e:
        logging.error(f"Auto Reply Error: {e}")

# === AUTO FORWARD ENGINE ===
async def handle_auto_forward(client, message):
    """Handle Auto Forward dari channel ke grup"""
    try:
        user_id = getattr(client, "owner_id", None)
        if not user_id: return
        
        from database import get_db
        db = get_db()
        user = db.get("users", {}).get(str(user_id), {})
        st = user.get("settings", {})
        
        if not st.get("fw_enabled", False): return
        
        fw_source = st.get("fw_source_ch", "").strip()
        fw_targets = st.get("fw_targets", [])
        fw_delay = st.get("fw_delay", 5)
        
        if not fw_targets or not fw_source: return
        
        # Check jika message dari source channel
        chat_id = str(message.chat.id)
        chat_username = message.chat.username or ""
        
        if chat_id != fw_source and chat_username.lower() != fw_source.lower():
            return
        
        # Forward ke semua target
        for target_item in fw_targets:
            try:
                target = target_item if isinstance(target_item, str) else target_item.get("target")
                
                await message.forward(target)
                await asyncio.sleep(fw_delay)
                logging.info(f"✅ FW sent to {target}")
            except Exception as e:
                logging.error(f"FW to {target} failed: {e}")
    except Exception as e:
        logging.error(f"Auto Forward Error: {e}")

# === AUTO BROADCAST ENGINE ===
async def handle_auto_broadcast(client):
    """Handle Auto Broadcast ke multiple grup dengan jeda"""
    try:
        user_id = getattr(client, "owner_id", None)
        if not user_id: return
        
        from database import get_db
        db = get_db()
        user = db.get("users", {}).get(str(user_id), {})
        st = user.get("settings", {})
        
        if not st.get("bc_enabled", False): return
        
        bc_text = st.get("bc_text", "").strip()
        bc_targets = st.get("bc_targets", [])
        bc_delay = st.get("bc_delay", 5)
        
        if not bc_text or not bc_targets: return
        
        for target in bc_targets:
            try:
                await client.send_message(target.strip(), bc_text)
                await asyncio.sleep(bc_delay)
                logging.info(f"✅ BC sent to {target}")
            except Exception as e:
                logging.error(f"BC to {target} failed: {e}")
    except Exception as e:
        logging.error(f"Auto Broadcast Error: {e}")

# === CREATE & START USERBOT ===
async def create_userbot(user_id, session_str):
    """Create dan setup userbot instance"""
    user_id = str(user_id)
    
    # Stop jika sudah ada
    if user_id in active_userbots:
        try:
            await active_userbots[user_id].stop()
        except:
            pass
    
    # Buat instance baru
    ub = Client(
        f"ub_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_str,
        in_memory=True
    )
    ub.owner_id = user_id
    
    # Handler Auto Reply
    @ub.on_message(filters.group & ~filters.me)
    async def ar_handler(c, m):
        await handle_auto_reply(c, m)
    
    # Handler Auto Forward (di private chat juga)
    @ub.on_message(filters.channel & ~filters.me)
    async def fw_handler(c, m):
        await handle_auto_forward(c, m)
    
    # Start client
    await ub.start()
    logging.info(f"✅ Userbot started: {user_id}")
    
    return ub

# === START ALL ACTIVE USERBOTS ===
async def start_all_userbots():
    """Restore dan start semua active userbots"""
    try:
        from database import get_db
        db = get_db()
        
        for uid, user in db.get("users", {}).items():
            sess = user.get("session", "").strip()
            tier = user.get("tier", "none")
            
            if sess and tier != "none":
                try:
                    ub = await create_userbot(uid, sess)
                    active_userbots[uid] = ub
                except Exception as e:
                    logging.error(f"Failed to restore {uid}: {e}")
    except Exception as e:
        logging.error(f"Start all userbots error: {e}")

# === BACKGROUND TIMER TASK ===
async def timer_task():
    """Background task untuk Auto BC & periodic tasks"""
    while True:
        try:
            for uid, ub in list(active_userbots.items()):
                try:
                    # Run Auto BC every minute
                    await handle_auto_broadcast(ub)
                except Exception as e:
                    logging.error(f"Timer task error for {uid}: {e}")
            
            await asyncio.sleep(60)  # Check every 60 seconds
        except Exception as e:
            logging.error(f"Timer task crashed: {e}")
            await asyncio.sleep(10)

# === HELPER FUNCTIONS ===
async def stop_userbot(user_id):
    """Stop userbot untuk user tertentu"""
    user_id = str(user_id)
    if user_id in active_userbots:
        try:
            await active_userbots[user_id].stop()
            del active_userbots[user_id]
            logging.info(f"Userbot stopped: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Stop userbot error: {e}")
    return False

async def get_userbot_status(user_id):
    """Get status userbot user"""
    user_id = str(user_id)
    if user_id in active_userbots:
        ub = active_userbots[user_id]
        try:
            me = await ub.get_me()
            return {"status": "active", "user": me.first_name}
        except:
            return {"status": "offline"}
    return {"status": "not_started"}

def get_all_active_userbots():
    """Get semua active userbots list"""
    return list(active_userbots.keys())
        


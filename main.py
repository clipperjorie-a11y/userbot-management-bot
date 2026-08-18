import os
import asyncio
import logging
from aiohttp import web

# Import dari file bot.py dan userbot.py
from bot import app as bot_app
from userbot import timer_task

logging.basicConfig(level=logging.INFO)

# Dummy Web Server untuk Railway Port Health Check
async def handle_health_check(request):
    return web.Response(text="Userbot Controller is Running!")

async def start_services():
    # 1. Jalankan Engine Timer Userbot (Background Task)
    asyncio.create_task(timer_task())
    logging.info("🚀 Engine Timer Userbot Berjalan...")

    # 2. Start Bot Controller Utama (Pyrogram)
    await bot_app.start()
    logging.info("✅ Bot Controller Berhasil Menyala!")

    # 3. Jalankan Web Server untuk Railway PORT
    web_app = web.Application()
    web_app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Web Server Health Check berjalan di port {port}")

    # Menjaga agar seluruh service tetap aktif
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot dihentikan.")
        

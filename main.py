import os
import asyncio
import logging
from aiohttp import web
from bot import app as bot_app
from userbot import timer_task, start_all_userbots

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def handle_health_check(request):
    return web.Response(text="🚀 Userbot Controller & Engine is Running Perfectly!")

async def start_services():
    logging.info("Starting Bot Controller...")
    await bot_app.start()
    logging.info("✅ Bot Controller Started!")

    logging.info("Starting Active Userbots...")
    await start_all_userbots()

    logging.info("Starting Background Engine Task...")
    asyncio.create_task(timer_task())

    web_app = web.Application()
    web_app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Railway Port Server Active on Port {port}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_services())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot Stopped.")
        

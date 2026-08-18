import asyncio
from bot import app as bot_app
from userbot import app as ubot_app, timer_task

async def main():
    print("🚀 Running Bot Controller & Engine Userbot (Tombol Toggle Mode)...")
    await asyncio.gather(
        bot_app.start(),
        ubot_app.start(),
        timer_task()
    )
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
  

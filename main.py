import asyncio
from bot import app as bot_app
from userbot import timer_task

async def main():
    print("🚀 Running Bot Controller & Engine Userbot (Multi-Client OTP Mode)...")
    await asyncio.gather(
        bot_app.start(),
        timer_task()
    )
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    

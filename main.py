import asyncio
from userbot import timer_task

async def main():
    print("🚀 Running Userbot Bot Controller & Engine...")
    # Jalankan tugas latar belakang userbot
    await timer_task()

if __name__ == "__main__":
    asyncio.run(main())


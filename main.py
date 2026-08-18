import asyncio
from bot import app as bot_app
from userbot import timer_task

async def main():
    print("🚀 Running Bot Controller & Engine Userbot...")
    # Jalankan tugas latar belakang userbot
    asyncio.create_task(timer_task())
    # Jalankan bot controller utama
    await bot_app.start()
    print("✅ Bot Controller Berhasil Menyala!")
    # Jaga agar bot tetap berjalan
    await asyncio.Event().wait()

if __name__ == "__main__":
    bot_app.run()
    

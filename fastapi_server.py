from fastapi import FastAPI, Request, Response, status
from contextlib import asynccontextmanager
from telegram import Update
from config.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET
import database.database as db

def create_app(bot_app):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Botni ishga tushirish
        print("Ma'lumotlar bazasi tekshirilmoqda...")
        try:
            db.init_db()
            print("PostgreSQL bazasi tayyor!")
        except Exception as e:
            print(f"Baza bilan ulanishda xatolik yuz berdi: {e}")
            raise e

        if WEBHOOK_URL:
            # Webhookni Telegramga o'rnatish
            await bot_app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/telegram",
                secret_token=WEBHOOK_SECRET
            )
            print(f"Webhook o'rnatildi: {WEBHOOK_URL}")
        
        await bot_app.initialize()
        await bot_app.start()
        
        yield
        
        # Botni to'xtatish
        await bot_app.stop()
        await bot_app.shutdown()

    app = FastAPI(lifespan=lifespan)

    @app.post(f"/telegram")
    async def process_update(request: Request):
        if WEBHOOK_SECRET:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if token != WEBHOOK_SECRET:
                return Response(status_code=status.HTTP_403_FORBIDDEN)

        update_data = await request.json()
        update = Update.de_json(update_data, bot_app.bot)
        await bot_app.process_update(update)
        return Response(status_code=status.HTTP_200_OK)

    @app.get("/")
    async def index():
        return {"status": "Bot is running", "api": "FastAPI"}

    return app

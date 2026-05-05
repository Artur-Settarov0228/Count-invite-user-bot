import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
import uvicorn
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from config.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT, WEBHOOK_LISTEN, WEBHOOK_SECRET
import database.database as db
from handlers import handlers

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Application obyektini yaratish
bot_app = Application.builder().token(BOT_TOKEN).build()

# Handlerlarni qo'shish
bot_app.add_handler(CommandHandler("start", handlers.start))
bot_app.add_handler(CommandHandler("stat", handlers.stat))
bot_app.add_handler(CommandHandler("top", handlers.top))
bot_app.add_handler(CallbackQueryHandler(handlers.check_sub_callback, pattern="^check_sub$"))
bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handlers.track_invites))

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

# FastAPI ilovasini yaratish
app = FastAPI(lifespan=lifespan)

@app.post("/telegram")
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

if __name__ == '__main__':
    if WEBHOOK_URL:
        print(f"Bot FastAPI (Webhook) rejimida ishga tushmoqda: {WEBHOOK_URL}")
        uvicorn.run(app, host=WEBHOOK_LISTEN, port=WEBHOOK_PORT)
    else:
        print("WEBHOOK_URL topilmadi. Polling rejimida ishga tushmoqda...")
        bot_app.run_polling(drop_pending_updates=True)
import logging
import uvicorn
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from config.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT, WEBHOOK_LISTEN
from fastapi_server import create_app
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

withdraw_handler = ConversationHandler(
    entry_points=[CommandHandler("money", handlers.money_start)],
    states={
        handlers.AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_amount)],
        handlers.DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_details)],
    },
    fallbacks=[CommandHandler("cancel", handlers.cancel)],
)
bot_app.add_handler(withdraw_handler)
bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handlers.track_invites))

# FastAPI ilovasini yaratish
app = create_app(bot_app)

if __name__ == '__main__':
    if WEBHOOK_URL:
        # FastAPI orqali Webhook rejimida ishga tushirish
        print(f"Bot FastAPI (Webhook) rejimida ishga tushmoqda: {WEBHOOK_URL}")
        uvicorn.run(app, host=WEBHOOK_LISTEN, port=WEBHOOK_PORT)
    else:
        # Agar URL yo'q bo'lsa, Polling rejimida ishga tushirish
        print("WEBHOOK_URL topilmadi. Polling rejimida ishga tushmoqda...")
        bot_app.run_polling(drop_pending_updates=True)
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from config.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT, WEBHOOK_LISTEN, WEBHOOK_SECRET
import database.database as db
from handlers import handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    print("Ma'lumotlar bazasi tekshirilmoqda...")
    try:
        db.init_db()
        print("PostgreSQL bazasi tayyor!")
    except Exception as e:
        print(f"Baza bilan ulanishda xatolik yuz berdi: {e}")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("stat", handlers.stat))
    app.add_handler(CommandHandler("top", handlers.top))
    app.add_handler(CallbackQueryHandler(handlers.check_sub_callback, pattern="^check_sub$"))
    

    # 5. Yangi odam qo'shilganini tutib oluvchi handler
    # filters.StatusUpdate.NEW_CHAT_MEMBERS aynan guruhga odam qo'shilgan eventni ushlaydi
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handlers.track_invites))

    # 5. Botni ishga tushirish
    print("Bot muvaffaqiyatli ishga tushdi...")

    if WEBHOOK_URL:
        # Webhook rejimi
        print(f"Webhook rejimida ishga tushmoqda: {WEBHOOK_URL}")
        app.run_webhook(
            listen=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            secret_token=WEBHOOK_SECRET
        )
    else:
        # Polling rejimi (agar URL berilmagan bo'lsa)
        print("Polling rejimida ishga tushmoqda...")
        app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from config.config import BOT_TOKEN
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
    
    # 4. Pul yechish (Withdrawal) conversation
    withdraw_handler = ConversationHandler(
        entry_points=[CommandHandler("money", handlers.money_start)],
        states={
            handlers.AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_amount)],
            handlers.DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.get_details)],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)],
    )
    app.add_handler(withdraw_handler)

    # 5. Yangi odam qo'shilganini tutib oluvchi handler
    # filters.StatusUpdate.NEW_CHAT_MEMBERS aynan guruhga odam qo'shilgan eventni ushlaydi
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handlers.track_invites))

    # 5. Botni ishga tushirish
    print("Bot muvaffaqiyatli ishga tushdi. Telegramdan xabarlar kutilyapti...")
    
    # drop_pending_updates=True bot o'chiq vaqtida kelgan eski xabarlarni o'qimasligini ta'minlaydi
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
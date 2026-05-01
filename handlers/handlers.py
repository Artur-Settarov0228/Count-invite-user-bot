# handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
import logging
import database.database as db

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    chat_type = update.effective_chat.type

    if chat_type == 'private':
        # userni bazaga qo‘shamiz
        db.add_user(user.id, user.username, user.first_name)

        await update.message.reply_text(
            f"Salom, {user.first_name}! 🚀\n\n"
            f"Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz.\n"
            f"Meni guruhga qo‘shib admin qilsangiz, kim nechta odam qo‘shganini hisoblayman 📊"
        )
    else:
        await update.message.reply_text(
            "Salom! Men invite hisoblovchi botman 📊"
        )


async def track_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message or not message.new_chat_members:
        return

    inviter = message.from_user
    chat = update.effective_chat

    for new_member in message.new_chat_members:

        # botlarni va self-joinni skip qilamiz
        if (
            new_member.is_bot or
            inviter.id == new_member.id or
            new_member.id == context.bot.id
        ):
            continue

        try:
            # inviterni saqlaymiz
            db.add_user(inviter.id, inviter.username, inviter.first_name)

            # duplicate check (agar funksiya bo‘lsa)
            if hasattr(db, "invite_exists"):
                if db.invite_exists(inviter.id, new_member.id, chat.id):
                    continue

            # invite qo‘shamiz
            db.add_invite(inviter.id, new_member.id, chat.id)

            logger.info(
                f"{inviter.id} invited {new_member.id} in {chat.id}"
            )

        except Exception as e:
            logger.error(f"Invite saqlashda xato: {e}")


async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat

    if chat.type == 'private':
        await update.message.reply_text(
            "Bu buyruq faqat guruhlarda ishlaydi ❌"
        )
        return

    try:
        count = db.get_user_stat(user.id, chat.id)
    except Exception as e:
        logger.error(f"Stat olishda xato: {e}")
        count = 0

    safe_name = escape_markdown(user.first_name, version=2)

    await update.message.reply_text(
        f"📊 {safe_name}, siz {count} ta odam qo‘shgansiz",
        parse_mode='MarkdownV2'
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat = update.effective_chat

    if chat.type == 'private':
        await update.message.reply_text(
            "Bu buyruq faqat guruhlarda ishlaydi ❌"
        )
        return

    try:
        results = db.get_top_inviters(chat.id)
    except Exception as e:
        logger.error(f"Top olishda xato: {e}")
        results = []

    if not results:
        await update.message.reply_text(
            "Hali hech kim odam qo‘shmagan 🤷‍♂️"
        )
        return

    text = "🏆 Eng ko‘p odam qo‘shganlar:\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for index, (name, count) in enumerate(results, start=1):
        medal = medals[index - 1] if index <= 3 else "🔹"
        display_name = name if name else "Noma'lum"

        text += f"{medal} {index}. {display_name} — {count} ta\n"

    await update.message.reply_text(text)
# handlers.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from telegram.helpers import escape_markdown
import logging
import database.database as db
from config.config import REQUIRED_CHANNELS, CHANNEL_URLS

logger = logging.getLogger(__name__)

# Conversation states
AMOUNT, DETAILS = range(2)




async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Foydalanuvchi barcha majburiy kanallarga a'zo ekanligini tekshiradi."""
    if not REQUIRED_CHANNELS:
        return True
        
    for channel_id in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            logger.info(f"User {user_id} status in {channel_id}: {member.status}")
            if member.status not in ['creator', 'administrator', 'member', 'restricted']:
                return False
        except Exception as e:
            logger.error(f"Obunani tekshirishda xato ({channel_id}): {e}")
            # Agar bot kanalni topolmasa yoki admin bo'lmasa, False qaytaradi
            return False
            
    return True


async def send_subscription_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchiga obuna bo'lish haqida xabar yuboradi."""
    keyboard = []
    for index, url in enumerate(CHANNEL_URLS, start=1):
        keyboard.append([InlineKeyboardButton(f"{index} - kanal ↗️", url=url)])
    
    keyboard.append([InlineKeyboardButton("Tekshirish ✅", callback_data="check_sub")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "Botdan foydalanish uchun ⚠️\n"
        "Iltimos quyidagi kanallarga obuna bo'ling ‼️"
    )
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    chat_type = update.effective_chat.type

    if chat_type == 'private':
        # 🛑 Majburiy obuna tekshiruvi (faqat agar oldin ro'yxatdan o'tgan bo'lsa yoki har doim)
        # Foydalanuvchi birinchi marta kelsa ham obuna bo'lishini so'raymiz
        is_subscribed = await check_subscription(user.id, context)
        
        # userni bazaga qo‘shamiz
        db.add_user(user.id, user.username, user.first_name)

        if not is_subscribed:
            await update.message.reply_text(
                f"Salom, {user.first_name}! 🚀\n\n"
                f"Botdan foydalanish uchun kanallarimizga a'zo bo'lishingiz kerak."
            )
            await send_subscription_prompt(update, context)
            return

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

    # 1. Guruhni bazaga qo'shamiz (foreign key uchun kerak)
    db.add_chat(chat.id, chat.title)
    
    # 2. Taklif qiluvchini bazaga qo'shamiz
    db.add_user(inviter.id, inviter.username, inviter.first_name)

    added_count = 0
    added_names = []
    for new_member in message.new_chat_members:
        # botlarni va self-joinni skip qilamiz
        if (
            new_member.is_bot or
            inviter.id == new_member.id or
            new_member.id == context.bot.id
        ):
            continue

        try:
            # 3. Yangi a'zoni bazaga qo'shamiz (foreign key uchun kerak)
            db.add_user(new_member.id, new_member.username, new_member.first_name)

            # duplicate check
            if hasattr(db, "invite_exists"):
                if db.invite_exists(inviter.id, new_member.id, chat.id):
                    continue

            # 4. Invite qo‘shamiz
            db.add_invite(inviter.id, new_member.id, chat.id)
            added_count += 1
            added_names.append(new_member.first_name if new_member.first_name else "Nomsiz")

            logger.info(
                f"{inviter.id} invited {new_member.id} in {chat.id}"
            )

        except Exception as e:
            logger.error(f"Invite saqlashda xato: {e}")
            
    # Agar haqiqatda yangi odam qo'shilgan bo'lsa, adminga xabar beramiz
    if added_count > 0:
        from config.config import ADMIN_ID
        if ADMIN_ID:
            try:
                total_invites = db.get_user_stat(inviter.id, chat.id)
                safe_name = escape_markdown(inviter.first_name if inviter.first_name else "Foydalanuvchi", version=2)
                added_users_str = escape_markdown(", ".join(added_names), version=2)
                
                admin_text = (
                    f"🔔 *Yangi taklif\\!*\n\n"
                    f"👤 *Foydalanuvchi:* {safe_name} \\([`{inviter.id}`](tg://user?id={inviter.id})\\)\n"
                    f"👥 *Guruhga qo'shdi:* {added_count} ta odam\n"
                    f"🆕 *Qo'shilganlar:* {added_users_str}\n"
                    f"📊 *Umumiy hisobi:* {total_invites} ta"
                )
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode='MarkdownV2')
            except Exception as e:
                logger.error(f"Adminga taklif xabarini yuborishda xato: {e}")


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

    # 🛑 Majburiy obuna tekshiruvi
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await send_subscription_prompt(update, context)
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

    user = update.effective_user
    chat = update.effective_chat

    if chat.type == 'private':
        await update.message.reply_text(
            "Bu buyruq faqat guruhlarda ishlaydi ❌"
        )
        return

    # 🛑 Majburiy obuna tekshiruvi
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await send_subscription_prompt(update, context)
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

    text = "🏆 *Eng ko‘p odam qo‘shganlar:*\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for index, (first_name, username, count) in enumerate(results, start=1):
        medal = medals[index - 1] if index <= 3 else "🔹"
        
        # Ismni escape qilamiz
        safe_name = escape_markdown(first_name if first_name else "Noma'lum", version=2)
        
        text += f"{medal} {index}\\. {safe_name} — *{count}* ta\n"

    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'Tekshirish' tugmasi bosilganda ishlaydi."""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer("Tekshirilmoqda...")
    
    is_subscribed = await check_subscription(user_id, context)
    
    if is_subscribed:
        await query.edit_message_text(
            "Tabriklaymiz! ✅\n"
            "Siz barcha kanallarga a'zo bo'ldingiz. Endi buyruqlarni qaytadan yuborishingiz mumkin."
        )
    else:
        keyboard = []
        for index, url in enumerate(CHANNEL_URLS, start=1):
            keyboard.append([InlineKeyboardButton(f"{index} - kanal ↗️", url=url)])
        
        keyboard.append([InlineKeyboardButton("Tekshirish ✅", callback_data="check_sub")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Matn o'zgarmagan bo'lsa edit_message_text xato beradi, shuning uchun try-except
            await query.edit_message_text(
                "Botdan foydalanish uchun ⚠️\n"
                "Iltimos quyidagi kanallarga obuna bo'ling ‼️\n\n"
                "❌ Siz hali hamma kanallarga a'zo bo'lmadingiz!",
                reply_markup=reply_markup
            )
        except Exception:
            pass



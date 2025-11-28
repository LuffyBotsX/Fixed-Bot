# utils.py
# Utility functions for Era Escrow Bot

from telegram import ChatMember
from telegram.constants import ParseMode
from datetime import datetime, timedelta, timezone

# India Time Offset
IST_OFFSET = timedelta(hours=5, minutes=30)

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# =====================================================
# 🕒 GET CURRENT IST TIME
# =====================================================

def ist_now():
    return datetime.now(timezone.utc) + IST_OFFSET


def ist_format(ts: str):
    """
    Convert ISO timestamp to readable IST time.
    """
    try:
        dt = datetime.fromisoformat(ts)
        dt = dt + IST_OFFSET
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except:
        return ts


# =====================================================
# 🧑 FORMAT USERNAME
# =====================================================

def format_username(user):
    if getattr(user, "username", None):
        return f"@{user.username}"
    if getattr(user, "first_name", None):
        return user.first_name
    return str(user.id)


# =====================================================
# 🛡 ENSURE BOT IS ADMIN IN GROUP
# =====================================================

async def ensure_bot_admin(update, context):
    """
    Ensures bot is admin before running group commands.
    If not admin → block command + show message.
    """
    chat = update.effective_chat
    bot_id = context.bot.id

    member = await context.bot.get_chat_member(chat.id, bot_id)

    if member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        await update.message.reply_text(
            "❌ *I must be an Admin in this group to manage deals.*\n\n"
            "Please grant me permissions:\n"
            "• Delete messages\n"
            "• Manage messages\n"
            "• Read all messages",
            parse_mode=ParseMode.MARKDOWN
        )
        return False

    return True


# =====================================================
# ❓ UNKNOWN COMMAND HANDLER
# =====================================================

async def unknown_cmd_handler(update, context):
    await update.message.reply_text(
        "❓ Unknown command.\nType /cmds if you are an admin.",
        parse_mode=ParseMode.MARKDOWN
    )

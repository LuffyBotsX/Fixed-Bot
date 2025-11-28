# utils.py
# Utility functions for Era Escrow Bot

from telegram import ChatMember
from telegram.constants import ParseMode
from datetime import datetime, timedelta, timezone

# Divider for UI
DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# India Time Offset
IST_OFFSET = timedelta(hours=5, minutes=30)


# ============================================================
# 🕒 Get Current IST Time
# ============================================================

def ist_now():
    """
    Returns current IST datetime object.
    """
    return datetime.now(timezone.utc) + IST_OFFSET


def ist_format(timestamp: str):
    """
    Convert ISO timestamp to readable IST time format.
    """
    try:
        dt = datetime.fromisoformat(timestamp)
        dt = dt + IST_OFFSET
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except:
        return timestamp


# ============================================================
# 🧑 Format Username
# ============================================================

def format_username(user):
    """
    Converts user object to @username or first name.
    """
    if getattr(user, "username", None):
        return f"@{user.username}"
    if getattr(user, "first_name", None):
        return user.first_name
    return str(user.id)


# ============================================================
# 🛡 Ensure Bot is Admin in Group
# ============================================================

async def ensure_bot_admin(update, context):
    """
    Check if bot is admin before performing group actions.
    """
    chat = update.effective_chat
    bot_id = context.bot.id

    try:
        member = await context.bot.get_chat_member(chat.id, bot_id)
    except:
        return False

    if member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
        await update.message.reply_text(
            "❌ *I must be an Admin in this group to manage deals.*\n\n"
            "Please enable permissions:\n"
            "• Delete messages\n"
            "• Manage messages\n"
            "• Read all messages",
            parse_mode=ParseMode.MARKDOWN
        )
        return False

    return True


# ============================================================
# ✉️ Clean Reply + Delete Command
# ============================================================

async def reply_and_clean(message, text, parse_mode=ParseMode.MARKDOWN):
    """
    Replies to user's message OR the replied message,
    then deletes the command message safely.
    """
    try:
        target = message.reply_to_message or message
        await target.reply_text(text, parse_mode=parse_mode)
        await message.delete()
    except:
        # If delete fails, still respond
        await message.reply_text(text, parse_mode=parse_mode)


# ============================================================
# ❓ Unknown Command
# ============================================================

async def unknown_cmd_handler(update, context):
    """
    Handles unknown commands.
    """
    await update.message.reply_text(
        "❓ Unknown command.\nType /cmds if you're an admin.",
        parse_mode=ParseMode.MARKDOWN
    )

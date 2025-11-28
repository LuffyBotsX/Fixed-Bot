# handlers/logs.py
# Logging system for Era Escrow Bot
# Allows owner/admin to set channels for logging deal actions, bans, notes etc.

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import connect
from utils import DIVIDER, format_username

OWNER_ID = 6847499628


# ============================================================
# 🔧 INTERNAL: SEND LOG MESSAGE
# ============================================================

async def send_log(context, log_chat_id: int, text: str):
    """
    Called by other handlers to send log messages safely.
    """
    if not log_chat_id:
        return  # No log channel configured
    try:
        await context.bot.send_message(
            chat_id=log_chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass


# ============================================================
# 🆔 /chatid — Display current chat ID
# ============================================================

async def chatid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    await update.message.reply_text(
        f"🆔 *Chat ID:* `{chat.id}`",
        parse_mode="Markdown"
    )


# ============================================================
# 📝 /setlogs — Set Logging Channel
# ============================================================

async def set_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id != OWNER_ID:
        return await update.message.reply_text("⛔ *Owner only command!*", parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text("Usage: `/setlogs <chat_id>`", parse_mode="Markdown")

    chat_id = context.args[0]

    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT OR REPLACE INTO logs (id, chat_id) VALUES (1, ?)", (chat_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "📡 Logging channel updated successfully!",
        parse_mode="Markdown"
    )


# ============================================================
# ❌ /removelogs — Disable logging
# ============================================================

async def remove_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id != OWNER_ID:
        return await update.message.reply_text("⛔ *Owner only command!*", parse_mode="Markdown")

    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM logs WHERE id=1")
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "🧹 Logging disabled!",
        parse_mode="Markdown"
    )


# ============================================================
# 📄 /tlogs — Show current logging channel
# ============================================================

async def show_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT chat_id FROM logs WHERE id=1")
    row = cur.fetchone()

    conn.close()

    if not row:
        return await update.message.reply_text("ℹ️ Logging is currently disabled.")

    await update.message.reply_text(
        f"📡 *Current Logging Channel:* `{row['chat_id']}`",
        parse_mode="Markdown"
    )


# ============================================================
# 🧪 /test — Send a test log message
# ============================================================

async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT chat_id FROM logs WHERE id=1")
    row = cur.fetchone()

    conn.close()

    if not row:
        return await update.message.reply_text("⚠️ Logging is disabled.")

    log_id = row["chat_id"]

    await send_log(context, log_id, "🧪 *Log Test Successful!*")

    await update.message.reply_text(
        "✔️ Test log sent.",
        parse_mode="Markdown"
    )

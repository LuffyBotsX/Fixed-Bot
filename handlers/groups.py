# handlers/groups.py
# Group linking, welcome system, farewell system.

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import connect
from utils import DIVIDER, format_username


# ============================================================
# 🔗 /setgroup — Register a group
# ============================================================

async def set_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        return await update.message.reply_text("❗ This command can only be used in groups.")

    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR REPLACE INTO groups (chat_id, welcome_enabled) VALUES (?, ?)",
        (chat.id, 1),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Group successfully registered.\n\n"
        f"Chat ID: `{chat.id}`",
        parse_mode="Markdown"
    )


# ============================================================
# ❌ /removegroup — Unregister group
# ============================================================

async def remove_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM groups WHERE chat_id=?", (chat.id,))
    conn.commit()
    conn.close()

    await update.message.reply_text("❌ Group removed from system.")


# ============================================================
# 📋 /groups — List all registered groups
# ============================================================

async def groups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT chat_id, welcome_enabled FROM groups")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No groups registered.")

    text = "📋 *Registered Groups*\n" + DIVIDER + "\n\n"

    for g in rows:
        status = "🟢 ON" if g["welcome_enabled"] else "🔴 OFF"
        text += f"• `{g['chat_id']}` — {status}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 👋 /setwelcome — Update welcome message
# ============================================================

async def set_welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage:\n`/setwelcome Welcome {user}!`", parse_mode="Markdown")

    chat = update.effective_chat
    text = " ".join(context.args)

    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "UPDATE groups SET welcome_message=? WHERE chat_id=?",
        (text, chat.id)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("✨ Welcome message updated!")


# ============================================================
# 👋 /setfarewell — Update farewell message
# ============================================================

async def set_farewell_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "Usage:\n`/setfarewell Goodbye {user}!`",
            parse_mode="Markdown"
        )

    chat = update.effective_chat
    text = " ".join(context.args)

    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "UPDATE groups SET farewell_message=? WHERE chat_id=?",
        (text, chat.id)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("✨ Farewell message updated!")


# ============================================================
# 🔁 /togglewelcome — Enable/Disable welcome/farewell
# ============================================================

async def toggle_welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT welcome_enabled FROM groups WHERE chat_id=?", (chat.id,))
    row = cur.fetchone()

    if not row:
        return await update.message.reply_text("❗ Group not registered. Use /setgroup first.")

    new_status = 0 if row["welcome_enabled"] else 1

    cur.execute(
        "UPDATE groups SET welcome_enabled=? WHERE chat_id=?",
        (new_status, chat.id)
    )
    conn.commit()
    conn.close()

    status_text = "🟢 Enabled" if new_status else "🔴 Disabled"

    await update.message.reply_text(f"Welcome system {status_text}!")


# ============================================================
# 🤝 AUTO-WELCOME
# ============================================================

async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    member = update.message.new_chat_members[0]

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT welcome_message, welcome_enabled FROM groups WHERE chat_id=?", (chat.id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row["welcome_enabled"]:
        return

    text = row["welcome_message"] or "👋 Welcome {user}!"
    text = text.replace("{user}", format_username(member))

    await update.message.reply_text(text)


# ============================================================
# 👋 AUTO-FAREWELL
# ============================================================

async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    member = update.message.left_chat_member

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT farewell_message, welcome_enabled FROM groups WHERE chat_id=?", (chat.id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row["welcome_enabled"]:
        return

    text = row["farewell_message"] or "👋 Goodbye {user}!"
    text = text.replace("{user}", format_username(member))

    await update.message.reply_text(text)

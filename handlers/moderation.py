# handlers/moderation.py
# All moderation features: warnings, bans, mute, kick, notes etc.

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import connect
from utils import format_username, DIVIDER


# ============================================================
# ⚠️ /warn — Give a warning
# ============================================================

async def warn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/warn @user`", parse_mode="Markdown")

    target = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT INTO warns (username) VALUES (?)", (target,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"⚠️ Warning added to {target}.",
        parse_mode="Markdown"
    )


# ============================================================
# 🧹 /dwarn — Remove 1 warning
# ============================================================

async def unwarn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/dwarn @user`", parse_mode="Markdown")

    user = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM warns WHERE username=? LIMIT 1", (user,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🧹 One warning removed from {user}.",
        parse_mode="Markdown"
    )


# ============================================================
# 📊 /warns — View user warnings
# ============================================================

async def warns_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Usage: `/warns @user`", parse_mode="Markdown")

    user = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM warns WHERE username=?", (user,))
    row = cur.fetchone()
    conn.close()

    count = row["c"]

    await update.message.reply_text(
        f"📊 {user} has `{count}` warnings.",
        parse_mode="Markdown"
    )


# ============================================================
# 🚫 /ban — Ban user
# ============================================================

async def ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Usage: `/ban @user`")

    user = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO bans (username) VALUES (?)", (user,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🚫 {user} has been *banned*.",
        parse_mode="Markdown"
    )


# ============================================================
# 🔓 /unban — Remove ban
# ============================================================

async def unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Usage: `/unban @user`")

    user = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM bans WHERE username=?", (user,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🔓 {user} has been *unbanned*.",
        parse_mode="Markdown"
    )


# ============================================================
# 👢 /kick — Kick from group
# ============================================================

async def kick_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return await msg.reply_text("Reply to a message to kick that user.")

    user = msg.reply_to_message.from_user

    try:
        await msg.chat.ban_member(user.id)
        await msg.chat.unban_member(user.id)  # Instant kick
        await msg.reply_text(f"👢 Kicked {format_username(user)}")
    except:
        await msg.reply_text("❗ Failed to kick user.")


# ============================================================
# 🔇 /mute — Mute user
# ============================================================

async def mute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return await msg.reply_text("Reply to a message to mute that user.")

    user = msg.reply_to_message.from_user

    try:
        await msg.chat.restrict_member(user.id, permissions={"can_send_messages": False})
        await msg.reply_text(f"🔇 Muted {format_username(user)}")
    except:
        await msg.reply_text("❗ Failed to mute user.")


# ============================================================
# 🔊 /unmute — Unmute user
# ============================================================

async def unmute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return await msg.reply_text("Reply to unmute that user.")

    user = msg.reply_to_message.from_user

    try:
        await msg.chat.restrict_member(user.id, permissions={"can_send_messages": True})
        await msg.reply_text(f"🔊 Unmuted {format_username(user)}")
    except:
        await msg.reply_text("❗ Failed to unmute user.")


# ============================================================
# 🕵️ /info — Get user info
# ============================================================

async def info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user

    text = (
        "🧾 *User Info*\n"
        f"{DIVIDER}\n"
        f"• Username: {format_username(user)}\n"
        f"• ID: `{user.id}`\n"
        f"• Is Bot: `{user.is_bot}`\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📝 /save <note>
# ============================================================

async def save_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return await msg.reply_text("Reply to a user to save a note.")

    if not context.args:
        return await msg.reply_text("Usage: `/save some text`")

    user = msg.reply_to_message.from_user
    note_text = " ".join(context.args)

    conn = connect()
    cur = conn.cursor()

    cur.execute("INSERT INTO notes (user_id, note) VALUES (?, ?)", (user.id, note_text))
    conn.commit()
    conn.close()

    await msg.reply_text(f"📝 Note saved for {format_username(user)}")


# ============================================================
# 📒 /notes — Show notes
# ============================================================

async def notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return await msg.reply_text("Reply to a user to show notes.")

    user = msg.reply_to_message.from_user

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT note FROM notes WHERE user_id=?", (user.id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await msg.reply_text("ℹ️ No notes for this user.")

    txt = f"📒 *Notes for {format_username(user)}*\n{DIVIDER}\n\n"

    for n in rows:
        txt += f"• {n['note']}\n"

    await msg.reply_text(txt, parse_mode="Markdown")


# ============================================================
# 🧹 /clean_warns — Delete all warnings
# ============================================================

async def clean_warns_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/clean_warns @user`")

    user = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM warns WHERE username=?", (user,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🧹 All warnings cleared for {user}.",
        parse_mode="Markdown"
    )


# ============================================================
# 🧹 /clean_notes — Delete all notes
# ============================================================

async def clean_notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return await msg.reply_text("Reply to user to clean notes.")

    user = msg.reply_to_message.from_user

    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE user_id=?", (user.id,))
    conn.commit()
    conn.close()

    await msg.reply_text(f"🧹 All notes removed for {format_username(user)}")

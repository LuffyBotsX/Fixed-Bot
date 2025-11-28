# handlers/deals.py
# Deal creation, refund, close, cancel, status, and summary handlers

import random
import re
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils import (
    ist_now,
    ist_format,
    ensure_bot_admin,
    format_username,
    reply_and_clean
)

from database import (
    connect,
    get_fee
)

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# ================================================================
# 🔢 GENERATE TRADE ID
# ================================================================

def generate_trade_id():
    return f"TID{random.randint(100000, 999999)}"


# ================================================================
# 💬 Extract usernames from text (Buyer/Seller)
# ================================================================

def extract_user(text: str, key: str):
    pattern = rf"{key}\s*[:\-]\s*(@\w+)"
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None


# ================================================================
# 💵 Extract Amount (supports: 100, 1k, 2.5k, 1m etc)
# ================================================================

def parse_amount(amount_str: str):
    if not amount_str:
        return None

    s = amount_str.replace(",", "").lower()

    # Pattern
    m = re.match(r"(\d+(?:\.\d+)?)([km]?)", s)

    if not m:
        return None

    value = float(m.group(1))
    suffix = m.group(2)

    if suffix == "k":
        value *= 1000
    elif suffix == "m":
        value *= 1_000_000

    return value


# ================================================================
# 🟩 ADD DEAL /add <amount>
# ================================================================

async def add_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    msg = update.message
    if not msg.reply_to_message:
        return await msg.reply_text(
            "❗ Reply to DEAL INFO message first.\nExample:\n/add 1500",
            parse_mode="Markdown"
        )

    if not context.args:
        return await msg.reply_text("Usage: `/add <amount>`", parse_mode="Markdown")

    # Amount
    amount = parse_amount(context.args[0])
    if not amount:
        return await msg.reply_text("❗ Invalid amount.", parse_mode="Markdown")

    # Extract Buyer/Seller
    source = msg.reply_to_message.text or ""
    buyer = extract_user(source, "buyer")
    seller = extract_user(source, "seller")

    if not buyer or not seller:
        return await msg.reply_text(
            "❗ Could not detect Buyer/Seller in message.",
            parse_mode="Markdown"
        )

    trade_id = generate_trade_id()

    conn = connect()
    cur = conn.cursor()

    now = ist_now().isoformat()
    admin_user = update.effective_user

    # Fees
    percent, min_fee = get_fee()
    fee = max((amount * percent) / 100, min_fee)
    admin_earning = fee

    # Save
    cur.execute("""
        INSERT INTO deals (
            trade_id, buyer_username, seller_username,
            created_by, created_by_username,
            amount, fee, admin_earning,
            status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade_id, buyer, seller,
        admin_user.id, format_username(admin_user),
        amount, fee, admin_earning,
        "active", now, now
    ))

    conn.commit()
    conn.close()

    text = (
        "💼 *New Escrow Deal Created*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: `#{trade_id}`\n"
        f"• Buyer: {buyer}\n"
        f"• Seller: {seller}\n"
        f"• Amount: ₹{amount:.2f}\n"
        f"• Fee: ₹{fee:.2f}\n"
        f"• Escrower: {format_username(admin_user)}\n"
    )

    await reply_and_clean(update, text)


# ================================================================
# 🟦 CLOSE DEAL /close <tradeid>
# ================================================================

async def close_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/close <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].upper().replace("#", "")

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deals WHERE trade_id=?", (trade_id,))
    deal = cur.fetchone()

    if not deal:
        return await msg.reply_text("❗ No such Trade ID.", parse_mode="Markdown")

    if deal["status"] != "active":
        return await msg.reply_text(
            f"ℹ️ Deal already `{deal['status']}`.",
            parse_mode="Markdown"
        )

    now = ist_now().isoformat()

    cur.execute("UPDATE deals SET status='released', updated_at=? WHERE trade_id=?", (now, trade_id))
    conn.commit()
    conn.close()

    txt = (
        "✅ *Funds Released*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: `#{trade_id}`\n"
        f"• Buyer: {deal['buyer_username']}\n"
        f"• Seller: {deal['seller_username']}\n"
        f"• Amount: ₹{deal['amount']:.2f}\n"
        f"• Status: released\n"
    )

    await reply_and_clean(update, txt)


# ================================================================
# 🟥 REFUND DEAL /refund <tradeid>
# ================================================================

async def refund_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/refund <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].upper().replace("#", "")

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deals WHERE trade_id=?", (trade_id,))
    deal = cur.fetchone()

    if not deal:
        return await msg.reply_text("❗ Invalid Trade ID.", parse_mode="Markdown")

    if deal["status"] != "active":
        return await msg.reply_text(
            f"ℹ️ Deal already `{deal['status']}`.",
            parse_mode="Markdown"
        )

    now = ist_now().isoformat()

    cur.execute("UPDATE deals SET status='refunded', updated_at=? WHERE trade_id=?", (now, trade_id))
    conn.commit()
    conn.close()

    txt = (
        "♻️ *Deal Refunded*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: `#{trade_id}`\n"
        f"• Amount: ₹{deal['amount']:.2f}\n"
        f"• Buyer: {deal['buyer_username']}\n"
        f"• Seller: {deal['seller_username']}\n"
    )

    await reply_and_clean(update, txt)


# ================================================================
# 🛑 CANCEL DEAL /cancel <tradeid>
# ================================================================

async def cancel_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/cancel <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].upper().replace("#", "")

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deals WHERE trade_id=?", (trade_id,))
    deal = cur.fetchone()

    if not deal:
        return await msg.reply_text("❗ Invalid Trade ID.", parse_mode="Markdown")

    if deal["status"] != "active":
        return await msg.reply_text(
            f"ℹ️ Deal already `{deal['status']}`.",
            parse_mode="Markdown"
        )

    now = ist_now().isoformat()
    cur.execute("UPDATE deals SET status='cancelled', updated_at=? WHERE trade_id=?", (now, trade_id))

    conn.commit()
    conn.close()

    txt = (
        "❌ *Deal Cancelled*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: `#{trade_id}`\n"
        f"• Amount: ₹{deal['amount']:.2f}\n"
        f"• Buyer: {deal['buyer_username']}\n"
        f"• Seller: {deal['seller_username']}\n"
    )

    await reply_and_clean(update, txt)


# ================================================================
# 🔄 UPDATE DEAL /update <tradeid> (completed)
# ================================================================

async def update_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/update <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].upper().replace("#", "")

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deals WHERE trade_id=?", (trade_id,))
    deal = cur.fetchone()

    if not deal:
        return await msg.reply_text("❗ Invalid Trade ID.", parse_mode="Markdown")

    now = ist_now().isoformat()

    cur.execute("UPDATE deals SET status='completed', updated_at=? WHERE trade_id=?", (now, trade_id))
    conn.commit()
    conn.close()

    txt = (
        "🏁 *Deal Completed*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: `#{trade_id}`\n"
        f"• Buyer: {deal['buyer_username']}\n"
        f"• Seller: {deal['seller_username']}\n"
        f"• Amount: ₹{deal['amount']:.2f}\n"
        f"• Status: completed\n"
    )

    await reply_and_clean(update, txt)


# ================================================================
# 📊 STATUS /status <tradeid>
# ================================================================

async def status_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/status <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].upper().replace("#", "")

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deals WHERE trade_id=?", (trade_id,))
    deal = cur.fetchone()

    if not deal:
        return await msg.reply_text("❗ Trade ID not found.", parse_mode="Markdown")

    txt = (
        "📄 *Deal Status*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: `#{trade_id}`\n"
        f"• Buyer: {deal['buyer_username']}\n"
        f"• Seller: {deal['seller_username']}\n"
        f"• Amount: ₹{deal['amount']:.2f}\n"
        f"• Status: `{deal['status']}`\n"
        f"• Created: `{ist_format(deal['created_at'])}`\n"
        f"• Updated: `{ist_format(deal['updated_at'])}`\n"
    )

    await msg.reply_text(txt, parse_mode="Markdown")


# ================================================================
# 📂 ONGOING DEALS /ongoing
# ================================================================

async def ongoing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT trade_id, buyer_username, seller_username, amount
        FROM deals
        WHERE status='active'
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No ongoing deals.", parse_mode="Markdown")

    txt = "📂 *Ongoing Deals*\n" + DIVIDER + "\n\n"

    for r in rows:
        txt += (
            f"`#{r['trade_id']}` | "
            f"{r['buyer_username']} → {r['seller_username']} | "
            f"₹{r['amount']:.2f}\n"
        )

    await update.message.reply_text(txt, parse_mode="Markdown")


# ================================================================
# 💰 HOLDING AMOUNT /holding
# ================================================================

async def holding_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c, SUM(amount) AS total FROM deals WHERE status='active'")
    row = cur.fetchone()
    conn.close()

    txt = (
        "💰 *Current Holding Amount*\n"
        f"{DIVIDER}\n"
        f"• Active Deals: `{row['c']}`\n"
        f"• Total Holding: ₹{(row['total'] or 0):.2f}`\n"
    )

    await update.message.reply_text(txt, parse_mode="Markdown")


# ================================================================
# 📢 NOTIFY BUYER & SELLER /notify <tradeid>
# ================================================================

async def notify_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await ensure_bot_admin(update, context):
        return

    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/notify <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].upper().replace("#", "")

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deals WHERE trade_id=?", (trade_id,))
    deal = cur.fetchone()

    conn.close()

    if not deal:
        return await msg.reply_text("❗ Invalid Trade ID.", parse_mode="Markdown")

    txt = (
        f"📢 *Deal Update Notification*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: `#{trade_id}`\n"
        f"• Buyer: {deal['buyer_username']}\n"
        f"• Seller: {deal['seller_username']}\n"
        "⚠️ Please respond regarding the ongoing escrow."
    )

    await update.message.reply_text(txt, parse_mode="Markdown")

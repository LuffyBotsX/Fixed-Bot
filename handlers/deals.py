# handlers/deals.py
# All deal-related commands

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import (
    create_deal,
    update_deal,
    get_deal,
    find_active,
    list_active,
    get_fee,
)
from utils import (
    generate_trade_id,
    smart_reply,
    deal_created_message,
    deal_close_message,
    deal_status_message,
    notify_message,
    ist_now,
)


# ============================================================
# 📌 /add – CREATE DEAL
# ============================================================

async def add_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return await msg.reply_text(
            "❗ *Reply to DEAL INFO and use:* `/add <amount>`",
            parse_mode="Markdown"
        )

    if not context.args:
        return await msg.reply_text(
            "❗ Example:\n`/add 1500`",
            parse_mode="Markdown"
        )

    amount = None
    try:
        amount = float(context.args[0])
    except:
        return await msg.reply_text("❗ Invalid amount.", parse_mode="Markdown")

    # extract BUYER / SELLER
    text = msg.reply_to_message.text or ""

    import re
    buyer = re.search(r"buyer\s*[:\-]\s*(\S+)", text, re.I)
    seller = re.search(r"seller\s*[:\-]\s*(\S+)", text, re.I)

    if not buyer or not seller:
        return await msg.reply_text(
            "❗ Could not detect *buyer* or *seller*.",
            parse_mode="Markdown"
        )

    buyer = buyer.group(1)
    seller = seller.group(1)

    trade_id = generate_trade_id()
    escrower = f"@{msg.from_user.username}" if msg.from_user.username else msg.from_user.id

    create_deal(trade_id, buyer, seller, amount, msg.from_user.id)

    text = deal_created_message(trade_id, buyer, seller, amount, escrower)

    await smart_reply(update, text)


# ============================================================
# 📌 /close – COMPLETE DEAL
# ============================================================

async def close_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/close <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].replace("#", "").upper()

    deal = get_deal(trade_id)
    if not deal:
        return await msg.reply_text("❗ Deal not found.", parse_mode="Markdown")

    if deal["status"] != "active":
        return await msg.reply_text(
            f"⚠️ Deal already `{deal['status']}`.",
            parse_mode="Markdown"
        )

    # complete deal
    update_deal(trade_id, "completed")

    deal = get_deal(trade_id)
    text = deal_close_message(deal)

    await smart_reply(update, text)


# ============================================================
# 📌 /cancel – CANCEL DEAL
# ============================================================

async def cancel_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/cancel <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].replace("#", "").upper()
    deal = get_deal(trade_id)

    if not deal:
        return await msg.reply_text("❗ Deal not found.", parse_mode="Markdown")

    if deal["status"] != "active":
        return await msg.reply_text(
            f"⚠️ Deal already `{deal['status']}`.",
            parse_mode="Markdown"
        )

    update_deal(trade_id, "cancelled")

    return await smart_reply(
        update,
        f"❌ *Deal Cancelled*\n{deal_status_message(get_deal(trade_id))}"
    )


# ============================================================
# 📌 /refund – REFUND DEAL
# ============================================================

async def refund_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/refund <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].replace("#", "").upper()
    deal = get_deal(trade_id)

    if not deal:
        return await msg.reply_text("❗ Deal not found.")

    if deal["status"] != "active":
        return await msg.reply_text(
            f"⚠️ Deal already `{deal['status']}`.",
            parse_mode="Markdown"
        )

    update_deal(trade_id, "refunded")

    return await smart_reply(
        update,
        f"♻️ *Deal Refunded*\n{deal_status_message(get_deal(trade_id))}"
    )


# ============================================================
# 📌 /update – MANUAL COMPLETE
# ============================================================

async def update_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/update <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].replace("#", "").upper()
    deal = get_deal(trade_id)

    if not deal:
        return await msg.reply_text("❗ Deal not found.")

    update_deal(trade_id, "completed")

    return await smart_reply(
        update,
        f"🔧 *Deal Manually Completed*\n{deal_status_message(get_deal(trade_id))}"
    )


# ============================================================
# 📌 /status – SHOW DEAL INFO
# ============================================================

async def status_deal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/status <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].replace("#", "").upper()
    deal = get_deal(trade_id)

    if not deal:
        return await msg.reply_text("❗ Deal not found.")

    text = deal_status_message(deal)
    await msg.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /ongoing – LIST ACTIVE DEALS
# ============================================================

async def ongoing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = list_active()

    if not rows:
        return await update.message.reply_text("ℹ️ No active deals.")

    text = "📂 *Ongoing Deals*\n" + "━━━━━━━━━━━━━━━━━━\n"

    for d in rows:
        text += (
            f"`#{d['trade_id']}` – {d['buyer']} → {d['seller']} "
            f"| ₹{d['amount']:.2f}\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /holding – TOTAL HOLD AMOUNT
# ============================================================

async def holding_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = list_active()

    if not rows:
        return await update.message.reply_text("ℹ️ No money on hold.")

    total = sum([d["amount"] for d in rows])

    await update.message.reply_text(
        f"💰 *Current Holding Amount:* ₹{total:.2f}",
        parse_mode="Markdown"
    )


# ============================================================
# 📌 /notify – REMIND BUYER & SELLER
# ============================================================

async def notify_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not context.args:
        return await msg.reply_text("Usage: `/notify <tradeid>`", parse_mode="Markdown")

    trade_id = context.args[0].replace("#", "").upper()
    deal = get_deal(trade_id)

    if not deal:
        return await msg.reply_text("❗ Deal not found.")

    text = notify_message(deal)

    # notify buyer
    try:
        await context.bot.send_message(chat_id=deal["buyer"], text=text)
    except:
        pass

    # notify seller
    try:
        await context.bot.send_message(chat_id=deal["seller"], text=text)
    except:
        pass

    return await msg.reply_text("📢 Notification sent!", parse_mode="Markdown")

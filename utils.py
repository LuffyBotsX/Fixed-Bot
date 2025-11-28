# utils.py
# Utility functions for Era Escrow Bot

import random
import string
from datetime import datetime, timedelta
from io import BytesIO
from telegram import InputFile
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from config import (
    DIVIDER,
    OWNER_ID,
    IST_OFFSET_HOURS,
    IST_OFFSET_MINUTES,
    TIME_FORMAT,
    BOT_NAME,
    POWERED_BY
)

# ============================================================
# 📌 TIME HANDLING
# ============================================================

def ist_now():
    """Return current Indian Standard Time."""
    return datetime.utcnow() + timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)


def format_time(dt_iso):
    """Convert ISO → readable IST time."""
    try:
        dt = datetime.fromisoformat(dt_iso)
        dt = dt + timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)
        return dt.strftime(TIME_FORMAT)
    except:
        return "Unknown Time"


# ============================================================
# 📌 TRADE ID GENERATOR (100% UNIQUE)
# ============================================================

def generate_trade_id():
    """Always generate a unique TID123456 style code."""
    return "TID" + "".join(random.choices(string.digits, k=6))


# ============================================================
# 📌 PERMISSION CHECKS
# ============================================================

def is_owner(uid: int):
    return uid == OWNER_ID


def require_admin(update, context, db_is_admin):
    """Stop command if user isn't admin."""
    uid = update.effective_user.id
    if not db_is_admin(uid):
        update.message.reply_text("⛔ *You are not an admin.*", parse_mode="Markdown")
        return False
    return True


# ============================================================
# 📌 SMART REPLY + DELETE COMMAND
# ============================================================

async def smart_reply(update, text):
    """Reply to replied message or command itself, then delete command."""
    msg = update.message

    target = msg.reply_to_message if msg.reply_to_message else msg

    await target.reply_text(text, parse_mode="Markdown")

    try:
        await msg.delete()
    except:
        pass


# ============================================================
# 📌 DEAL MESSAGE TEMPLATES
# ============================================================

def deal_created_message(trade_id, buyer, seller, amount, escrower):
    return (
        f"💼 *New Escrow Deal Created*\n"
        f"{DIVIDER}\n"
        f"• *Trade ID:* `#{trade_id}`\n"
        f"• *Buyer:* {buyer}\n"
        f"• *Seller:* {seller}\n"
        f"• *Amount:* ₹{amount:.2f}\n"
        f"• *Escrower:* {escrower}\n\n"
        f"⚡ Powered by {POWERED_BY}"
    )


def deal_status_message(deal):
    return (
        f"📄 *Deal Status*\n"
        f"{DIVIDER}\n"
        f"• *Trade ID:* `#{deal['trade_id']}`\n"
        f"• *Buyer:* {deal['buyer']}\n"
        f"• *Seller:* {deal['seller']}\n"
        f"• *Amount:* ₹{deal['amount']:.2f}\n"
        f"• *Status:* `{deal['status']}`\n"
        f"• *Created:* `{format_time(deal['created_at'])}`\n"
        f"• *Updated:* `{format_time(deal['updated_at'])}`"
    )


def deal_close_message(deal):
    return (
        f"✅ *Deal Closed Successfully*\n"
        f"{DIVIDER}\n"
        f"• *Trade ID:* `#{deal['trade_id']}`\n"
        f"• *Buyer:* {deal['buyer']}\n"
        f"• *Seller:* {deal['seller']}\n"
        f"• *Amount:* ₹{deal['amount']:.2f}\n"
        f"• *Fee Charged:* ₹{deal['fee_amount']:.2f}\n"
        f"• *Admin Earning:* ₹{deal['admin_earning']:.2f}\n\n"
        f"🎉 Deal completed safely!"
    )


def notify_message(deal):
    return (
        f"⏰ *Deal Reminder Notification*\n"
        f"{DIVIDER}\n"
        f"• Trade ID: #{deal['trade_id']}\n"
        f"• Buyer: {deal['buyer']}\n"
        f"• Seller: {deal['seller']}\n"
        f"• Amount: ₹{deal['amount']:.2f}\n"
        f"• Status: {deal['status']}\n\n"
        f"⚠️ Please complete the deal ASAP!"
    )


# ============================================================
# 📌 PDF GENERATOR
# ============================================================

def generate_pdf(deals, filename="report.pdf"):
    """Generate table-style PDF for escrow reports."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=20)

    styles = getSampleStyleSheet()

    story = []

    # Title
    story.append(
        Paragraph(f"<b>{BOT_NAME} — Escrow Report</b>", styles["Title"])
    )
    story.append(Spacer(1, 12))

    # Table headers
    data = [[
        "ID", "Buyer", "Seller", "Amount (₹)",
        "Status", "Created", "Updated"
    ]]

    # Fill rows
    for row in deals:
        data.append([
            row["trade_id"],
            row["buyer"],
            row["seller"],
            f"₹{row['amount']:.2f}",
            row["status"],
            format_time(row["created_at"]),
            format_time(row["updated_at"]),
        ])

    table = Table(data)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.black),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )

    story.append(table)
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<i>Powered by {POWERED_BY}</i>", styles["Normal"]))

    doc.build(story)

    buffer.seek(0)
    return InputFile(buffer, filename)


# ============================================================
# 📌 LOG WRITER (for log channels)
# ============================================================

async def send_logs(context, channels, text):
    """Send log message to all registered channels."""
    for row in channels:
        try:
            await context.bot.send_message(row["channel_id"], text)
        except:
            pass

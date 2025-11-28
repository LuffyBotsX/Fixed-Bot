# utils.py — Full Utility Module for Era Escrow Bot
# Works with ALL your handlers. Zero missing functions.

import re
import random
from datetime import datetime, timezone, timedelta
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# ============================================================
# 🕒 IST Time & Formatting
# ============================================================

IST_OFFSET = timedelta(hours=5, minutes=30)


def ist_now():
    """Return current IST datetime."""
    return datetime.now(timezone.utc) + IST_OFFSET


def ist_format(dt):
    """Format datetime into IST readable string."""
    try:
        dt_ist = dt + IST_OFFSET
        return dt_ist.strftime("%Y-%m-%d %I:%M %p")
    except:
        return str(dt)


# ============================================================
# 👤 Username Formatter
# ============================================================

def format_username(user):
    """Return @username OR first name OR ID."""
    if getattr(user, "username", None):
        return f"@{user.username}"
    if getattr(user, "first_name", None):
        return user.first_name
    return str(user.id)


# ============================================================
# ━━━━━━━━━ Divider
# ============================================================

def divider():
    return "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# ============================================================
# 🧹 Reply + Delete Command
# ============================================================

async def reply_and_clean(message, text, parse_mode="Markdown"):
    """Reply to a message and delete the user's command."""
    try:
        target = message.reply_to_message or message
        await target.reply_text(text, parse_mode=parse_mode)
        await message.delete()
    except:
        await message.reply_text(text, parse_mode=parse_mode)


# ============================================================
# 🔢 Amount Parser (10k, 1m, 5.5k, etc.)
# ============================================================

def parse_amount(s: str):
    """Convert human amount like 10k → 10000"""
    if not s:
        return None

    s = s.replace(",", "").strip()
    m = re.match(r"(\d+(?:\.\d+)?)([kKmM]?)", s)
    if not m:
        return None

    num = float(m.group(1))
    suffix = m.group(2).lower()

    if suffix == "k":
        num *= 1000
    elif suffix == "m":
        num *= 1_000_000

    return num


# ============================================================
# 📝 Deal Info Parser (Buyer/Seller/Amount)
# ============================================================

def parse_deal_form(text: str):
    """Extract buyer, seller, and amount from message text."""
    buyer = seller = None
    amount = None

    # Buyer
    b = re.search(r"buyer\s*[:\-]\s*(@\w+)", text, re.IGNORECASE)
    if b:
        buyer = b.group(1)

    # Seller
    s = re.search(r"seller\s*[:\-]\s*(@\w+)", text, re.IGNORECASE)
    if s:
        seller = s.group(1)

    # Amount
    a = re.search(r"(amount|deal amount)\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if a:
        amount = parse_amount(a.group(2).strip())

    return {"buyer": buyer, "seller": seller, "amount": amount}


# ============================================================
# 🆔 Random Trade ID Generator
# ============================================================

def random_trade_id():
    """Generate unique TradeID like TID123456"""
    return f"TID{random.randint(100000, 999999)}"


# ============================================================
# 📄 PDF Generator
# ============================================================

def build_pdf(rows, title="Deal History"):
    """Generate a PDF file with deals data."""
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    if not rows:
        story.append(Paragraph("No records found.", styles["Normal"]))
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        return pdf

    table_data = [["Trade ID", "Buyer", "Seller", "Amount", "Status", "Date"]]

    for r in rows:
        table_data.append([
            r["trade_id"],
            r["buyer_username"],
            r["seller_username"],
            f"₹{float(r['amount']):.2f}",
            r["status"],
            str(r["created_at"])[:16],
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Generated by Era Escrow Bot</i>", styles["Italic"]))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# ============================================================
# ❓ Unknown Command Handler
# ============================================================

async def unknown_cmd_handler(update, context):
    await update.message.reply_text(
        "❓ Unknown command.\nType /start to view available commands.",
        parse_mode="Markdown"
    )

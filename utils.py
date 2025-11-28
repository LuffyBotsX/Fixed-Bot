# utils.py
# Shared utility functions for all handlers

import os
import sqlite3
from datetime import datetime, timezone, timedelta
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# BOT TIMEZONE (IST)
IST_OFFSET = timedelta(hours=5, minutes=30)


# ============================================================
# 📌 Basic Helpers
# ============================================================

def ist_now():
    """Return current Indian time (IST)."""
    return datetime.now(timezone.utc) + IST_OFFSET


def format_username(user):
    """Format telegram username or fallback to first name."""
    if getattr(user, "username", None):
        return f"@{user.username}"
    if getattr(user, "first_name", None):
        return user.first_name
    return str(user.id)


def divider():
    """Pretty line divider."""
    return "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# ============================================================
# 📌 reply_and_clean() — Smart Reply Helper
# ============================================================

async def reply_and_clean(message, text, parse_mode="Markdown"):
    """
    Replies to message, then deletes the user's command.
    Works in private & group.
    """
    try:
        target = message.reply_to_message or message
        await target.reply_text(text, parse_mode=parse_mode)
        await message.delete()
    except:
        await message.reply_text(text, parse_mode=parse_mode)


# ============================================================
# 📌 PDF BUILDER for /history, /escrow
# ============================================================

def build_pdf(rows, title="PDF Export"):
    """Generate styled PDF with deal records."""
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    if not rows:
        story.append(Paragraph("No records found.", styles["Normal"]))
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        return pdf

    columns = ["Trade ID", "Buyer", "Seller", "Amount", "Status", "Date"]
    table_data = [columns]

    for r in rows:
        table_data.append([
            r["trade_id"],
            r["buyer_username"],
            r["seller_username"],
            f"₹{float(r['amount']):.2f}",
            r["status"],
            r["created_at"].split("T")[0] if "T" in r["created_at"] else r["created_at"],
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))

    story.append(table)
    story.append(Spacer(1, 12))
    story.append(Paragraph("<i>Generated via Era Escrow Bot</i>", styles["Italic"]))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf

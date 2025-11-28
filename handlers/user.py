# handlers/user.py
# User Commands: start, stats, mydeals, PDFs, global stats, top users, etc.

from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from io import BytesIO
from datetime import datetime, timedelta, timezone

from database import connect
from utils import (
    format_username,
    ist_now,
    ist_format,
    DIVIDER
)
from pdfbuilder import build_history_pdf, build_escrow_pdf


# ============================================================
# 🚀 /start — Welcome Message
# ============================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"✨ *Welcome to Era Escrow Bot!* ✨\n"
        f"{DIVIDER}\n"
        f"👤 *User:* {format_username(user)}\n"
        f"🆔 *ID:* `{user.id}`\n\n"
        "🔐 This bot helps you perform safe escrow deals:\n"
        "• Secure Buyer ↔ Seller deals\n"
        "• Track active, completed & refunded deals\n"
        "• Generate full PDFs of your history\n\n"
        "Use:\n"
        "• `/stats` — Your stats\n"
        "• `/mydeals` — Your transactions\n"
        "• `/history` — Complete PDF\n"
        "• `/escrow` — Your created deals\n"
        "• `/topuser` — Top traders\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📊 /stats — User Trading Stats
# ============================================================

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uname = format_username(user)

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(amount) AS volume,
            SUM(CASE WHEN status IN ('released','completed') THEN 1 END) AS completed,
            SUM(CASE WHEN status='active' THEN 1 END) AS active,
            SUM(CASE WHEN status IN ('cancelled','refunded') THEN 1 END) AS canceled,
            MIN(created_at) AS first_deal,
            MAX(created_at) AS last_deal
        FROM deals
        WHERE buyer_username=? OR seller_username=? OR created_by=?
    """, (uname, uname, user.id))

    row = cur.fetchone()
    conn.close()

    if row["total"] == 0:
        return await update.message.reply_text(
            f"ℹ️ User {uname} has no recorded deals yet.",
            parse_mode="Markdown"
        )

    text = (
        f"📊 *Your Trading Stats*\n"
        f"{DIVIDER}\n"
        f"👤 Username: {uname}\n"
        f"📍 Total Deals: `{row['total']}`\n"
        f"💰 Total Worth: ₹{(row['volume'] or 0):.2f}\n"
        f"🎯 Completed: `{row['completed'] or 0}`\n"
        f"🟡 Active: `{row['active'] or 0}`\n"
        f"❌ Cancelled/Refunded: `{row['canceled'] or 0}`\n"
        f"⏱ First Deal: `{ist_format(row['first_deal'])}`\n"
        f"⏱ Last Deal: `{ist_format(row['last_deal'])}`\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /stats @username — Tag Stats
# ============================================================

async def stats_tag_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message.text.split()
    if len(msg) < 2:
        return

    target = msg[1].strip().lower()
    if not target.startswith("@"):
        target = "@" + target

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(amount) AS volume,
            MIN(created_at) AS first_deal,
            MAX(created_at) AS last_deal
        FROM deals
        WHERE buyer_username=? OR seller_username=?
    """, (target, target))

    row = cur.fetchone()
    conn.close()

    if row["total"] == 0:
        return await update.message.reply_text(
            f"ℹ️ User {target} has not been involved in any recorded deals.",
            parse_mode="Markdown"
        )

    text = (
        f"📊 *Participant Stats for {target}*\n"
        f"{DIVIDER}\n"
        f"🧾 Total Deals: `{row['total']}`\n"
        f"💰 Total Volume: ₹{(row['volume'] or 0):.2f}\n"
        f"⏱ First Deal: `{ist_format(row['first_deal'])}`\n"
        f"⏱ Last Deal: `{ist_format(row['last_deal'])}`\n\n"
        "⚠️ Always use a trusted escrow!"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 🧾 /mydeals — User Deal List
# ============================================================

async def my_deals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uname = format_username(user)

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT trade_id, buyer_username, seller_username, amount, status
        FROM deals
        WHERE buyer_username=? OR seller_username=? OR created_by=?
        ORDER BY id DESC
        LIMIT 25
    """, (uname, uname, user.id))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ You haven't made any deals yet.")

    text = f"🧾 *Your Deals*\n{DIVIDER}\n\n"

    for r in rows:
        text += (
            f"`#{r['trade_id']}` | "
            f"{r['buyer_username']} → {r['seller_username']} | "
            f"₹{r['amount']:.2f} | *{r['status']}*\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📅 /today — Today’s Activity
# ============================================================

async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = ist_now().date()

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals")
    rows = cur.fetchall()
    conn.close()

    t = vol = comp = act = canc = 0

    for r in rows:
        dt = datetime.fromisoformat(r["created_at"]) + timedelta(hours=5, minutes=30)
        if dt.date() != today:
            continue

        t += 1
        vol += r["amount"]

        if r["status"] in ("released","completed"):
            comp += 1
        elif r["status"] == "active":
            act += 1
        else:
            canc += 1

    text = (
        f"📅 *Today's Summary*\n"
        f"{DIVIDER}\n"
        f"📦 Total Deals: `{t}`\n"
        f"💰 Volume: ₹{vol:.2f}\n"
        f"✔ Completed: `{comp}`\n"
        f"🟡 Active: `{act}`\n"
        f"❌ Cancelled/Refunded: `{canc}`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📆 /week — Weekly Summary
# ============================================================

async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = ist_now().date()
    week_start = today - timedelta(days=6)

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals")
    rows = cur.fetchall()
    conn.close()

    t = vol = comp = act = canc = 0

    for r in rows:
        dt = datetime.fromisoformat(r["created_at"]) + timedelta(hours=5, minutes=30)

        if not (week_start <= dt.date() <= today):
            continue

        t += 1
        vol += r["amount"]

        if r["status"] in ("released", "completed"):
            comp += 1
        elif r["status"] == "active":
            act += 1
        else:
            canc += 1

    text = (
        f"📆 *Weekly Summary*\n"
        f"{DIVIDER}\n"
        f"📅 {week_start} → {today}\n"
        f"📦 Total Deals: `{t}`\n"
        f"💰 Volume: ₹{vol:.2f}\n"
        f"✔ Completed: `{comp}`\n"
        f"🟡 Active: `{act}`\n"
        f"❌ Cancelled/Refunded: `{canc}`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📜 /escrow — Deals created *by user* (PDF)
# ============================================================

async def escrow_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    pdf_bytes = build_escrow_pdf(user.id, format_username(user))
    filename = f"escrow_{user.id}.pdf"

    await update.message.reply_document(
        InputFile(BytesIO(pdf_bytes), filename=filename),
        caption="📜 Your Escrow Summary PDF"
    )


# ============================================================
# 📄 /history — Complete User History PDF
# ============================================================

async def history_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    pdf_bytes = build_history_pdf(user.id, format_username(user))
    filename = f"history_{user.id}.pdf"

    await update.message.reply_document(
        InputFile(BytesIO(pdf_bytes), filename=filename),
        caption="📄 Complete Deal History PDF"
    )


# ============================================================
# 🌍 /gstats — Global Stats
# ============================================================

async def global_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(amount) AS volume,
            SUM(CASE WHEN status IN ('released','completed') THEN 1 END) AS completed,
            SUM(CASE WHEN status='active' THEN 1 END) AS active
        FROM deals
    """)
    row = cur.fetchone()
    conn.close()

    text = (
        f"🌍 *Global Escrow Stats*\n"
        f"{DIVIDER}\n"
        f"📦 Total Deals: `{row['total']}`\n"
        f"💰 Total Volume: ₹{(row['volume'] or 0):.2f}\n"
        f"✔ Completed: `{row['completed'] or 0}`\n"
        f"🟡 Active: `{row['active'] or 0}`\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 🏆 /topuser — Top Traders
# ============================================================

async def topuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT buyer_username, seller_username, amount
        FROM deals 
        WHERE status IN ('released','completed')
    """)

    rows = cur.fetchall()
    conn.close()

    volume = {}

    for r in rows:
        for u in ["buyer_username", "seller_username"]:
            if r[u]:
                volume[u] = volume.get(u, 0) + r["amount"]

    ranking = sorted(volume.items(), key=lambda x: x[1], reverse=True)[:20]

    if not ranking:
        return await update.message.reply_text("ℹ️ No completed deals yet.")

    text = "🏆 *Top Traders*\n" + DIVIDER + "\n\n"

    for i, (user, vol) in enumerate(ranking, 1):
        text += f"{i}. {user} — ₹{vol:.2f}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

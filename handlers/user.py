# handlers/user.py
# User-facing commands: /start /stats /stats @user /mydeals /find /today /week /escrow /history /gstats /topuser

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import connect
from utils import (
    format_username,
    ist_now,
    divider,
    build_pdf,
)


# ============================================================
# 🚀 /start — Welcome Message
# ============================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"✨ *Welcome to Era Escrow Bot!* ✨\n"
        f"{divider()}\n"
        f"👤 *User:* {format_username(user)}\n"
        f"🆔 *ID:* `{user.id}`\n\n"
        "This bot helps you track escrow deals securely:\n"
        "• Secure Buyer ↔ Seller transactions\n"
        "• Auto-tracking of all deal statuses\n"
        "• Beautiful PDF reports\n\n"
        "Use */stats* to view your trading stats.\n"
        "Use */mydeals* to view all your deals."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📊 /stats — Self Stats
# ============================================================

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uname = format_username(user)

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) AS total_deals,
            SUM(amount) AS total_volume,
            SUM(CASE WHEN status IN ('completed','released') THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN status IN ('refunded','cancelled') THEN 1 ELSE 0 END) AS cancelled
        FROM deals
        WHERE buyer_username=? OR seller_username=? OR created_by=?
    """, (uname, uname, user.id))

    row = cur.fetchone()
    conn.close()

    text = (
        f"📊 *Participant Stats for {uname}*\n"
        f"{divider()}\n"
        f"👑 Ranking: `#00`\n"
        f"📈 Total Volume: ₹{(row['total_volume'] or 0):.2f}\n"
        f"🔢 Total Deals: {row['total_deals']}\n"
        f"🕜 Ongoing Deals: {row['active']}\n"
        f"⚡ Highest Deal: ₹0.00\n\n"
        "📌 Always use *Verified Escrow Admins* for safe trades."
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 👤 /stats @username — Other User Stats
# ============================================================

async def stats_tag_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tag = update.message.text.split()[1].lower()
    except:
        return await update.message.reply_text("❗ Usage: `/stats @username`", parse_mode="Markdown")

    if not tag.startswith("@"):
        tag = "@" + tag

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) AS total_deals,
            SUM(amount) AS total_volume,
            SUM(CASE WHEN status IN ('completed','released') THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active
        FROM deals
        WHERE buyer_username=? OR seller_username=?
    """, (tag, tag))

    row = cur.fetchone()
    conn.close()

    if row["total_deals"] == 0:
        return await update.message.reply_text(
            f"ℹ️ User {tag} has not been involved in any recorded deals yet.",
            parse_mode="Markdown"
        )

    text = (
        f"📊 *User Stats*\n"
        f"{divider()}\n"
        f"👤 Username: {tag}\n"
        f"📍 Total Escrows: {row['total_deals']}\n"
        f"🎉 Completed: {row['completed']}\n"
        f"⏳ Active Deals: {row['active']}\n"
        f"💰 Total Worth: ₹{(row['total_volume'] or 0):.2f}\n"
        f"⏰ Fastest Escrow: None\n"
        f"⏰ First Escrow Time: None\n"
        f"⏰ Last Escrow Time: None\n"
        f"💰 Last Escrow Worth: ₹0.00"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📁 /mydeals — User's Deal List
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
        ORDER BY id DESC LIMIT 20
    """, (uname, uname, user.id))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ You don't have any deals yet.")

    text = f"🧾 *Your Deals*\n{divider()}\n\n"
    for r in rows:
        text += (
            f"`#{r['trade_id']}` | "
            f"{r['buyer_username']} → {r['seller_username']} | "
            f"₹{r['amount']:.2f} | *{r['status']}*\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 🔍 /find — Search Active Deals by Username
# ============================================================

async def find_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Usage: `/find @username`", parse_mode="Markdown")

    target = context.args[0].lower()
    if not target.startswith("@"):
        target = "@" + target

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT trade_id, buyer_username, seller_username, amount
        FROM deals
        WHERE status='active' AND 
        (LOWER(buyer_username)=? OR LOWER(seller_username)=?)
        ORDER BY id DESC
        LIMIT 25
    """, (target, target))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text(
            f"ℹ️ No active deals found for {target}.", parse_mode="Markdown"
        )

    text = f"🔍 *Active Deals for {target}*\n{divider()}\n\n"
    for r in rows:
        text += (
            f"`#{r['trade_id']}` | "
            f"{r['buyer_username']} → {r['seller_username']} | "
            f"₹{r['amount']:.2f}\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📅 /today — Today Summary
# ============================================================

async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = ist_now().date()

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT amount, status, created_at FROM deals")
    rows = cur.fetchall()
    conn.close()

    total = volume = completed = active = cancelled = 0

    for r in rows:
        dt = r["created_at"]
        try:
            date = dt.split("T")[0]
        except:
            continue

        if str(today) != date:
            continue

        total += 1
        volume += r["amount"] or 0

        if r["status"] in ("completed","released"):
            completed += 1
        elif r["status"] == "active":
            active += 1
        else:
            cancelled += 1

    text = (
        f"📅 *Today's Summary*\n{divider()}\n"
        f"• Total Deals: {total}\n"
        f"• Volume: ₹{volume:.2f}\n"
        f"• Completed: {completed}\n"
        f"• Active: {active}\n"
        f"• Cancelled: {cancelled}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📆 /week — Weekly Summary
# ============================================================

async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    now = ist_now().date()
    week_start = now - timedelta(days=6)

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT amount, status, created_at FROM deals")
    rows = cur.fetchall()
    conn.close()

    total = volume = completed = active = cancelled = 0

    for r in rows:
        d = r["created_at"].split("T")[0]
        if not (str(week_start) <= d <= str(now)):
            continue

        total += 1
        volume += r["amount"] or 0

        if r["status"] in ("completed","released"):
            completed += 1
        elif r["status"] == "active":
            active += 1
        else:
            cancelled += 1

    text = (
        f"📆 *Weekly Summary*\n{divider()}\n"
        f"• Deals: {total}\n"
        f"• Volume: ₹{volume:.2f}\n"
        f"• Completed: {completed}\n"
        f"• Active: {active}\n"
        f"• Cancelled: {cancelled}"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📄 /escrow — Escrow History PDF (Admin Work)
# ============================================================

async def escrow_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM deals
        WHERE created_by=?
        ORDER BY id DESC
    """, (user.id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ You haven't escrowed any deals yet.")

    pdf_bytes = build_pdf(rows, title=f"{format_username(user)} — Escrow Summary")
    await update.message.reply_document(pdf_bytes, filename="escrow_summary.pdf")


# ============================================================
# 📄 /history — Complete Deal History PDF
# ============================================================

async def history_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uname = format_username(user)

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM deals
        WHERE buyer_username=? OR seller_username=? OR created_by=?
        ORDER BY id DESC
    """, (uname, uname, user.id))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No deal history found.")

    pdf_bytes = build_pdf(rows, title=f"{uname} — Full Deal History")
    await update.message.reply_document(pdf_bytes, filename="history.pdf")


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
            SUM(CASE WHEN status IN ('completed','released') THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active
        FROM deals
    """)
    row = cur.fetchone()
    conn.close()

    text = (
        f"🌍 *Global Escrow Stats*\n{divider()}\n"
        f"🔢 Total Deals: {row['total']}\n"
        f"💰 Total Volume: ₹{(row['volume'] or 0):.2f}\n"
        f"🎉 Completed: {row['completed']}\n"
        f"⏳ Active: {row['active']}"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 🏆 /topuser — Top 20 Traders
# ============================================================

async def topuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT buyer_username, seller_username, amount
        FROM deals
        WHERE status IN ('completed','released')
    """)

    volume = {}
    for r in cur.fetchall():
        for u in (r["buyer_username"], r["seller_username"]):
            if not u:
                continue
            volume[u] = volume.get(u, 0) + (r["amount"] or 0)

    conn.close()

    if not volume:
        return await update.message.reply_text("ℹ️ No completed deals yet.")

    ranking = sorted(volume.items(), key=lambda x: x[1], reverse=True)[:20]

    text = "🏆 *Top 20 Traders*\n" + divider() + "\n\n"
    rank = 1
    for u, v in ranking:
        text += f"#{rank} — {u} → ₹{v:.2f}\n"
        rank += 1

    await update.message.reply_text(text, parse_mode="Markdown")

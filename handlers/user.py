# handlers/user.py
# User-level commands (stats, history, summaries)

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import (
    get_deal,
    list_active,
    connect,
    is_admin,
)
from utils import (
    generate_pdf,
    ist_now,
    format_time,
)

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# ============================================================
# 📌 /start — WELCOME
# ============================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"✨ *Welcome to Era Escrow Bot!* ✨\n"
        f"{DIVIDER}\n"
        f"👤 *User:* @{user.username}\n"
        f"🆔 *ID:* `{user.id}`\n\n"
        "This bot helps you perform safe escrow trades.\n"
        "Use commands like:\n"
        "• /stats\n"
        "• /mydeals\n"
        "• /escrow\n"
        "• /history\n\n"
        "Admins can use /cmds for full panel."
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 INTERNAL: USER DEAL QUERY
# ============================================================

def fetch_user_deals(uid, username):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM deals
        WHERE buyer=? OR seller=? OR created_by=?
        ORDER BY id DESC
    """, (username, username, uid))
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================================================
# 📌 /stats — YOUR STATS
# ============================================================

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"

    deals = fetch_user_deals(user.id, username)

    total = len(deals)
    volume = sum([d["amount"] for d in deals]) if deals else 0

    completed = len([d for d in deals if d["status"] == "completed"])
    active = len([d for d in deals if d["status"] == "active"])
    cancelled = len([d for d in deals if d["status"] in ("cancelled", "refunded")])

    text = (
        f"📊 *Your Stats – {username}*\n"
        f"{DIVIDER}\n"
        f"• Total Deals: `{total}`\n"
        f"• Total Volume: ₹{volume:.2f}\n"
        f"• Completed: `{completed}`\n"
        f"• Active: `{active}`\n"
        f"• Cancelled/Refunded: `{cancelled}`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /stats @username — CHECK OTHERS
# ============================================================

async def stats_tag_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()

    username = text.split()[1].lower()

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM deals
        WHERE lower(buyer)=? OR lower(seller)=?
    """, (username, username))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await msg.reply_text(
            f"ℹ️ User {username} has no recorded deals."
        )

    total = len(rows)
    volume = sum([r["amount"] for r in rows])
    completed = len([r for r in rows if r["status"] == "completed"])
    active = len([r for r in rows if r["status"] == "active"])
    cancelled = len([r for r in rows if r["status"] in ("cancelled", "refunded")])

    reply = (
        f"📊 *Stats for {username}*\n"
        f"{DIVIDER}\n"
        f"• Total Deals: `{total}`\n"
        f"• Total Volume: ₹{volume:.2f}\n"
        f"• Completed: `{completed}`\n"
        f"• Active: `{active}`\n"
        f"• Cancelled/Refunded: `{cancelled}`"
    )

    await msg.reply_text(reply, parse_mode="Markdown")


# ============================================================
# 📌 /mydeals — USER DEAL LIST
# ============================================================

async def my_deals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"

    rows = fetch_user_deals(user.id, username)

    if not rows:
        return await update.message.reply_text("ℹ️ You have no deals yet.")

    text = "🧾 *Your Deals*\n" + DIVIDER + "\n\n"

    for d in rows[:25]:
        text += (
            f"`#{d['trade_id']}` | {d['buyer']} → {d['seller']} "
            f"| ₹{d['amount']:.2f} | *{d['status']}*\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /find — ADMIN ONLY: FIND USER ACTIVE DEALS
# ============================================================

async def find_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Admin only.")

    if not context.args:
        return await update.message.reply_text("Usage: /find @username")

    target = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM deals
        WHERE status='active'
        AND (lower(buyer)=? OR lower(seller)=?)
    """, (target, target))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No active deals for this user.")

    text = f"🔍 *Active Deals for {target}*\n{DIVIDER}\n\n"

    for d in rows:
        text += (
            f"`#{d['trade_id']}` | {d['buyer']} → {d['seller']} "
            f"| ₹{d['amount']:.2f}\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /today — TODAY SUMMARY
# ============================================================

async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = ist_now().date()

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals")
    rows = cur.fetchall()
    conn.close()

    deals_today = [d for d in rows if datetime.fromisoformat(d["created_at"]).date() == today]

    if not deals_today:
        return await update.message.reply_text("ℹ️ No deals today.")

    total = len(deals_today)
    volume = sum([d["amount"] for d in deals_today])

    await update.message.reply_text(
        f"📅 *Today's Summary*\n{DIVIDER}\n"
        f"• Deals: `{total}`\n"
        f"• Volume: ₹{volume:.2f}",
        parse_mode="Markdown"
    )


# ============================================================
# 📌 /week — WEEKLY SUMMARY
# ============================================================

async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = ist_now().date()
    week_start = now - timedelta(days=7)

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals")
    rows = cur.fetchall()
    conn.close()

    week_deals = [
        d for d in rows
        if week_start <= datetime.fromisoformat(d["created_at"]).date() <= now
    ]

    if not week_deals:
        return await update.message.reply_text("ℹ️ No deals this week.")

    total = len(week_deals)
    volume = sum([d["amount"] for d in week_deals])

    await update.message.reply_text(
        f"📆 *Weekly Summary*\n{DIVIDER}\n"
        f"• Deals: `{total}`\n"
        f"• Volume: ₹{volume:.2f}",
        parse_mode="Markdown"
    )


# ============================================================
# 📌 /escrow — PDF OF DEALS CREATED BY USER
# ============================================================

async def escrow_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals WHERE created_by=? ORDER BY id DESC", (user.id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ You have not created any deals.")

    pdf = generate_pdf(rows, filename=f"escrow_{user.id}.pdf")

    await update.message.reply_document(pdf, caption="📜 All-Time Escrow Summary")


# ============================================================
# 📌 /history — FULL PDF HISTORY
# ============================================================

async def history_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"

    rows = fetch_user_deals(user.id, username)

    if not rows:
        return await update.message.reply_text("ℹ️ No deal history found.")

    pdf = generate_pdf(rows, filename=f"history_{user.id}.pdf")

    await update.message.reply_document(pdf, caption="📜 Full Deal History")


# ============================================================
# 📌 /gstats — GLOBAL STATS
# ============================================================

async def global_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals")
    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    volume = sum([r["amount"] for r in rows]) if rows else 0
    completed = len([r for r in rows if r["status"] == "completed"])
    active = len([r for r in rows if r["status"] == "active"])

    await update.message.reply_text(
        f"🌐 *Global Stats*\n{DIVIDER}\n"
        f"• Total Deals: `{total}`\n"
        f"• Total Volume: ₹{volume:.2f}\n"
        f"• Completed: `{completed}`\n"
        f"• Active: `{active}`",
        parse_mode="Markdown"
    )


# ============================================================
# 📌 /topuser — TOP 20 TRADERS
# ============================================================

async def topuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT buyer, seller, amount
        FROM deals
        WHERE status='completed'
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No completed deals found.")

    ranking = {}

    for d in rows:
        ranking[d["buyer"]] = ranking.get(d["buyer"], 0) + d["amount"]
        ranking[d["seller"]] = ranking.get(d["seller"], 0) + d["amount"]

    top = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:20]

    text = "🏆 *Top 20 Traders*\n" + DIVIDER + "\n\n"

    for i, (user, vol) in enumerate(top, start=1):
        text += f"#{i} — {user} • ₹{vol:.2f}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

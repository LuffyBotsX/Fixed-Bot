# handlers/user.py
# User-level commands (stats, deals, summaries, PDFs, etc.)

from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from io import BytesIO

from database import connect
from utils import format_username, ist_now, ist_format, DIVIDER


# ============================================================
# 📌 /start — Welcome message
# ============================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"🤖 *Welcome to Era Escrow Bot!*\n"
        f"{DIVIDER}\n"
        f"👤 User: {format_username(user)}\n"
        f"🆔 ID: `{user.id}`\n\n"
        "This bot safely manages escrow deals between Buyer & Seller.\n"
        "• Trusted Deal Creation\n"
        "• Auto Status Tracking\n"
        "• Secure Payout System\n"
        "• Admin Fees Tracking\n\n"
        "Type `/stats` to see your profile.\n"
        "Admins can use `/cmds` for full panel."
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ============================================================
# 📌 /stats — Self Stats
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
            MAX(amount) AS biggest,
            MIN(amount) AS smallest
        FROM deals
        WHERE buyer_username=? OR seller_username=? OR created_by=?
    """, (uname, uname, user.id))

    row = cur.fetchone()
    conn.close()

    total = row["total"] or 0
    volume = row["volume"] or 0

    if total == 0:
        return await update.message.reply_text(
            f"ℹ️ {uname} does not have any recorded deals yet.",
            parse_mode="Markdown"
        )

    text = (
        f"📊 *Your Trading Stats — {uname}*\n"
        f"{DIVIDER}\n"
        f"• Total Deals: `{total}`\n"
        f"• Total Volume: ₹{volume:.2f}\n"
        f"• Biggest Deal: ₹{(row['biggest'] or 0):.2f}\n"
        f"• Smallest Deal: ₹{(row['smallest'] or 0):.2f}\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown)


# ============================================================
# 📌 /stats @username — Tagged Stats
# ============================================================

async def stats_tag_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    parts = msg.text.split()

    if len(parts) < 2:
        return await msg.reply_text("Usage: `/stats @username`", parse_mode="Markdown")

    uname = parts[1].lower()

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(amount) AS volume
        FROM deals
        WHERE LOWER(buyer_username)=? OR LOWER(seller_username)=?
    """, (uname, uname))

    row = cur.fetchone()
    conn.close()

    if not row or row["total"] == 0:
        return await msg.reply_text(
            f"ℹ️ User {uname} has not been involved in any recorded deals.",
            parse_mode="Markdown"
        )

    text = (
        f"📊 *User Stats for {uname}*\n"
        f"{DIVIDER}\n"
        f"• Total Deals: `{row['total']}`\n"
        f"• Total Volume: ₹{row['volume']:.2f}\n"
        "• Ranking: Coming Soon…\n"
    )

    await msg.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /mydeals — Show user’s recent deals
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
        LIMIT 20
    """, (uname, uname, user.id))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ You do not have any deals yet.")

    txt = "🧾 *Your Recent Deals*\n" + DIVIDER + "\n\n"

    for r in rows:
        txt += (
            f"`#{r['trade_id']}` | {r['buyer_username']} → {r['seller_username']} | "
            f"₹{r['amount']:.2f} | *{r['status']}*\n"
        )

    await update.message.reply_text(txt, parse_mode="Markdown")


# ============================================================
# 📌 /find @user — Admin search
# ============================================================

async def find_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/find @username`")

    uname = context.args[0].lower()

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT trade_id, buyer_username, seller_username, amount
        FROM deals
        WHERE status='active'
        AND (LOWER(buyer_username)=? OR LOWER(seller_username)=?)
    """, (uname, uname))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text(f"ℹ️ No active deals for {uname}.")

    txt = f"🔍 *Active Deals for {uname}*\n{DIVIDER}\n\n"

    for r in rows:
        txt += (
            f"`#{r['trade_id']}` | "
            f"{r['buyer_username']} → {r['seller_username']} | "
            f"₹{r['amount']:.2f}\n"
        )

    await update.message.reply_text(txt, parse_mode="Markdown")


# ============================================================
# 📌 /today — Today's summary
# ============================================================

async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = ist_now().date()

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deals")
    rows = cur.fetchall()
    conn.close()

    total = volume = 0

    for d in rows:
        dt = ist_format(d["created_at"])
        if str(today) in dt:
            total += 1
            volume += d["amount"] or 0

    txt = (
        "📅 *Today's Summary*\n"
        f"{DIVIDER}\n"
        f"• Deals: `{total}`\n"
        f"• Volume: ₹{volume:.2f}\n"
    )

    await update.message.reply_text(txt, parse_mode="Markdown")


# ============================================================
# 📌 /week — Weekly summary
# ============================================================

async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = ist_now().date()
    week_start = today - timedelta(days=6)

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals")
    rows = cur.fetchall()
    conn.close()

    total = volume = 0

    for d in rows:
        dt = ist_format(d["created_at"]).split()[0]  
        try:
            date_dt = datetime.strptime(dt, "%Y-%m-%d").date()
        except:
            continue

        if week_start <= date_dt <= today:
            total += 1
            volume += d["amount"] or 0

    txt = (
        "📆 *Weekly Summary*\n"
        f"{DIVIDER}\n"
        f"• Deals: `{total}`\n"
        f"• Volume: ₹{volume:.2f}\n"
    )

    await update.message.reply_text(txt, parse_mode="Markdown")


# ============================================================
# 📌 /escrow — PDF Summary (deals created by user)
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

    deals = cur.fetchall()
    conn.close()

    if not deals:
        return await update.message.reply_text("ℹ️ You have not created any deals as Escrow.")

    pdf = BytesIO()
    pdf.write(b"PDF report generation placeholder.")
    pdf.seek(0)

    await update.message.reply_document(
        document=InputFile(pdf, filename="escrow_summary.pdf"),
        caption="📜 Escrow Summary PDF"
    )


# ============================================================
# 📌 /history — PDF All deals
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

    deals = cur.fetchall()
    conn.close()

    if not deals:
        return await update.message.reply_text("ℹ️ No deal history found.")

    pdf = BytesIO()
    pdf.write(b"User deal history placeholder PDF.")
    pdf.seek(0)

    await update.message.reply_document(
        document=InputFile(pdf, filename="history.pdf"),
        caption="📜 Full Deal History PDF"
    )


# ============================================================
# 📌 /gstats — Global Stats
# ============================================================

async def global_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(amount) AS volume,
               SUM(CASE WHEN status='active' THEN 1 END) AS active,
               SUM(CASE WHEN status IN ('completed','released') THEN 1 END) AS completed
        FROM deals
    """)

    row = cur.fetchone()
    conn.close()

    text = (
        "🌐 *Global Escrow Stats*\n"
        f"{DIVIDER}\n"
        f"• Total Deals: `{row['total']}`\n"
        f"• Total Volume: ₹{(row['volume'] or 0):.2f}\n"
        f"• Active: `{row['active']}`\n"
        f"• Completed: `{row['completed']}`\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /topuser — Top Users Ranking
# ============================================================

async def topuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT buyer_username AS user, SUM(amount) AS volume 
        FROM deals WHERE status IN ('completed','released')
        GROUP BY buyer_username
        ORDER BY volume DESC
        LIMIT 20
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No completed deals found.")

    txt = "🏆 *Top Traders*\n" + DIVIDER + "\n\n"

    rank = 1
    for r in rows:
        txt += f"#{rank} — {r['user']} → ₹{r['volume']:.2f}\n"
        rank += 1

    await update.message.reply_text(txt, parse_mode="Markdown")

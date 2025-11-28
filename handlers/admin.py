# handlers/admin.py
# Admin & Owner command handlers for Era Escrow Bot

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils import ist_now, format_username, reply_and_clean
from database import (
    is_admin,
    add_admin,
    remove_admin,
    list_admins,
    set_fee,
    get_fee,
    set_logs,
    remove_logs,
    get_logs,
    connect
)

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
OWNER_ONLY = "⛔ *Owner only command!*"
ADMIN_ONLY = "⛔ *Admin only command!*"


# ============================================================
# 📌 /cmds – FULL ADMIN COMMAND LIST
# ============================================================

async def cmds_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    text = (
        "🛠 *Admin Command Panel*\n"
        f"{DIVIDER}\n"
        "💼 *Deal Management*\n"
        "/add <amount>\n"
        "/close <tradeid>\n"
        "/refund <tradeid>\n"
        "/cancel <tradeid>\n"
        "/update <tradeid>\n"
        "/status <tradeid>\n"
        "/ongoing\n"
        "/holding\n"
        "/notify <tradeid>\n\n"
        
        "📊 *User & Summary*\n"
        "/stats\n"
        "/stats @user\n"
        "/mydeals\n"
        "/find @user\n"
        "/today\n"
        "/week\n"
        "/escrow\n"
        "/history\n"
        "/gstats\n"
        "/topuser\n\n"

        "👑 *Admin Control*\n"
        "/adminlist\n"
        "/addadmin <id>\n"
        "/removeadmin <id>\n"
        "/setfee <percent> <min_fee>\n"
        "/earnings\n"
        "/myearnings\n"
        "/adminwise\n"
        "/topadmins\n\n"

        "⚠️ *Owner Panel*\n"
        "/panel\n"
        "/reset_all confirm\n"
        "/export_data\n"
        "/setlogs <chatid>\n"
        "/removelogs\n"
        "/tlogs\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /menu – INLINE ADMIN DASHBOARD
# ============================================================

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    buttons = [
        [InlineKeyboardButton("📂 Ongoing Deals", callback_data="ongoing")],
        [InlineKeyboardButton("💰 Holding Amount", callback_data="holding")],
        [InlineKeyboardButton("📊 Global Stats", callback_data="gstats")],
        [InlineKeyboardButton("👑 Admin List", callback_data="admins")],
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "📋 *Admin Dashboard*\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# ============================================================
# 📌 /panel – OWNER PANEL
# ============================================================

async def panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    await update.message.reply_text(
        "👑 *Owner Panel*\n"
        f"{DIVIDER}\n"
        "/setfee <percent> <min_fee>\n"
        "/addadmin <id>\n"
        "/removeadmin <id>\n"
        "/reset_all confirm\n"
        "/export_data\n"
        "/setlogs <chatid>\n"
        "/removelogs\n"
        "/tlogs",
        parse_mode="Markdown"
    )


# ============================================================
# 📌 /setfee – CHANGE ESCROW FEE
# ============================================================

async def set_fee_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    if len(context.args) < 1:
        return await update.message.reply_text("Usage: `/setfee <percent> <min_fee>`", parse_mode="Markdown")

    try:
        percent = float(context.args[0])
        min_fee = float(context.args[1]) if len(context.args) > 1 else 0
    except:
        return await update.message.reply_text("❗ Invalid numbers.", parse_mode="Markdown")

    set_fee(percent, min_fee)

    await update.message.reply_text(
        f"✅ *Fee Updated Successfully*\n"
        f"{DIVIDER}\n"
        f"• Percent: `{percent}%`\n"
        f"• Minimum: `₹{min_fee}`",
        parse_mode="Markdown"
    )


# ============================================================
# 📌 /addadmin – ADD ADMIN
# ============================================================

async def add_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text("Usage: `/addadmin <userid>`", parse_mode="Markdown")

    try:
        admin_id = int(context.args[0])
    except:
        return await update.message.reply_text("❗ Invalid ID.", parse_mode="Markdown")

    add_admin(admin_id)

    await update.message.reply_text(f"👮 *Admin Added:* `{admin_id}`", parse_mode="Markdown")


# ============================================================
# 📌 /removeadmin – REMOVE ADMIN
# ============================================================

async def remove_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text("Usage: `/removeadmin <userid>`", parse_mode="Markdown")

    try:
        admin_id = int(context.args[0])
    except:
        return await update.message.reply_text("❗ Invalid ID.", parse_mode="Markdown")

    remove_admin(admin_id)

    await update.message.reply_text(f"❌ *Admin Removed:* `{admin_id}`", parse_mode="Markdown")


# ============================================================
# 📌 /adminlist – ALL ADMINS
# ============================================================

async def admin_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    admins = list_admins()

    text = "👑 *Admin List*\n" + DIVIDER + "\n\n"

    for a in admins:
        text += f"• `{a['user_id']}`\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 LOGGING CHANNELS (setlogs / removelogs / tlogs)
# ============================================================

async def set_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text("Usage: `/setlogs <chatid>`", parse_mode="Markdown")

    chat_id = int(context.args[0])
    set_logs(chat_id)

    await update.message.reply_text(f"📡 Logs channel set to `{chat_id}`", parse_mode="Markdown")


async def remove_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    remove_logs()

    await update.message.reply_text("🗑 Logs removed.", parse_mode="Markdown")


async def show_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    chat_id = get_logs()

    if not chat_id:
        return await update.message.reply_text("ℹ️ No logs channel set.", parse_mode="Markdown")

    await update.message.reply_text(f"📡 Logs Channel: `{chat_id}`", parse_mode="Markdown")


# ============================================================
# 📌 DATABASE EXPORT (OWNER ONLY)
# ============================================================

async def export_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    conn = connect()
    cur = conn.cursor()

    tables = ["deals", "admins", "fees", "bans", "warns", "notes", "groups", "logs"]
    data = {}

    for t in tables:
        cur.execute(f"SELECT * FROM {t}")
        rows = [dict(r) for r in cur.fetchall()]
        data[t] = rows

    conn.close()

    import json
    dump = json.dumps(data, indent=4)

    await update.message.reply_document(
        document=dump.encode(),
        filename="export_data.json",
        caption="📦 Full Database Export"
    )


# ============================================================
# 📌 RESET ALL DATA (OWNER ONLY)
# ============================================================

async def reset_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 6847499628:
        return await update.message.reply_text(OWNER_ONLY, parse_mode="Markdown")

    if not context.args or context.args[0] != "confirm":
        return await update.message.reply_text(
            "⚠️ This will delete ALL data.\nUse:\n`/reset_all confirm`",
            parse_mode="Markdown"
        )

    conn = connect()
    cur = conn.cursor()

    tables = ["deals", "admins", "fees", "bans", "warns", "notes", "groups", "logs"]
    for t in tables:
        cur.execute(f"DELETE FROM {t}")

    conn.commit()
    conn.close()

    await update.message.reply_text("🔥 *All data reset successfully!*", parse_mode="Markdown")


# ============================================================
# 📌 EARNINGS PANEL
# ============================================================

async def earnings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT created_by, SUM(admin_earning) AS total FROM deals GROUP BY created_by")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No earnings yet.")

    text = "💰 *Admin Earnings*\n" + DIVIDER + "\n\n"

    for r in rows:
        text += f"• `{r['created_by']}` → ₹{r['total']:.2f}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /myearnings – ADMIN PERSONAL EARNING
# ============================================================

async def admin_earnings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not is_admin(uid):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT SUM(admin_earning) AS total FROM deals WHERE created_by=?", (uid,))
    row = cur.fetchone()
    conn.close()

    total = row["total"] or 0

    await update.message.reply_text(
        f"💸 *Your Earnings:* ₹{total:.2f}",
        parse_mode="Markdown"
    )


# ============================================================
# 📌 /adminwise – COMPARE ALL ADMIN EARNINGS
# ============================================================

async def admin_compare_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT created_by, SUM(admin_earning) AS total FROM deals GROUP BY created_by")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await update.message.reply_text("ℹ️ No earnings found.")

    text = "📊 *Admin Earnings Comparison*\n" + DIVIDER + "\n\n"

    for r in rows:
        text += f"• `{r['created_by']}` → ₹{r['total']:.2f}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# 📌 /topadmins – RANK ADMIN EARNINGS
# ============================================================

async def top_admins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text(ADMIN_ONLY, parse_mode="Markdown")

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT created_by, SUM(admin_earning) AS total FROM deals GROUP BY created_by")
    rows = cur.fetchall()
    conn.close()

    ranking = sorted(rows, key=lambda x: x["total"], reverse=True)

    text = "🏆 *Top Admins by Earnings*\n" + DIVIDER + "\n\n"

    for idx, r in enumerate(ranking, start=1):
        text += f"#{idx} — `{r['created_by']}` → ₹{r['total']:.2f}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

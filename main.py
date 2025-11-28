#!/usr/bin/env python3
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# ------------------ MERGED CONFIG ------------------
BOT_TOKEN = "8389093783:AAFiQGG8SLs9ba7AmEHFrFMPzvqYUtOcGYU"
OWNER_ID = 6847499628

BOT_NAME = "Era Escrow Bot"
POWERED_BY = "@LuffyBots"

DB_PATH = "data/escrow.db"

IST_OFFSET_HOURS = 5
IST_OFFSET_MINUTES = 30

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DEFAULT_FEE_PERCENT = 5
DEFAULT_MIN_FEE = 5

DEFAULT_WELCOME = "👋 Welcome {user}!"
DEFAULT_FAREWELL = "👋 Goodbye {user}!"

TIME_FORMAT = "%I:%M %p"

LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
# ---------------------------------------------------


# Import internal modules
from database import init_database
from handlers.admin import (
    cmds_handler,
    menu_handler,
    panel_handler,
    add_admin_handler,
    remove_admin_handler,
    admin_list_handler,
    set_fee_handler,
    reset_all_handler,
    export_data_handler,
    set_logs_handler,
    remove_logs_handler,
    show_logs_handler,
    earnings_handler,
    admin_earnings_handler,
    admin_compare_handler,
    top_admins_handler,
)
from handlers.deals import (
    add_deal_handler,
    close_deal_handler,
    refund_deal_handler,
    cancel_deal_handler,
    update_deal_handler,
    status_deal_handler,
    ongoing_handler,
    holding_handler,
    notify_handler,
)
from handlers.user import (
    start_handler,
    stats_handler,
    stats_tag_handler,
    my_deals_handler,
    find_handler,
    today_handler,
    week_handler,
    escrow_pdf_handler,
    history_pdf_handler,
    global_stats_handler,
    topuser_handler,
)
from handlers.moderation import (
    warn_handler,
    unwarn_handler,
    warns_handler,
    ban_handler,
    unban_handler,
    kick_handler,
    mute_handler,
    unmute_handler,
    info_handler,
    save_note_handler,
    notes_handler,
    clean_warns_handler,
    clean_notes_handler,
)
from handlers.groups import (
    set_group_handler,
    remove_group_handler,
    groups_handler,
    set_welcome_handler,
    set_farewell_handler,
    toggle_welcome_handler,
)
from handlers.logs import (
    test_handler,
    chatid_handler,
)

from utils import unknown_cmd_handler


# --------------------- LOGGER ---------------------
logging.basicConfig(
    level=logging.INFO,
    format=LOGGING_FORMAT
)
logger = logging.getLogger(__name__)


# --------------------- MAIN -----------------------
def main():
    logger.info("📦 Initializing database...")
    init_database()

    logger.info("🤖 Starting Era Escrow Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ========== USER COMMANDS ==========
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("mydeals", my_deals_handler))
    app.add_handler(CommandHandler("today", today_handler))
    app.add_handler(CommandHandler("week", week_handler))
    app.add_handler(CommandHandler("escrow", escrow_pdf_handler))
    app.add_handler(CommandHandler("history", history_pdf_handler))
    app.add_handler(CommandHandler("gstats", global_stats_handler))
    app.add_handler(CommandHandler("topuser", topuser_handler))

    # /stats @username
    app.add_handler(MessageHandler(filters.Regex(r"^/stats\s+@"), stats_tag_handler))

    # ========== DEAL COMMANDS ==========
    app.add_handler(CommandHandler("add", add_deal_handler))
    app.add_handler(CommandHandler("close", close_deal_handler))
    app.add_handler(CommandHandler("refund", refund_deal_handler))
    app.add_handler(CommandHandler("cancel", cancel_deal_handler))
    app.add_handler(CommandHandler("update", update_deal_handler))
    app.add_handler(CommandHandler("status", status_deal_handler))
    app.add_handler(CommandHandler("ongoing", ongoing_handler))
    app.add_handler(CommandHandler("holding", holding_handler))
    app.add_handler(CommandHandler("notify", notify_handler))
    app.add_handler(CommandHandler("find", find_handler))

    # ========== ADMIN PANEL ==========
    app.add_handler(CommandHandler("cmds", cmds_handler))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("panel", panel_handler))
    app.add_handler(CommandHandler("setfee", set_fee_handler))
    app.add_handler(CommandHandler("addadmin", add_admin_handler))
    app.add_handler(CommandHandler("removeadmin", remove_admin_handler))
    app.add_handler(CommandHandler("adminlist", admin_list_handler))
    app.add_handler(CommandHandler("reset_all", reset_all_handler))
    app.add_handler(CommandHandler("export_data", export_data_handler))

    # Logging channels
    app.add_handler(CommandHandler("setlogs", set_logs_handler))
    app.add_handler(CommandHandler("removelogs", remove_logs_handler))
    app.add_handler(CommandHandler("tlogs", show_logs_handler))

    # Admin earnings
    app.add_handler(CommandHandler("earnings", earnings_handler))
    app.add_handler(CommandHandler("myearnings", admin_earnings_handler))
    app.add_handler(CommandHandler("adminwise", admin_compare_handler))
    app.add_handler(CommandHandler("topadmins", top_admins_handler))

    # ========== MODERATION ==========
    app.add_handler(CommandHandler("warn", warn_handler))
    app.add_handler(CommandHandler("dwarn", unwarn_handler))
    app.add_handler(CommandHandler("warns", warns_handler))
    app.add_handler(CommandHandler("ban", ban_handler))
    app.add_handler(CommandHandler("unban", unban_handler))
    app.add_handler(CommandHandler("kick", kick_handler))
    app.add_handler(CommandHandler("mute", mute_handler))
    app.add_handler(CommandHandler("unmute", unmute_handler))
    app.add_handler(CommandHandler("info", info_handler))
    app.add_handler(CommandHandler("save", save_note_handler))
    app.add_handler(CommandHandler("notes", notes_handler))
    app.add_handler(CommandHandler("clean_warns", clean_warns_handler))
    app.add_handler(CommandHandler("clean_notes", clean_notes_handler))

    # ========== GROUP / WELCOME ==========
    app.add_handler(CommandHandler("setgroup", set_group_handler))
    app.add_handler(CommandHandler("removegroup", remove_group_handler))
    app.add_handler(CommandHandler("groups", groups_handler))
    app.add_handler(CommandHandler("setwelcome", set_welcome_handler))
    app.add_handler(CommandHandler("setfarewell", set_farewell_handler))
    app.add_handler(CommandHandler("togglewelcome", toggle_welcome_handler))

    # ========== UTILITIES ==========
    app.add_handler(CommandHandler("test", test_handler))
    app.add_handler(CommandHandler("chatid", chatid_handler))

    # ========== CALLBACK QUERIES ==========
    app.add_handler(CallbackQueryHandler(menu_handler))

    # ========== UNKNOWN COMMAND ==========
    app.add_handler(MessageHandler(filters.COMMAND, unknown_cmd_handler))

    logger.info("🚀 Bot is now running...")
    app.run_polling()


if __name__ == "__main__":
    main()

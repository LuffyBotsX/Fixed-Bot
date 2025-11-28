#!/usr/bin/env python3
# ===============================================================
#  FULL 2025 PREMIUM ESCROW + MODERATION + PANEL + SPAM BOT
#  PART 1 / 8 — CORE ENGINE, CONFIG, DATABASE, UTILITIES
# ===============================================================

import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
import json
from io import BytesIO
from typing import Optional, List, Dict, Any

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
)

from pymongo import MongoClient

# ===============================================================
# CONFIGURATION
# ===============================================================

BOT_TOKEN = "8389093783:AAFLpMBDJ-0nZ3G4BQrBn_Y9JhsBOEy1Jcg"   # ← you will paste your token here
OWNER_ID = 6847499628              # fixed owner id

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "mega_escrow_bot_2025"

BOT_NAME = "Luffy Premium Escrow Bot 2025"
POWERED_BY = "@LuffyBots"

IST_OFFSET = timedelta(hours=5, minutes=30)
DIVIDER = "══════════════════════════════════════"

WELCOME_DEFAULT = (
    "👋 Welcome {name}!\n"
    "Please read the rules and trade safely.\n"
    "Powered by @LuffyBots"
)

FAREWELL_DEFAULT = (
    "👋 {name} just left the group."
)

# ===============================================================
# LOGGING
# ===============================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ===============================================================
# DATABASE
# ===============================================================

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]

config_col      = db["config"]           # fee, welcome settings, spam settings
admins_col      = db["admins"]           # admin_ids
deals_col       = db["deals"]            # full escrow deals
warns_col       = db["warns"]            # moderation warns
notes_col       = db["notes"]            # saved notes
groups_col      = db["groups"]           # registered groups
log_channels    = db["log_channels"]     # logging channels
antispam_col    = db["antispam"]         # spam settings per group
joins_col       = db["joins"]            # join logs (anti-raid)
welcome_col     = db["welcome"]          # welcome & leave settings

# ===============================================================
# UTILITY FUNCTIONS
# ===============================================================

def now_ist():
    return datetime.now(timezone.utc) + IST_OFFSET


def is_owner(uid: int) -> bool:
    return uid == OWNER_ID


def is_admin(uid: int) -> bool:
    if uid == OWNER_ID:
        return True
    return admins_col.find_one({"_id": uid}) is not None


def fmt_user(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.first_name or str(user.id)


def parse_amount(txt: str) -> Optional[float]:
    if not txt:
        return None
    t = txt.lower().replace(",", "").strip()
    mul = 1
    if t.endswith("k"):
        mul = 1000
        t = t[:-1]
    elif t.endswith("m"):
        mul = 1_000_000
        t = t[:-1]
    try:
        return float(t) * mul
    except:
        return None


def calculate_fee(amount: float) -> float:
    cfg = config_col.find_one({"_id": "fee"}) or {}
    pct = cfg.get("percent", 3.0)
    min_fee = cfg.get("min_fee", 5.0)
    fee = max((amount * pct) / 100.0, min_fee)
    return round(fee, 2)


def escape_md(text: str) -> str:
    return (text.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("[", "\\[")
                .replace("`", "\\`"))


def ensure_base_config():
    if not config_col.find_one({"_id": "fee"}):
        config_col.insert_one({
            "_id": "fee",
            "percent": 3.0,
            "min_fee": 5.0,
            "updated": datetime.utcnow()
        })

    if not admins_col.find_one({"_id": OWNER_ID}):
        admins_col.insert_one({
            "_id": OWNER_ID,
            "added_at": datetime.utcnow()
        })

    if not config_col.find_one({"_id": "welcome"}):
        config_col.insert_one({
            "_id": "welcome",
            "enabled": True,
            "message": WELCOME_DEFAULT,
            "farewell": FAREWELL_DEFAULT
        })

    if not config_col.find_one({"_id": "spam"}):
        config_col.insert_one({
            "_id": "spam",
            "enabled": True,
            "max_msgs": 5,
            "interval_sec": 4,
            "action": "mute"  # ban/kick/mute
        })


def compute_fastest_escrow(user_id: int):
    """Compute fastest escrow time for a user."""
    completed = list(deals_col.find({
        "admin_id": user_id,
        "status": "completed"
    }))

    if len(completed) < 2:
        return None

    # difference between creation and completion
    durations = []
    for d in completed:
        created = d.get("created_at")
        completed_at = d.get("updated_at")
        if created and completed_at:
            durations.append((completed_at - created).total_seconds())

    if not durations:
        return None

    sec = min(durations)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    out = []
    if h > 0:
        out.append(f"{h}h")
    if m > 0:
        out.append(f"{m}m")
    if s > 0:
        out.append(f"{s}s")
    return " ".join(out) or "0s"


def get_rank(user_id: int):
    """Rank users by total volume."""
    pipeline = [
        {"$group": {"_id": "$admin_id", "vol": {"$sum": "$amount"}}},
        {"$sort": {"vol": -1}}
    ]
    ranks = list(deals_col.aggregate(pipeline))
    for i, r in enumerate(ranks, start=1):
        if r["_id"] == user_id:
            return i
    return None


def build_owner_panel():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 Admins", callback_data="panel_admins"),
            InlineKeyboardButton("⚙ Fee Config", callback_data="panel_fee")
        ],
        [
            InlineKeyboardButton("📂 Export", callback_data="panel_export"),
            InlineKeyboardButton("🗑 Reset", callback_data="panel_reset")
        ],
        [
            InlineKeyboardButton("📢 Logs", callback_data="panel_logs"),
            InlineKeyboardButton("📌 Groups", callback_data="panel_groups")
        ],
        [
            InlineKeyboardButton("🔙 Close", callback_data="panel_close")
        ]
    ])


def build_admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 My Stats", callback_data="menu_stats"),
            InlineKeyboardButton("💰 My Earnings", callback_data="menu_earn")
        ],
        [
            InlineKeyboardButton("💼 Add Deal", callback_data="menu_adddeal"),
            InlineKeyboardButton("📄 User Stats", callback_data="menu_userstats")
        ],
        [
            InlineKeyboardButton("🔧 Moderation", callback_data="menu_moderation")
        ],
        [
            InlineKeyboardButton("🔙 Close", callback_data="menu_close")
        ]
    ])

# ===============================================================
# INIT BOT
# ===============================================================

ensure_base_config()

app = Client(
    "main_bot",
    api_id=0,
    api_hash="none",
    bot_token=BOT_TOKEN,
    in_memory=True
)

log.info("PART 1 / 8 loaded successfully.")

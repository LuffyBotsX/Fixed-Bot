# database.py
# Clean + Upgraded hybrid model (A+B)
# Handles all persistent storage for Era Escrow Bot

import sqlite3
import json
from datetime import datetime, timedelta
from config import (
    DB_PATH,
    IST_OFFSET_HOURS,
    IST_OFFSET_MINUTES,
    DEFAULT_FEE_PERCENT,
    DEFAULT_MIN_FEE,
)

# ============================================================
# 📌 UTIL FUNCTIONS
# ============================================================

def connect():
    """Open database connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ist_now():
    """Return current India time."""
    return datetime.utcnow() + timedelta(
        hours=IST_OFFSET_HOURS,
        minutes=IST_OFFSET_MINUTES
    )


# ============================================================
# 📌 INITIALIZATION
# ============================================================

def init_database():
    """Create tables if missing."""
    conn = connect()
    cur = conn.cursor()

    # DEALS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT UNIQUE,
            buyer TEXT,
            seller TEXT,
            amount REAL,
            status TEXT,
            created_by INTEGER,
            created_at TEXT,
            updated_at TEXT,
            fee_percent REAL,
            fee_min REAL,
            fee_amount REAL,
            admin_earning REAL DEFAULT 0
        )
    """)

    # ADMINS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)

    # FEES
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY,
            percent REAL,
            min_fee REAL
        )
    """)

    # Insert default fee once
    cur.execute("SELECT * FROM fees")
    if not cur.fetchone():
        cur.execute("INSERT INTO fees (id, percent, min_fee) VALUES (1, ?, ?)",
                    (DEFAULT_FEE_PERCENT, DEFAULT_MIN_FEE))

    # BANS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY
        )
    """)

    # WARNS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            user_id INTEGER PRIMARY KEY,
            warns INTEGER DEFAULT 0
        )
    """)

    # NOTES
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note TEXT,
            added_by INTEGER,
            created_at TEXT
        )
    """)

    # GROUPS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY
        )
    """)

    # WELCOME / FAREWELL
    cur.execute("""
        CREATE TABLE IF NOT EXISTS welcome (
            group_id INTEGER PRIMARY KEY,
            text TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS farewell (
            group_id INTEGER PRIMARY KEY,
            text TEXT
        )
    """)

    # LOG CHANNELS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            channel_id INTEGER PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# 📌 DEAL SYSTEM
# ============================================================

def create_deal(trade_id, buyer, seller, amount, created_by):
    """Insert new deal."""
    conn = connect()
    cur = conn.cursor()

    now = ist_now().isoformat()

    # get fee settings
    cur.execute("SELECT percent, min_fee FROM fees WHERE id=1")
    fee = cur.fetchone()
    fee_percent = fee["percent"]
    min_fee = fee["min_fee"]

    # calculate fee
    fee_amount = max(amount * (fee_percent / 100), min_fee)

    cur.execute("""
        INSERT INTO deals (
            trade_id, buyer, seller, amount, status,
            created_by, created_at, updated_at,
            fee_percent, fee_min, fee_amount
        )
        VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
    """, (
        trade_id, buyer, seller, amount,
        created_by, now, now,
        fee_percent, min_fee, fee_amount
    ))

    conn.commit()
    conn.close()


def update_deal(trade_id, new_status):
    """Update deal status + apply admin earning when completed."""
    conn = connect()
    cur = conn.cursor()

    now = ist_now().isoformat()

    # If closing → give earning
    if new_status == "completed":
        cur.execute("SELECT fee_amount FROM deals WHERE trade_id=?", (trade_id,))
        row = cur.fetchone()
        earning = row["fee_amount"]
        cur.execute("UPDATE deals SET admin_earning=? WHERE trade_id=?", (earning, trade_id))

    cur.execute("UPDATE deals SET status=?, updated_at=? WHERE trade_id=?",
                (new_status, now, trade_id))

    conn.commit()
    conn.close()


def get_deal(trade_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals WHERE trade_id=?", (trade_id,))
    row = cur.fetchone()
    conn.close()
    return row


def find_active(buyer, seller, amount):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM deals
        WHERE buyer=? AND seller=? AND amount=?
        AND status='active'
    """, (buyer, seller, amount))
    row = cur.fetchone()
    conn.close()
    return row


def list_active():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals WHERE status='active'")
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================================================
# 📌 ADMIN MANAGEMENT
# ============================================================

def add_admin(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()


def remove_admin(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM admins WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()


def is_admin(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def list_admins():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins")
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================================================
# 📌 FEE SETTINGS
# ============================================================

def set_fee(percent, min_fee):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE fees SET percent=?, min_fee=? WHERE id=1",
                (percent, min_fee))
    conn.commit()
    conn.close()


def get_fee():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT percent, min_fee FROM fees WHERE id=1")
    row = cur.fetchone()
    conn.close()
    return row


# ============================================================
# 📌 USER WARNS
# ============================================================

def warn(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT warns FROM warns WHERE user_id=?", (uid,))
    row = cur.fetchone()

    if row:
        new = row["warns"] + 1
        cur.execute("UPDATE warns SET warns=? WHERE user_id=?", (new, uid))
    else:
        cur.execute("INSERT INTO warns (user_id, warns) VALUES (?, 1)", (uid,))

    conn.commit()
    conn.close()


def unwarn(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT warns FROM warns WHERE user_id=?", (uid,))
    row = cur.fetchone()

    if row and row["warns"] > 0:
        new = row["warns"] - 1
        cur.execute("UPDATE warns SET warns=? WHERE user_id=?", (new, uid))

    conn.commit()
    conn.close()


def get_warn(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT warns FROM warns WHERE user_id=?", (uid,))
    row = cur.fetchone()
    conn.close()
    return row["warns"] if row else 0


# ============================================================
# 📌 NOTES
# ============================================================

def add_note(uid, note, admin_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notes (user_id, note, added_by, created_at)
        VALUES (?, ?, ?, ?)
    """, (uid, note, admin_id, ist_now().isoformat()))
    conn.commit()
    conn.close()


def get_notes(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT note, added_by, created_at FROM notes WHERE user_id=?", (uid,))
    rows = cur.fetchall()
    conn.close()
    return rows


def clear_notes(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()


# ============================================================
# 📌 BANS
# ============================================================

def ban(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO bans (user_id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()


def unban(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM bans WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()


def is_banned(uid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM bans WHERE user_id=?", (uid,))
    row = cur.fetchone()
    conn.close()
    return bool(row)


# ============================================================
# 📌 GROUP SETTINGS
# ============================================================

def add_group(gid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO groups (group_id) VALUES (?)", (gid,))
    conn.commit()
    conn.close()


def remove_group(gid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM groups WHERE group_id=?", (gid,))
    conn.commit()
    conn.close()


def get_groups():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT group_id FROM groups")
    rows = cur.fetchall()
    conn.close()
    return rows


# welcome / farewell text
def set_welcome(gid, text):
    conn = connect()
    cur = conn.cursor()
    cur.execute("REPLACE INTO welcome (group_id, text) VALUES (?, ?)", (gid, text))
    conn.commit()
    conn.close()


def set_farewell(gid, text):
    conn = connect()
    cur = conn.cursor()
    cur.execute("REPLACE INTO farewell (group_id, text) VALUES (?, ?)", (gid, text))
    conn.commit()
    conn.close()


def get_welcome_text(gid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT text FROM welcome WHERE group_id=?", (gid,))
    row = cur.fetchone()
    conn.close()
    return row["text"] if row else None


def get_farewell_text(gid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT text FROM farewell WHERE group_id=?", (gid,))
    row = cur.fetchone()
    conn.close()
    return row["text"] if row else None


# ============================================================
# 📌 LOG CHANNELS
# ============================================================

def add_log_channel(cid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO logs (channel_id) VALUES (?)", (cid,))
    conn.commit()
    conn.close()


def remove_log_channel(cid):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM logs WHERE channel_id=?", (cid,))
    conn.commit()
    conn.close()


def get_log_channels():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT channel_id FROM logs")
    rows = cur.fetchall()
    conn.close()
    return rows

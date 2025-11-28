# database.py
# Database layer for Era Escrow Bot
# Auto-creates all tables, handles read/write operations

import sqlite3
import os

DB_PATH = "data/escrow.db"


# =====================================================
# 📌 CONNECT DATABASE
# =====================================================

def connect():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================
# 📌 INITIALIZE DATABASE (Auto-create tables)
# =====================================================

def init_database():
    conn = connect()
    cur = conn.cursor()

    # Deals table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT UNIQUE,
            buyer_username TEXT,
            seller_username TEXT,
            created_by INTEGER,
            created_by_username TEXT,
            amount REAL,
            fee REAL DEFAULT 0,
            admin_earning REAL DEFAULT 0,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # Admins table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)

    # Fee settings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY,
            percent REAL,
            min_fee REAL
        )
    """)

    # Logs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER
        )
    """)

    # Groups table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE,
            welcome_text TEXT,
            farewell_text TEXT,
            welcome_enabled INTEGER DEFAULT 1
        )
    """)

    # Warnings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            group_id INTEGER,
            reason TEXT,
            timestamp TEXT
        )
    """)

    # Bans
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            reason TEXT
        )
    """)

    # Notes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()


# =====================================================
# 📌 ADMIN HELPERS
# =====================================================

def is_admin(user_id: int) -> bool:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def add_admin(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def remove_admin(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def list_admins():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins")
    rows = cur.fetchall()
    conn.close()
    return rows


# =====================================================
# 📌 FEES
# =====================================================

def set_fee(percent, min_fee):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM fees")
    cur.execute("INSERT INTO fees (id, percent, min_fee) VALUES (1, ?, ?)", (percent, min_fee))
    conn.commit()
    conn.close()


def get_fee():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT percent, min_fee FROM fees LIMIT 1")
    row = cur.fetchone()
    conn.close()

    if row:
        return row["percent"], row["min_fee"]
    return 5, 5  # Default


# =====================================================
# 📌 LOG CHANNELS
# =====================================================

def set_logs(chat_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO logs (id, chat_id) VALUES (1, ?)", (chat_id,))
    conn.commit()
    conn.close()


def remove_logs():
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM logs WHERE id=1")
    conn.commit()
    conn.close()


def get_logs():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM logs WHERE id=1")
    row = cur.fetchone()
    conn.close()
    return row["chat_id"] if row else None


# =====================================================
# 📌 GROUP SETTINGS
# =====================================================

def set_group(chat_id, welcome, farewell):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO groups (chat_id, welcome_text, farewell_text)
        VALUES (?, ?, ?)
    """, (chat_id, welcome, farewell))
    conn.commit()
    conn.close()


def remove_group(chat_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM groups WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()


def get_groups():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM groups")
    rows = cur.fetchall()
    conn.close()
    return rows


def toggle_welcome(chat_id, enabled):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE groups SET welcome_enabled=? WHERE chat_id=?", (enabled, chat_id))
    conn.commit()
    conn.close()


def get_group_settings(chat_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM groups WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row


# =====================================================
# 📌 END DATABASE MODULE
# =====================================================

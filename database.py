"""
database.py
-----------
All MySQL access lives here so the other modules never deal with
connections directly.

Connection details are stored in config.json (created by setup.py).
"""
import hashlib
import json
import os
import secrets

import mysql.connector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "football_league",
}


# --------------------------------------------------------------------------
# Configuration / connection
# --------------------------------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def test_connection(host, port, user, password):
    """Try to connect with the given details (no database selected yet).
    Returns (True, None) or (False, error_message)."""
    try:
        conn = mysql.connector.connect(host=host, port=port, user=user, password=password)
        conn.close()
        return True, None
    except mysql.connector.Error as e:
        return False, str(e)


def initialize_database(host, port, user, password, database="football_league"):
    """Create the database and tables from setup.sql, then save the
    connection details to config.json. Raises mysql.connector.Error on
    failure - the caller decides how to show that to the user."""
    conn = mysql.connector.connect(host=host, port=port, user=user, password=password)
    try:
        cur = conn.cursor()
        sql_path = os.path.join(BASE_DIR, "setup.sql")
        with open(sql_path, "r", encoding="utf-8") as f:
            script = f.read()
        for statement in script.split(";"):
            if statement.strip():
                cur.execute(statement)
        conn.commit()
        cur.close()
    finally:
        conn.close()
    save_config({"host": host, "port": port, "user": user, "password": password, "database": database})


def get_connection():
    cfg = load_config()
    return mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
    )


# --------------------------------------------------------------------------
# Query helpers
# --------------------------------------------------------------------------
def query(sql, params=None):
    """Run a SELECT and return a list of dictionaries."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else None


def scalar(sql, params=None):
    row = query_one(sql, params)
    return list(row.values())[0] if row else 0


def execute(sql, params=None):
    """Run INSERT / UPDATE / DELETE. Returns the last inserted id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id
    finally:
        conn.close()


def migrate_roles():
    """Older databases had the roles Super Admin / Co-Admin / Viewer. Turn
    every Super Admin and Co-Admin into an Admin and shrink the column to
    ENUM('Admin','Viewer'). Safe to run on every start-up."""
    row = query_one("SELECT COLUMN_TYPE AS t FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users' AND COLUMN_NAME='role'")
    if not row or "Super Admin" not in row["t"] and "Co-Admin" not in row["t"]:
        return
    execute("ALTER TABLE users MODIFY role ENUM('Super Admin','Co-Admin','Admin','Viewer') "
            "NOT NULL DEFAULT 'Viewer'")
    execute("UPDATE users SET role='Admin' WHERE role IN ('Super Admin','Co-Admin')")
    execute("ALTER TABLE users MODIFY role ENUM('Admin','Viewer') NOT NULL DEFAULT 'Viewer'")


class BulkInserter:
    """Insert many rows in small batches (so a progress bar can follow along)
    inside ONE transaction: either every row is saved or none is."""

    def __init__(self, sql):
        self.sql = sql
        self.conn = get_connection()
        self.cur = self.conn.cursor()

    def add(self, rows):
        self.cur.executemany(self.sql, rows)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        try:
            self.conn.rollback()
        except mysql.connector.Error:
            pass

    def close(self):
        try:
            self.cur.close()
            self.conn.close()
        except mysql.connector.Error:
            pass


class Transaction:
    """Several statements, one commit: either all of them happen or none do
    (used by the pool draw, which creates pools, moves teams and removes
    empty pools)."""

    def __init__(self):
        self.conn = get_connection()
        self.cur = self.conn.cursor()

    def execute(self, sql, params=None):
        self.cur.execute(sql, params or ())
        return self.cur.lastrowid

    def commit(self):
        self.conn.commit()

    def rollback(self):
        try:
            self.conn.rollback()
        except mysql.connector.Error:
            pass

    def close(self):
        try:
            self.cur.close()
            self.conn.close()
        except mysql.connector.Error:
            pass


# --------------------------------------------------------------------------
# Passwords (salted PBKDF2 - never store plain text)
# --------------------------------------------------------------------------
def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    try:
        salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000).hex()
    return secrets.compare_digest(check, digest)


# --------------------------------------------------------------------------
# Settings (small key/value table, e.g. the Admin refer code)
# --------------------------------------------------------------------------
def get_setting(name, default=None):
    row = query_one("SELECT setting_value FROM settings WHERE setting_name=%s", (name,))
    return row["setting_value"] if row else default


def set_setting(name, value):
    execute("INSERT INTO settings (setting_name, setting_value) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)", (name, value))


# --------------------------------------------------------------------------
# Shared lookups
# --------------------------------------------------------------------------
def get_pools(category=None):
    if category:
        return query("SELECT id, category, name FROM pools WHERE category=%s ORDER BY name", (category,))
    return query("SELECT id, category, name FROM pools ORDER BY category, name")


def pool_names(category=None):
    """Distinct pool names (used to fill filter drop-downs)."""
    if category:
        rows = query("SELECT DISTINCT name FROM pools WHERE category=%s ORDER BY name", (category,))
    else:
        rows = query("SELECT DISTINCT name FROM pools ORDER BY name")
    return [r["name"] for r in rows]


FIXTURE_SQL = """
SELECT f.id, f.category, f.match_date, f.match_time, f.venue, f.status,
       f.home_score, f.away_score, f.home_team_id, f.away_team_id, f.pool_id,
       h.name AS home, a.name AS away, p.name AS pool
FROM fixtures f
JOIN teams h ON h.id = f.home_team_id
JOIN teams a ON a.id = f.away_team_id
JOIN pools p ON p.id = f.pool_id
"""


def get_fixtures(where="", params=None, order="f.match_date, f.match_time", limit=None):
    """Fixtures joined with team and pool names. `where` is an SQL fragment
    written by our own code; user values always go through `params`."""
    sql = FIXTURE_SQL
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY {order}"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return query(sql, params)

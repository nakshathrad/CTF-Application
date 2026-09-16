"""
GuardianMart — db.py

Connection helper + query functions over a plain sqlite3 file. No ORM,
on purpose (see README §1) — an ORM would parameterise everything and
quietly remove the A05a SQL injection challenge.

Everything in here is parameterised EXCEPT raw_login_lookup(), which is
deliberately built with string formatting. That is the one function in
this file that should never be "fixed" — it is the challenge.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "guardianmart.db")


def get_db():
    """New connection per call, rows addressable by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema():
    """Create all tables. Idempotent — safe to call on an existing DB."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,             -- plaintext, on purpose: A04 / A05a / A07a
            department TEXT,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'user'    -- 'user' or 'admin'
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT,
            image TEXT,
            stock INTEGER DEFAULT 100
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            address TEXT,
            delivery_notes TEXT,
            status TEXT DEFAULT 'placed',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT,
            qty INTEGER,
            unit_price REAL,
            line_total REAL
        );

        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            encoded_value TEXT NOT NULL,          -- base64, NOT encryption: A04
            discount_percent INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT,
            message TEXT,                         -- rendered with |safe on /support/admin: A05b
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            uploaded_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def raw_login_lookup(email, password):
    """
    A05a — SQL injection, intentionally.

    Built with an f-string instead of parameters, exactly as specced.
    A tautology like `' OR '1'='1' --` in `email` returns the first
    matching row regardless of `password` — which, because admin is
    always seeded first (id=1), is how the bypass hands you the admin
    account. Do not parameterise this query.
    """
    conn = get_db()
    query = f"SELECT * FROM users WHERE email='{email}' AND password='{password}'"
    row = conn.execute(query).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def create_user(name, email, password, department, phone="", role="user"):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password, department, phone, role) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, password, department, phone, role),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_user_profile(user_id, name, email, department, phone):
    conn = get_db()
    conn.execute(
        "UPDATE users SET name = ?, email = ?, department = ?, phone = ? WHERE id = ?",
        (name, email, department, phone, user_id),
    )
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def get_all_products(search=None, category=None):
    conn = get_db()
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_product_by_id(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return row


def get_categories():
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()
    conn.close()
    return [r["category"] for r in rows]


def update_product_price(product_id, new_price):
    conn = get_db()
    conn.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, product_id))
    conn.commit()
    conn.close()


def insert_product(name, description, price, category, image, stock=100):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, description, price, category, image, stock) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, description, price, category, image, stock),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


# ---------------------------------------------------------------------------
# Orders — see app.py for the A01a IDOR check that's missing on purpose.
# This layer just runs the query it's given; it doesn't know or care who's
# asking.
# ---------------------------------------------------------------------------

def insert_order(order_id, user_id, total, address, delivery_notes, created_at, status="placed"):
    """Explicit-id insert — seed.py uses this to pin order #7 for A01a."""
    conn = get_db()
    conn.execute(
        "INSERT INTO orders (id, user_id, total, address, delivery_notes, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (order_id, user_id, total, address, delivery_notes, status, created_at),
    )
    conn.commit()
    conn.close()


def create_order(user_id, total, address, delivery_notes, created_at, status="placed"):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO orders (user_id, total, address, delivery_notes, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, total, address, delivery_notes, status, created_at),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_order_total(order_id, total):
    conn = get_db()
    conn.execute("UPDATE orders SET total = ? WHERE id = ?", (total, order_id))
    conn.commit()
    conn.close()


def add_order_item(order_id, product_id, product_name, qty, unit_price, line_total):
    conn = get_db()
    conn.execute(
        "INSERT INTO order_items (order_id, product_id, product_name, qty, unit_price, line_total) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (order_id, product_id, product_name, qty, unit_price, line_total),
    )
    conn.commit()
    conn.close()


def get_orders_for_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_order_by_id(order_id):
    """No ownership filter — intentionally. The check belongs in app.py,
    and skipping it there is the whole A01a challenge."""
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return row


def get_order_items(order_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    conn.close()
    return rows


def get_all_orders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------

def get_coupon_by_code(code):
    conn = get_db()
    row = conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row


def insert_coupon(code, encoded_value, discount_percent):
    conn = get_db()
    conn.execute(
        "INSERT INTO coupons (code, encoded_value, discount_percent) VALUES (?, ?, ?)",
        (code, encoded_value, discount_percent),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Support tickets
# ---------------------------------------------------------------------------

def create_ticket(user_id, subject, message, created_at):
    conn = get_db()
    conn.execute(
        "INSERT INTO tickets (user_id, subject, message, created_at) VALUES (?, ?, ?, ?)",
        (user_id, subject, message, created_at),
    )
    conn.commit()
    conn.close()


def get_all_tickets():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_tickets_for_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------

def create_claim(user_id, filename, original_filename, uploaded_at):
    conn = get_db()
    conn.execute(
        "INSERT INTO claims (user_id, filename, original_filename, uploaded_at) "
        "VALUES (?, ?, ?, ?)",
        (user_id, filename, original_filename, uploaded_at),
    )
    conn.commit()
    conn.close()


def get_claims_for_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM claims WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows

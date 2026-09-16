"""
GuardianMart — seed.py

Wipes and recreates guardianmart.db, then fills it with synthetic data.
Run this before `python app.py`, and any time you want a clean slate:

    python seed.py

Everything here is made up for training purposes: names, emails, orders,
tickets. No production data, ever.
"""

import base64
import os
import random
from datetime import datetime, timedelta

import db
from flags import FLAGS

random.seed(42)  # same seed data on every run, so flags land in the same spot


def reset_db():
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    db.init_schema()


def seed_products():
    products = [
        # (name, description, price INR, category, image)
        ("Yoga Mat & Kit", "Non-slip mat, block, and strap set.", 799, "Wellness Kits", "yoga-mat.jpg"),
        ("Ayurveda Wellness Box", "Curated box of Ayurvedic self-care essentials.", 1299, "Wellness Kits", "ayurveda-box.jpg"),
        ("Fitness Tracker Band", "Step count, heart rate, and sleep tracking.", 2499, "Wellness Kits", "fitness-band.jpg"),
        ("Ergonomic Desk Cushion", "Lumbar support cushion for long work days.", 999, "Wellness Kits", "desk-cushion.jpg"),
        ("Meditation App — 1 Yr", "Annual subscription to a guided meditation app.", 599, "Wellness Kits", "meditation-app.jpg"),
        ("Dental Care Add-on", "Covers routine and major dental procedures.", 1500, "Insurance Add-ons", "dental.jpg"),
        ("OPD Cover Add-on", "Out-patient consultation and diagnostics cover.", 2000, "Insurance Add-ons", "opd.jpg"),
        ("Critical Illness Top-up", "Extra cover on critical illness diagnosis.", 5000, "Insurance Add-ons", "critical-illness.jpg"),
        ("Family Floater Extension", "Extends your base policy to more dependants.", 3500, "Insurance Add-ons", "family-floater.jpg"),
        ("Accidental Cover Add-on", "Additional payout on accidental injury.", 1200, "Insurance Add-ons", "accidental.jpg"),
        ("Amazon Gift Voucher \u20b9500", "Digital gift voucher, delivered by email.", 500, "Gift Vouchers", "amazon-500.jpg"),
        ("Amazon Gift Voucher \u20b91000", "Digital gift voucher, delivered by email.", 1000, "Gift Vouchers", "amazon-1000.jpg"),
        ("Myntra Gift Voucher \u20b9750", "Digital gift voucher, delivered by email.", 750, "Gift Vouchers", "myntra-750.jpg"),
        ("BookMyShow Voucher \u20b9300", "Digital voucher for movies and events.", 300, "Gift Vouchers", "bms-300.jpg"),
        ("Swiggy Voucher \u20b9400", "Digital food delivery voucher.", 400, "Gift Vouchers", "swiggy-400.jpg"),
        ("Noise-Cancelling Earbuds", "Reimbursement for a pair of ANC earbuds.", 3000, "Tech Perks", "earbuds.jpg"),
        ("Home WiFi Extender", "Reimbursement toward a WiFi range extender.", 1800, "Tech Perks", "wifi-extender.jpg"),
        ("Ergonomic Mouse", "Vertical ergonomic mouse for WFH setups.", 899, "Tech Perks", "mouse.jpg"),
        ("Laptop Stand", "Adjustable aluminium laptop stand.", 1099, "Tech Perks", "laptop-stand.jpg"),
        ("Blue-Light Glasses", "Reimbursement for a pair of blue-light glasses.", 699, "Tech Perks", "glasses.jpg"),
    ]
    for name, desc, price, category, image in products:
        db.insert_product(name, desc, price, category, image)


def seed_users():
    # id=1, admin, inserted first on purpose — app.py's A05a bypass relies
    # on this being the row SQLite hands back for a tautology WHERE clause.
    admin_id = db.create_user(
        "Guardian Admin", "admin@guardianmart.local", "Welcome@123",
        "IT Security", "9840000000", role="admin",
    )

    names = [
        "Aditi Rao", "Rohan Mehta", "Priya Sharma", "Kiran Kumar", "Ananya Iyer",
        "Vikram Nair", "Sneha Reddy", "Arjun Pillai", "Divya Menon", "Karthik Subramaniam",
        "Meera Krishnan", "Sanjay Gupta", "Lakshmi Venkatesh", "Rahul Desai", "Pooja Varma",
    ]
    departments = ["Finance", "Operations", "HR", "IT", "Sales", "Marketing", "Legal", "Claims"]

    user_ids = [admin_id]
    for i, name in enumerate(names):
        first, last = name.split()
        email = f"{first.lower()}.{last.lower()}@guardianmart.local"
        password = f"{first}@123"  # plaintext, matches how /login authenticates
        dept = departments[i % len(departments)]
        phone = f"98400{10000 + i}"
        uid = db.create_user(name, email, password, dept, phone, role="user")
        user_ids.append(uid)

    return user_ids  # [admin_id, *15 regular user ids]


def seed_coupons():
    coupons = [("WELCOME10", 10), ("FESTIVE20", 20), ("LOYAL15", 15)]
    for code, pct in coupons:
        encoded = base64.b64encode(f"{code}:{pct}".encode()).decode()
        db.insert_coupon(code, encoded, pct)


def seed_orders(user_ids):
    admin_id = user_ids[0]
    regular_users = user_ids[1:]
    products = db.get_all_products()

    addresses = [
        "Guardian LIC Towers, OMR, Chennai",
        "12th Floor, Egattur Campus, Chennai",
        "Block C, Tech Park, Chennai",
        "Remote — WFH",
    ]
    now = datetime.now()

    for order_id in range(1, 41):
        if order_id == 7:
            # A01a — pinned flag order. Belongs to admin, never to whoever
            # is logged in, and only reachable by walking the URL.
            user_id = admin_id
            delivery_notes = FLAGS["A01_IDOR"]
            address = "Guardian LIC HQ, Executive Floor, Chennai"
        else:
            user_id = random.choice(regular_users)
            delivery_notes = random.choice([
                "Leave at reception.", "Call on arrival.", "",
                "Deliver after 6 PM.", "Handover to security desk.",
            ])
            address = random.choice(addresses)

        item_count = random.randint(1, 3)
        chosen = random.sample(products, item_count)
        created_at = (now - timedelta(days=random.randint(0, 120))).strftime("%Y-%m-%d %H:%M:%S")

        db.insert_order(order_id, user_id, 0, address, delivery_notes, created_at)

        total = 0.0
        for p in chosen:
            qty = random.randint(1, 3)
            line_total = p["price"] * qty
            total += line_total
            db.add_order_item(order_id, p["id"], p["name"], qty, p["price"], line_total)

        db.update_order_total(order_id, total)


def seed_tickets(user_ids):
    regular_users = user_ids[1:]
    tickets = [
        ("Payslip not visible", "I can't see last month's payslip under my profile. Can someone check?"),
        ("Voucher not received", "Ordered an Amazon voucher two weeks ago, still no email."),
        ("Wrong department listed", "My profile shows Sales but I moved to Marketing in March."),
        ("Claim status query", "Submitted a claim document last week, no update since."),
        ("Basket coupon not applying", "The FESTIVE20 code isn't reducing my total at checkout."),
    ]
    now = datetime.now()
    for i, (subject, message) in enumerate(tickets):
        uid = regular_users[i % len(regular_users)]
        created_at = (now - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S")
        db.create_ticket(uid, subject, message, created_at)


def main():
    print("Resetting guardianmart.db ...")
    reset_db()
    print("Seeding products (20) ...")
    seed_products()
    print("Seeding users (1 admin + 15 employees) ...")
    user_ids = seed_users()
    print("Seeding coupons (3) ...")
    seed_coupons()
    print("Seeding orders (40, #7 pinned to admin for A01a) ...")
    seed_orders(user_ids)
    print("Seeding support tickets (5) ...")
    seed_tickets(user_ids)
    print("Done.")
    print("  Admin login: admin@guardianmart.local / Welcome@123")
    print("  Employee logins: <firstname>.<lastname>@guardianmart.local / <Firstname>@123")


if __name__ == "__main__":
    main()

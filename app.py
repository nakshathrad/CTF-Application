"""
GuardianMart — app.py

A fictional internal employee-benefits storefront, deliberately built with
13 vulnerabilities across the OWASP Top 10:2025, for an easy, browser-only
CTF. Non-cybersec colleagues are the audience — every bug here is reachable
with nothing but a browser, DevTools, and the URL bar.

THIS APP IS INTENTIONALLY INSECURE. Every "bug" flagged in a comment below
is the point, not an oversight — do not "fix" it. See CHALLENGES.md for the
full vuln -> route -> flag map (once that file exists — week 1 draft still
needs it).

Run:
    python seed.py      # once, and again any time you want a clean slate
    python app.py        # -> http://0.0.0.0:5000
"""

import base64
import mimetypes
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, Response, abort, make_response, redirect,
    render_template, request, send_from_directory, url_for,
)

import db
from flags import FLAGS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB — a sane upload cap, not part of the lesson

TRAINING_BANNER = (
    "\u26a0 GuardianMart is an intentionally vulnerable training application. "
    "Runs on an isolated local instance only. Do not reuse this code, or "
    "these credentials, anywhere real."
)

# In-memory basket + applied coupon, keyed by user id. A dict is enough for
# a single-process LAN event; nothing here needs to survive a restart.
BASKETS = {}
APPLIED_COUPONS = {}


# ---------------------------------------------------------------------------
# Session helpers
#
# A07b — this is a plaintext, unsigned cookie, NOT Flask's signed session.
# gm_session looks like: "user_id:7|role:user|dept:finance". Edit role in
# DevTools -> Application -> Cookies and every route below trusts it as-is.
# ---------------------------------------------------------------------------

def parse_session_cookie(raw):
    if not raw:
        return None
    parts = {}
    for chunk in raw.split("|"):
        if ":" not in chunk:
            return None
        k, v = chunk.split(":", 1)
        parts[k] = v
    if "user_id" not in parts or "role" not in parts:
        return None
    try:
        parts["user_id"] = int(parts["user_id"])
    except ValueError:
        return None
    return parts


def build_session_cookie(user_id, role, dept):
    # Lowercase and de-space the department so the cookie value never
    # contains a character that makes the browser quote it. A quoted
    # value still works, but it looks confusing in DevTools and the
    # A07b challenge is all about reading and editing this by hand.
    dept_slug = (dept or "").strip().lower().replace(" ", "-")
    return f"user_id:{user_id}|role:{role}|dept:{dept_slug}"


def current_session():
    """Parsed cookie dict, or None. role/dept come straight from the
    client and are never re-checked against the DB — that's A07b, not a
    bug to quietly patch here."""
    return parse_session_cookie(request.cookies.get("gm_session"))


def current_user_row():
    sess = current_session()
    if not sess:
        return None
    return db.get_user_by_id(sess["user_id"])


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_session() is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    # Makes the banner + current user/session available in every template
    # without every route having to pass them explicitly.
    return {
        "training_banner": TRAINING_BANNER,
        "logged_in_user": current_user_row(),
        "logged_in_session": current_session(),
    }


# ---------------------------------------------------------------------------
# A09 — insecure logging: verbose, includes secrets, web-readable later on.
# ---------------------------------------------------------------------------

def log_event(line):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {line}\n")


# ---------------------------------------------------------------------------
# A10 part 2 — fail-open coupon validation
# ---------------------------------------------------------------------------

def validate_coupon(raw_code):
    """
    Look up a real coupon first. Failing that, try to treat the input as
    the same base64 blob the basket shows the client (see A04) and pull a
    discount out of it. If THAT throws for any reason, fail OPEN instead
    of closed — a malformed code like "%%%" gets a free 100% discount.
    This is the bug (A10), not a missing try/except to add.
    """
    coupon = db.get_coupon_by_code(raw_code)
    if coupon:
        return coupon["discount_percent"], False  # (discount_percent, fail_open)

    try:
        padded = raw_code + "=" * (-len(raw_code) % 4)
        decoded = base64.b64decode(padded).decode()
        _, pct = decoded.split(":")
        return int(pct), False
    except Exception:
        return 100, True


# ---------------------------------------------------------------------------
# 1. Home
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    featured = db.get_all_products()[:4]
    announcements = [
        "Open enrolment for wellness benefits closes 30 Sep.",
        "New: Tech Perks category is now live.",
        "Support tickets are reviewed within 2 working days.",
    ]
    return render_template("home.html", featured=featured, announcements=announcements)


# ---------------------------------------------------------------------------
# 2 & 3. Catalogue + product detail
# ---------------------------------------------------------------------------

@app.route("/products")
def products():
    q = request.args.get("q", "")
    category = request.args.get("category", "")
    items = db.get_all_products(search=q or None, category=category or None)
    categories = db.get_categories()
    return render_template("products.html", products=items, categories=categories,
                            q=q, category=category)


@app.route("/product/<product_id>")
def product_detail(product_id):
    # A10 part 1 — no try/except around the cast, and debug=True below
    # means a non-integer id shows a full Werkzeug stack trace (file
    # paths, the DB location, source snippets) instead of a clean 404.
    pid = int(product_id)
    product = db.get_product_by_id(pid)
    if product is None:
        abort(404)
    return render_template("product_detail.html", product=product)


# ---------------------------------------------------------------------------
# 4, 5, 6. Register / Login / Logout
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        department = request.form.get("department", "")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        if db.get_user_by_email(email):
            return render_template("register.html", error="An account with that email already exists.")

        db.create_user(name, email, password, department, role="user")
        return redirect(url_for("login"))

    return render_template("register.html", error=None)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        # A09 — logging the raw password verbatim is the bug. Don't redact it.
        log_event(f"LOGIN ATTEMPT email={email!r} password={password!r} ip={request.remote_addr}")

        # A05a — SQL injection. String-formatted query, run as-is.
        user = db.raw_login_lookup(email, password)

        if user is None:
            log_event(f"LOGIN FAILED email={email!r}")
            return render_template("login.html", error="Invalid email or password.")

        # If the row that came back has a *stored* password different from
        # what was submitted, the WHERE clause was manipulated rather than
        # satisfied honestly — i.e. this is an injection bypass.
        bypassed = user["password"] != password
        cookie_value = build_session_cookie(user["id"], user["role"], user["department"] or "")
        log_event(f"LOGIN OK user_id={user['id']} role={user['role']} cookie={cookie_value!r}")

        if bypassed:
            resp = make_response(render_template(
                "login.html", error=None,
                welcome_flag=FLAGS["A05_SQLI"], welcome_name=user["name"],
            ))
        else:
            resp = make_response(redirect(url_for("home")))

        max_age = 60 * 60 * 24 * 30 if remember else None
        resp.set_cookie("gm_session", cookie_value, max_age=max_age)
        return resp

    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("home")))
    resp.delete_cookie("gm_session")
    return resp


# ---------------------------------------------------------------------------
# 7. Profile
# ---------------------------------------------------------------------------

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    sess = current_session()
    user = current_user_row()

    if request.method == "POST":
        name = request.form.get("name", user["name"])
        email = request.form.get("email", user["email"])
        department = request.form.get("department", user["department"])
        phone = request.form.get("phone", user["phone"])
        db.update_user_profile(user["id"], name, email, department, phone)
        user = current_user_row()

    # A07b — authorisation decided from the cookie's role, never the DB's.
    # Flip gm_session to role:admin and this flips too, no matter what the
    # users table actually says.
    is_admin_session = sess["role"] == "admin"
    flag = FLAGS["A07_AUTH"] if is_admin_session else None

    return render_template("profile.html", user=user, is_admin_session=is_admin_session, flag=flag)


# ---------------------------------------------------------------------------
# 8 & 9. Basket + checkout
# ---------------------------------------------------------------------------

@app.route("/basket", methods=["GET", "POST"])
@login_required
def basket():
    uid = current_session()["user_id"]
    BASKETS.setdefault(uid, [])

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            product_id = int(request.form.get("product_id"))
            qty = int(request.form.get("qty", 1))
            product = db.get_product_by_id(product_id)
            if product:
                BASKETS[uid].append({
                    "product_id": product["id"],
                    "name": product["name"],
                    "unit_price": product["price"],
                    "qty": qty,
                })

        elif action == "update_qty":
            idx = int(request.form.get("index"))
            qty = int(request.form.get("qty", 1))
            if 0 <= idx < len(BASKETS[uid]):
                BASKETS[uid][idx]["qty"] = qty

        elif action == "remove":
            idx = int(request.form.get("index"))
            if 0 <= idx < len(BASKETS[uid]):
                BASKETS[uid].pop(idx)

        elif action == "apply_coupon":
            code = request.form.get("coupon_code", "").strip()
            discount_percent, fail_open = validate_coupon(code)
            coupon_row = db.get_coupon_by_code(code)
            encoded = coupon_row["encoded_value"] if coupon_row else base64.b64encode(
                f"{code}:{discount_percent}".encode()
            ).decode()
            APPLIED_COUPONS[uid] = {
                "code": code,
                "discount_percent": discount_percent,
                "fail_open": fail_open,
                "encoded_value": encoded,  # A04 — shown as-is, decodable via atob()
            }

        return redirect(url_for("basket"))

    items = BASKETS[uid]
    subtotal = sum(i["unit_price"] * i["qty"] for i in items)
    applied = APPLIED_COUPONS.get(uid)
    coupon_flag = FLAGS["A10_EXCEPTION"] if applied and applied.get("fail_open") else None

    return render_template("basket.html", items=items, subtotal=subtotal,
                            applied_coupon=applied, coupon_flag=coupon_flag)


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    uid = current_session()["user_id"]

    product_ids = request.form.getlist("product_id")
    names = request.form.getlist("name")
    quantities = request.form.getlist("qty")
    unit_prices = request.form.getlist("unit_price")  # A06 — trusted straight off the hidden field

    if not product_ids:
        return redirect(url_for("basket"))

    address = request.form.get("address", "Employee address on file")
    delivery_notes = request.form.get("delivery_notes", "")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line_items = []
    total = 0.0
    for pid, name, qty_raw, price_raw in zip(product_ids, names, quantities, unit_prices):
        qty = int(qty_raw)              # no lower bound — negative qty allowed (A06)
        unit_price = float(price_raw)   # never re-priced against the products table
        line_total = qty * unit_price
        total += line_total
        line_items.append((int(pid), name, qty, unit_price, line_total))

    order_id = db.create_order(uid, total, address, delivery_notes, created_at)
    for pid, name, qty, unit_price, line_total in line_items:
        db.add_order_item(order_id, pid, name, qty, unit_price, line_total)

    BASKETS[uid] = []
    APPLIED_COUPONS.pop(uid, None)

    flag = FLAGS["A06_INSECURE_DESIGN"] if total <= 0 else None
    return render_template("order_confirmation.html", order_id=order_id, total=total, flag=flag)


# ---------------------------------------------------------------------------
# 10 & 11. Order history + order detail
# ---------------------------------------------------------------------------

@app.route("/orders")
@login_required
def orders():
    uid = current_session()["user_id"]
    my_orders = db.get_orders_for_user(uid)
    return render_template("orders.html", orders=my_orders)


@app.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    # A01a — no check that order.user_id == the logged-in user's id.
    # Compare with /orders above, which filters correctly. Order #7
    # belongs to admin; walking the URL here is the whole challenge.
    order = db.get_order_by_id(order_id)
    if order is None:
        abort(404)
    items = db.get_order_items(order_id)
    return render_template("order_detail.html", order=order, items=items)


# ---------------------------------------------------------------------------
# 12. Claims upload
# ---------------------------------------------------------------------------

ALLOWED_CLAIM_EXTENSIONS = {".pdf"}  # enforced client-side only — see claims.html (A08)


@app.route("/claims", methods=["GET", "POST"])
@login_required
def claims():
    uid = current_session()["user_id"]
    flag = None

    if request.method == "POST":
        f = request.files.get("claim_file")
        if f and f.filename:
            # os.path.basename strips any directory components the client
            # sends — that's a path-traversal guard, not part of the A08
            # lesson, which is purely about the missing type check below.
            original_name = os.path.basename(f.filename)
            ext = os.path.splitext(original_name)[1].lower()

            # A08 — no server-side type/size/extension check at all. The
            # client-side accept=".pdf" in claims.html is the only gate.
            safe_name = f"{uid}_{int(datetime.now().timestamp())}_{original_name}"
            f.save(os.path.join(UPLOAD_DIR, safe_name))

            uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.create_claim(uid, safe_name, original_name, uploaded_at)

            if ext not in ALLOWED_CLAIM_EXTENSIONS:
                flag = FLAGS["A08_INTEGRITY"]

    my_claims = db.get_claims_for_user(uid)
    return render_template("claims.html", claims=my_claims, flag=flag)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # A08 continued — served back with a guessed content type, so an
    # uploaded .html file renders as HTML instead of downloading as data.
    guessed_type, _ = mimetypes.guess_type(filename)
    return send_from_directory(UPLOAD_DIR, filename, mimetype=guessed_type)


# ---------------------------------------------------------------------------
# 13 & 14. Support tickets
# ---------------------------------------------------------------------------

@app.route("/support", methods=["GET", "POST"])
@login_required
def support():
    uid = current_session()["user_id"]

    if request.method == "POST":
        subject = request.form.get("subject", "")
        message = request.form.get("message", "")  # stored as-is, feeds A05b
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.create_ticket(uid, subject, message, created_at)
        return redirect(url_for("support"))

    my_tickets = db.get_tickets_for_user(uid)
    return render_template("support.html", tickets=my_tickets)


@app.route("/support/admin")
@login_required
def support_admin():
    sess = current_session()
    if sess["role"] != "admin":
        abort(403)
    tickets = db.get_all_tickets()
    # A05b — support_admin.html renders ticket.message with |safe, so a
    # stored <script> payload fires right here when "admin" views it.
    return render_template("support_admin.html", tickets=tickets, xss_flag=FLAGS["A05_XSS"])


# ---------------------------------------------------------------------------
# 15. Admin panel
# ---------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_panel():
    # A01b — checks authentication only (is there a valid session cookie?),
    # never authorisation (is role == 'admin'?). Not linked in the nav for
    # normal users, but the route itself has no gate at all.
    users = db.get_all_users()
    all_orders = db.get_all_orders()
    products_list = db.get_all_products()
    return render_template("admin.html", users=users, orders=all_orders,
                            products=products_list, flag=FLAGS["A01_BFLA"])


@app.route("/admin/product/<int:product_id>/price", methods=["POST"])
@login_required
def admin_update_price(product_id):
    try:
        new_price = float(request.form.get("price"))
    except (TypeError, ValueError):
        return redirect(url_for("admin_panel"))
    db.update_product_price(product_id, new_price)
    return redirect(url_for("admin_panel"))


# ---------------------------------------------------------------------------
# 16 & 17. About / Scoreboard stub
# ---------------------------------------------------------------------------

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/scoreboard")
def scoreboard():
    # Week 1: static stub. Week 2: real scoreboard, teams, scoring.
    return render_template("scoreboard.html")


# ---------------------------------------------------------------------------
# 18. robots.txt  +  A02 directory listing  +  A09 log exposure
# ---------------------------------------------------------------------------

@app.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nDisallow: /static/backup/\n"
    return Response(content, mimetype="text/plain")


@app.route("/static/backup/")
def backup_listing():
    # A02 — directory listing enabled on a path robots.txt just told you
    # to avoid. The interesting files here (users_2024.bak etc.) are
    # static assets, not generated by this route.
    backup_dir = os.path.join(app.static_folder, "backup")
    os.makedirs(backup_dir, exist_ok=True)
    files = sorted(os.listdir(backup_dir))
    return render_template("dir_listing.html", dir_name="/static/backup/", files=files)


@app.route("/logs/app.log")
def view_log():
    # A09 — logs/ sits outside static/ but is still served directly, and
    # it's full of things (session cookies, plaintext passwords) that
    # should never be web-readable. No alerting on repeated failures
    # either — 100 failed logins here would be completely silent.
    banner = f"# {FLAGS['A09_LOGGING']}\n# (log files should never be web-readable — see CHALLENGES.md)\n\n"
    if not os.path.exists(LOG_FILE):
        return Response(banner, mimetype="text/plain")
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(banner + content, mimetype="text/plain")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.path.exists(db.DB_PATH):
        print("No database found — run `python seed.py` first.")
    app.run(host="0.0.0.0", port=5000, debug=True)

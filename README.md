# GuardianMart

A deliberately vulnerable Flask application for an internal Capture The Flag
training event. A fictional employee-benefits storefront with 13 planted
vulnerabilities covering all ten OWASP Top 10:2025 categories.

Built for colleagues in Operations, Finance and other non-security functions —
**every challenge is solvable with a browser, DevTools and the URL bar.** No
Burp, no Postman, no terminal.

> ⚠️ **This application is intentionally insecure.** It runs on an isolated
> local instance only, carries a training banner on every page, and uses
> entirely synthetic data. Do not deploy it anywhere reachable, do not reuse
> any code from it, and do not reuse any credential in it.

---

## Run it

Requires Python 3.11+.

```bash
pip install -r requirements.txt
python seed.py       # creates and populates guardianmart.db
python app.py        # serves on http://0.0.0.0:5000
```

Open <http://127.0.0.1:5000>. For LAN access on event day, players use the
host's IP on port 5000.

Re-run `python seed.py` any time to get a clean slate. It drops and rebuilds
the database.

---

## Logins

| Account | Email | Password |
|---|---|---|
| Admin | `admin@guardianmart.local` | `Welcome@123` |
| Employees (15) | `<first>.<last>@guardianmart.local` | `<First>@123` |

For example: `aditi.rao@guardianmart.local` / `Aditi@123`.

Players can also self-register at `/register`. All identities are synthetic.

---

## Layout

```
guardianmart/
├── app.py                 # all routes
├── db.py                  # sqlite3 helpers and queries
├── seed.py                # builds guardianmart.db
├── flags.py               # FLAGS dict — the interface to week 2
├── requirements.txt
├── CHALLENGES.md          # facilitator reference — NOT for players
├── templates/             # Jinja2
├── static/
│   ├── css/app.css
│   ├── js/app.js
│   ├── vendor/            # A03 lives here
│   └── backup/            # A02 and A04 live here
├── uploads/               # A08 lands here
└── logs/                  # A09 lives here
```

`guardianmart.db`, `uploads/*` and `logs/*.log` are gitignored — all three are
generated at runtime.

---

## Scope

**Week 1 (this repo):** the vulnerable application. All pages, all
functionality, all 13 vulnerabilities reachable and demonstrable. Flags are
displayed as plain text in-page on success.

**Week 2:** scoreboard, team registration, hints, flag submission, scoring,
first-blood bonus.

**Interface between them:** `flags.py` exposes a single `FLAGS` dict. The week
2 platform imports or receives it. Nothing in week 1 depends on the platform
existing.

Flag capture is display-only. Solving a challenge reveals the flag string and
nothing else — no privilege is granted, no state is changed, nothing is
executed on the player's behalf. It is a simulation.

---

## Coverage

| Category | Challenge(s) | Route(s) |
|---|---|---|
| A01 Broken Access Control | IDOR + admin panel | `/order/<id>`, `/admin` |
| A02 Security Misconfiguration | robots.txt → dir listing | `/robots.txt`, `/static/backup/` |
| A03 Software Supply Chain Failures | Stale deps, no SRI | `/static/vendor/` |
| A04 Cryptographic Failures | Plaintext backup, base64 coupon | `/static/backup/users_2024.bak` |
| A05 Injection | SQLi login + stored XSS | `/login`, `/support` → `/support/admin` |
| A06 Insecure Design | Client-side price | `/checkout` |
| A07 Authentication Failures | Default creds + cookie role | `/login`, cookie |
| A08 Software/Data Integrity | Client-only upload filter | `/claims` |
| A09 Logging & Alerting | Exposed logs, no alerting | `/logs/app.log` |
| A10 Mishandling of Exceptions | Stack trace + fail-open coupon | `/product/<id>`, `/basket` |

Routes, solution paths and flags for each: see `CHALLENGES.md`.

---

## Notes for maintainers

Several things in this codebase look like mistakes and are not. They are
commented in place. The main ones:

- `db.raw_login_lookup()` uses an f-string instead of parameters. Do not
  parameterise it — that is challenge 6.
- The session cookie is plaintext and unsigned, not Flask's signed session.
- `support_admin.html` renders ticket bodies with `|safe`.
- `/checkout` trusts `unit_price` and `qty` from hidden form fields.
- `/admin` checks authentication but never authorisation.
- `validate_coupon()` fails open by design.
- `debug=True` in `app.run()` is required for the A10 stack trace.

Two guards **are** real and should stay: uploaded filenames go through
`os.path.basename()` (path traversal), and `MAX_CONTENT_LENGTH` caps uploads at
10 MB. Neither is part of any lesson, and this app is LAN-accessible during the
event.

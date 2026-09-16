# GuardianMart — Challenges

Facilitator reference. **Do not hand this to players.**

13 challenges across all 10 OWASP Top 10:2025 categories. Every one is
solvable with a browser, DevTools and the URL bar. No Burp, no Postman,
no terminal.

Flags are shown in-page on success and are display-only — nothing is
unlocked or executed on the player's behalf. Week 2's scoreboard takes
over submission and scoring.

**Difficulty:** ★ easy, ★★ moderate.

---

## Quick reference

| # | Category | Challenge | Route | Flag key | ★ |
|---|---|---|---|---|---|
| 1 | A01 | IDOR on order detail | `/order/<id>` | `A01_IDOR` | ★ |
| 2 | A01 | Missing function-level access control | `/admin` | `A01_BFLA` | ★★ |
| 3 | A02 | robots.txt → directory listing | `/robots.txt`, `/static/backup/` | `A02_MISCONFIG` | ★ |
| 4 | A03 | Stale vendored deps, no SRI | `/static/vendor/` | `A03_SUPPLY_CHAIN` | ★ |
| 5 | A04 | Plaintext backup + base64 coupon | `/static/backup/users_2024.bak` | `A04_CRYPTO` | ★ |
| 6 | A05 | SQL injection on login | `POST /login` | `A05_SQLI` | ★★ |
| 7 | A05 | Stored XSS on support tickets | `/support` → `/support/admin` | `A05_XSS` | ★★ |
| 8 | A06 | Client-side price / negative qty | `POST /checkout` | `A06_INSECURE_DESIGN` | ★★ |
| 9 | A07 | Default credentials | `POST /login` | `A07_AUTH` | ★★ |
| 10 | A07 | Role in a plaintext cookie | cookie → `/profile` | `A07_AUTH` | ★★ |
| 11 | A08 | Client-only upload filter | `POST /claims` | `A08_INTEGRITY` | ★★ |
| 12 | A09 | Web-readable logs, no alerting | `/logs/app.log` | `A09_LOGGING` | ★ |
| 13 | A10 | Stack trace + fail-open coupon | `/product/<id>`, `/basket` | `A10_EXCEPTION` | ★ |

**Intentional soft chain:** A02 (discovery) → A04 (backup contents) → A07a
(admin credentials). Everything else is independent.

---

## A01:2025 — Broken Access Control

### 1. IDOR on order detail ★
**Route:** `GET /order/<int:order_id>`
**Flag:** `GLIC{orders_are_not_yours_to_read}`

**Bug:** `order_detail()` fetches the order by ID and renders it without ever
comparing `order.user_id` to the session's `user_id`. Compare with `/orders`,
which filters correctly.

**Solution path:**
1. Log in as any user, place an order, land on `/order/<n>`.
2. Edit the number in the URL bar. Walk downward.
3. Order **#7** belongs to admin; the flag sits in its delivery notes.

**Facilitator note:** order 7 is pinned by explicit ID in `seed.py`, so it is
stable across reseeds. Players who only walk upward from a freshly placed
order (#41+) will miss it — nudge them downward.

**Teaching point:** ownership must be verified server-side on every request.
The object ID is not a secret.

### 2. Missing function-level access control ★★
**Route:** `GET /admin`
**Flag:** `GLIC{no_link_is_not_a_lock}`

**Bug:** `admin_panel()` is wrapped in `@login_required`, which checks
*authentication* only. There is no `role == 'admin'` check anywhere. The nav
link is hidden from normal users, and that is the only thing keeping them out.

**Solution path:**
1. Log in as any normal employee.
2. Type `/admin` into the URL bar.
3. Full user list, all orders, and the price editor. Flag in the header.

**Teaching point:** BFLA. Hiding a link from the menu is not access control —
the endpoint is what needs the check.

> **SSRF:** consolidated into A01 for 2025 but not browser-solvable at this
> difficulty. Cover it verbally in the debrief.

---

## A02:2025 — Security Misconfiguration ★
**Routes:** `GET /robots.txt`, `GET /static/backup/`
**Flag:** `GLIC{robots_txt_tells_on_you}`

**Bug:** `robots.txt` advertises `Disallow: /static/backup/`, and that path has
directory listing switched on with no access control of its own.

**Solution path:**
1. Open `/robots.txt`.
2. Browse to `/static/backup/` — full file index renders.
3. Open `README.txt`. Flag is in it.

**Facilitator note:** the explicit `/static/backup/` route in `app.py` takes
precedence over Flask's static file handler. Both files in the folder are real
static assets, so they are also directly fetchable if a player guesses names.

**Teaching point:** `robots.txt` is a polite request, not a control — and it
advertises exactly what you were trying to hide. Maps to WSTG-INFO-03.

---

## A03:2025 — Software Supply Chain Failures ★
**Route:** `GET /static/vendor/`
**Flag:** `GLIC{jquery_1_4_2_called_its_lawyer}`

**Bug:** every page loads `jquery-1.4.2.min.js` (Feb 2010) and `analytics.js`
from `static/vendor/` with no Subresource Integrity attribute. A publicly
served `package.json` lists pinned, years-stale dependencies. `analytics.js`
has a header comment showing its checksum verification was skipped.

**Solution path:**
1. View Source on any page → spot the two vendored `<script>` tags, note no
   `integrity=` attribute.
2. Open `/static/vendor/package.json` → stale versions, `lastReviewed: 2019`.
3. Open `/static/vendor/analytics.js` → flag in the header comment.

**Facilitator note:** the jQuery file is a stub, not the real library. Nothing
in the app depends on it working — it exists so the version string and the
missing SRI are visible in page source.

**Teaching point:** you ship your dependencies' bugs. Pin, scan, verify
integrity. Reference SolarWinds and xz Utils in the debrief.

---

## A04:2025 — Cryptographic Failures ★
**Route:** `GET /static/backup/users_2024.bak` (found via A02)
**Flag:** `GLIC{plaintext_backups_never_forget}`

**Bug, part 1:** a stale DB export with passwords in plaintext, plus three
accounts as unsalted MD5. The flag is a fake `backup-auditor` record.

**Bug, part 2:** the coupon token on `/basket` is base64-**encoded**, not
encrypted. Players decode it in the DevTools console with `atob()`.

**Solution path:**
1. From the A02 listing, open `users_2024.bak` in the browser or a text editor.
2. Read the flag off the `backup-auditor` row.
3. Note `admin@guardianmart.local` / `Welcome@123` — this feeds A07a directly.
4. Separately: apply any coupon on `/basket`, copy the `coupon_token`, run
   `atob('...')` in the console → `FESTIVE20:20`.

**Teaching point:** encoding is not encryption. Hash *and* salt. Backups
inherit the sensitivity of the data they came from.

---

## A05:2025 — Injection

### 6. SQL injection on login ★★
**Route:** `POST /login`
**Flag:** `GLIC{or_1_equals_1_forever}`

**Bug:** `db.raw_login_lookup()` builds the query with an f-string:
`SELECT * FROM users WHERE email='{email}' AND password='{password}'`

**Solution path:**
1. Go to `/login`.
2. Email: `' OR '1'='1' --`   Password: anything.
3. The tautology returns the first row, which is admin (id 1, seeded first).
   Flag appears in the welcome banner and you are signed in as admin.

**Other payloads that work:** `admin@guardianmart.local' --`,
`' OR 1=1 LIMIT 1 --`.

**Facilitator note:** the flag fires when the returned row's stored password
differs from what was submitted — a clean signal the WHERE clause was
manipulated rather than satisfied honestly. An honest login never flags.

**Teaching point:** parameterised queries, always. Input validation alone does
not fix this.

### 7. Stored XSS on support tickets ★★
**Routes:** `POST /support` (injection) → `GET /support/admin` (render)
**Flag:** `GLIC{script_tags_in_the_wild}`

**Bug:** `support_admin.html` renders the ticket body with `{{ t.message|safe }}`,
disabling Jinja autoescaping. `/support` itself escapes correctly — the
submitter never sees their own payload fire.

**Solution path:**
1. Log in, go to `/support`, submit `<script>alert(1)</script>` as the message.
2. Become admin (via challenge 6, 9 or 10) and open `/support/admin`.
3. The alert fires; the flag panel becomes visible.

**Facilitator note:** `static/js/app.js` wraps `window.alert` and reveals a
flag box the server already rendered hidden. It only *observes* that a payload
ran — it does not execute anything itself. This is the simulation boundary.

**Teaching point:** encode on output. Stored XSS hits the *staff member reading
the ticket*, not the attacker. That is what makes it worse than reflected.

---

## A06:2025 — Insecure Design ★★
**Route:** `POST /checkout`
**Flag:** `GLIC{price_tags_are_a_suggestion}`

**Bug:** `/basket` carries `<input type="hidden" name="unit_price">` and
`name="qty"` per line, and `checkout()` trusts both to compute the total. No
re-pricing against the `products` table, no lower bound on quantity.

**Solution path — either works:**
- **Price:** DevTools → Elements → find the hidden `unit_price` input → edit to
  `0` or `1` → Place order.
- **Quantity:** set a line quantity to `-5` → negative line total.

The flag shows on the confirmation page whenever the total is ≤ 0.

**Teaching point:** this is a *design* bug, not a coding bug. No input filter
fixes it — price must not round-trip through the client at all. The flow has to
be redesigned. This is the one that lands hardest with Finance and Operations.

---

## A07:2025 — Authentication Failures

Both paths share the flag `GLIC{admin_welcome123_and_a_cookie}`.

### 9. Default credentials ★★
**Route:** `POST /login`

**Bug:** `admin@guardianmart.local` / `Welcome@123` — a weak default, recovered
from the A04 backup. No rate limiting, no lockout, no MFA. Brute force is
completely unthrottled and generates no alert (see A09).

**Solution path:** read the `.bak` from A04 → log in as admin → `/profile`
shows the flag.

### 10. Role in a plaintext cookie ★★
**Route:** cookie → `GET /profile`

**Bug:** the session cookie is not Flask's signed session. It is literally
`gm_session=user_id:2|role:user|dept:finance`, and every route reads `role`
straight off it without checking the database.

**Solution path:**
1. Log in as any normal employee.
2. DevTools → Application → Cookies → `gm_session`.
3. Change `role:user` to `role:admin`. Refresh.
4. `/profile` shows the flag, the admin nav links appear, and
   `/support/admin` opens.

**Facilitator note:** department is slugified into the cookie (`it-security`)
so the value never contains a space and the browser never quotes it — keeps
the cookie readable and hand-editable in DevTools.

**Teaching point:** sessions must be signed and validated server-side. Never
trust client state for authorisation. Enforce lockout and MFA.

---

## A08:2025 — Software or Data Integrity Failures ★★
**Route:** `POST /claims`
**Flag:** `GLIC{client_side_checks_are_theater}`

**Bug:** file type is validated **only** in the browser — `accept=".pdf"` plus
`validateClaimUpload()` in `static/js/app.js`. The server saves whatever
arrives and serves it back from `/uploads/<filename>` with a guessed content
type, so an uploaded `.html` renders as HTML.

**Solution path:**
1. Create a text file `evil.html` containing `<h1>hello</h1>`.
2. `/claims` → DevTools → Elements → delete the `accept=".pdf"` attribute
   (or the `onsubmit` handler, or just disable JavaScript).
3. Upload it. Flag appears immediately.
4. Click it in the claims list — it renders as a web page, not a download.

**Facilitator note:** filenames are passed through `os.path.basename()` before
saving. That is a path-traversal guard, deliberately kept — it is not part of
the lesson, and this app is LAN-accessible on event day. Verified: uploading
`../../etc/passwd` lands in `uploads/`, not on the filesystem root.

**Teaching point:** client-side validation is UX, not security. Validate type,
size and extension server-side; serve uploads from a separate origin.

---

## A09:2025 — Security Logging and Alerting Failures ★
**Route:** `GET /logs/app.log`
**Flag:** `GLIC{your_password_is_in_the_logs}`

**Bug:** the app logs every login attempt verbatim — including plaintext
passwords and full session cookie values — and the log file is served over
HTTP. Separately, 100 failed logins produce **no alert whatsoever**: the A07
brute force is entirely silent.

**Solution path:**
1. Browse to `/logs/app.log`.
2. Flag is in the banner at the top.
3. Read further down for other players' passwords and live session cookies —
   paste one into `gm_session` and you are them.

**Facilitator note:** the log grows as players use the app, so this gets more
interesting over the session. It starts empty on a fresh clone, so run a
couple of logins before demoing it. `logs/*.log` is gitignored.

**Teaching point:** logs are sensitive assets in their own right. And logging
without *alerting* is just archaeology — the 2025 rename to "Alerting" is the
whole point. Make that explicit.

---

## A10:2025 — Mishandling of Exceptional Conditions ★
**Routes:** `GET /product/<id>`, `POST /basket` (coupon field)
**Flag:** `GLIC{fail_open_fail_everyone}`

### Part 1 — verbose failure (demo only, no flag)
**Bug:** `product_detail()` casts the URL segment with a bare `int()`, and the
app runs `debug=True`.

**Solution path:** open `/product/abc` → full Werkzeug interactive debugger,
exposing absolute file paths, the source line, and the traceback.

**Verified:** leaks `guardianmart/app.py`, the `int(product_id)` source line,
and the `ValueError`.

### Part 2 — fail open (this is the flag)
**Bug:** `validate_coupon()` wraps its decode in `try/except Exception` and, on
*any* failure, returns a **100% discount** instead of rejecting the code.

**Solution path:**
1. Add anything to the basket.
2. Enter `%%%` (or `!!!`, or any junk that is not valid base64) as the coupon.
3. "100% off" is applied and the flag appears.

**Teaching point:** fail *closed*, never open. Error handling is a security
control. And stack traces are reconnaissance gifts — `debug=True` never goes
to production.

---

## Facilitator checklist

**Before the session**
- [ ] `python seed.py` on a clean checkout — confirms order #7 is pinned to admin
- [ ] Run two or three logins so `/logs/app.log` has content for A09
- [ ] Confirm the host is on the isolated network only
- [ ] Have a plain `evil.html` file ready to hand out for A08

**Demo order for a non-technical audience** (biggest reaction first)
1. **A05a SQLi** — type one line into a login box, become admin
2. **A06 price tampering** — edit a number in DevTools, order for ₹0
3. **A10 fail-open coupon** — type `%%%`, get everything free

**Reset between groups**
```
python seed.py          # wipes orders, users, tickets, claims records
rm -f logs/app.log      # clears leaked credentials
rm -f uploads/*         # clears uploaded files (keep .gitkeep)
```
Restart `app.py` afterwards — baskets and applied coupons are in memory and
clear on restart.

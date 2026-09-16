"""
GuardianMart — flag registry.

Week 2's scoreboard platform imports (or receives) this dict directly.
Nothing in this week's app depends on that platform existing — flags are
simply returned as plain text, in-page, when a challenge is solved.

One entry per distinct flag. A01, A04, A05 and A07 each cover two exploit
paths under a single OWASP category — see CHALLENGES.md for which route
triggers which key.
"""

FLAGS = {
    "A01_IDOR": "GLIC{orders_are_not_yours_to_read}",
    "A01_BFLA": "GLIC{no_link_is_not_a_lock}",
    "A02_MISCONFIG": "GLIC{robots_txt_tells_on_you}",
    "A03_SUPPLY_CHAIN": "GLIC{jquery_1_4_2_called_its_lawyer}",
    "A04_CRYPTO": "GLIC{plaintext_backups_never_forget}",
    "A05_SQLI": "GLIC{or_1_equals_1_forever}",
    "A05_XSS": "GLIC{script_tags_in_the_wild}",
    "A06_INSECURE_DESIGN": "GLIC{price_tags_are_a_suggestion}",
    "A07_AUTH": "GLIC{admin_welcome123_and_a_cookie}",
    "A08_INTEGRITY": "GLIC{client_side_checks_are_theater}",
    "A09_LOGGING": "GLIC{your_password_is_in_the_logs}",
    "A10_EXCEPTION": "GLIC{fail_open_fail_everyone}",
}

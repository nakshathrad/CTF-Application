GuardianMart — /static/backup
------------------------------
Temporary staging area for the Q1 database migration. This folder was
supposed to come down once the users_2024 export was verified against
the new environment — leaving it here (and leaving directory listing
switched on) is exactly the kind of thing that should have been caught
in a pre-launch config review.

If you're reading this from a browser instead of a code checkout, you've
just found the finding: robots.txt told you this path exists and asked
you not to look. It also has no access control of its own, which is the
real bug — "don't look here" is a request, not a control.

Flag: GLIC{robots_txt_tells_on_you}

— Ops. Cleanup ticket: OPS-4102. Do not deploy with this folder present.

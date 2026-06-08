"""
One-off repair: fix inflated home heatmap caused by copied articles.

BACKGROUND
----------
When a user adds a keyword that other users already track,
`copy_articles_from_shared_keyword` (app.py) copies their existing articles to
the new user. A bug omitted `created_at`, so every copied (historical) article
defaulted to `utcnow()` — i.e. "today". The home heatmap
(/api/home/map-timeline) groups by `created_at`, so all those copies piled onto
the current day and made the per-country numbers explode (e.g. 7600).

The forward fix (preserving created_at on copy) is already in app.py. This
script repairs the rows that were already mis-stamped BEFORE that fix.

HOW IT IDENTIFIES BAD ROWS
--------------------------
On a normal save, `created_at` and `fetched_at` are set in the same moment, so
they are within seconds of each other. On a buggy copy, `fetched_at` is the
ORIGINAL (old) ingest time while `created_at` is the copy day. So mis-stamped
copies are exactly the rows where `created_at` is significantly LATER than
`fetched_at`. We restore `created_at = fetched_at` for those rows, putting them
back on their real timeline.

USAGE
-----
Dry run (default — shows what WOULD change, writes nothing):
    python repair_copied_created_at.py

Apply the fix:
    python repair_copied_created_at.py --apply

Optional: change the tolerance (default 1 hour). Rows where
created_at - fetched_at exceeds this are considered mis-stamped copies:
    python repair_copied_created_at.py --apply --tolerance-minutes 60

Works on both local SQLite and production PostgreSQL — it uses the same
DATABASE_URL / engine as the app, so on Render just run it from the service
shell.
"""
import argparse
import sys
from datetime import timedelta

sys.stdout.reconfigure(encoding="utf-8")

from models import get_db, Article  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Repair mis-stamped created_at on copied articles.")
    parser.add_argument("--apply", action="store_true",
                        help="Actually write the changes. Without this flag it's a dry run.")
    parser.add_argument("--tolerance-minutes", type=int, default=60,
                        help="created_at later than fetched_at by more than this many minutes "
                             "is treated as a mis-stamped copy. Default: 60.")
    parser.add_argument("--batch", type=int, default=500,
                        help="Commit every N updates when applying. Default: 500.")
    args = parser.parse_args()

    tolerance = timedelta(minutes=args.tolerance_minutes)

    db = get_db()
    try:
        # Candidate rows: created_at is AFTER fetched_at (works on SQLite + Postgres).
        candidates = db.query(Article).filter(
            Article.fetched_at.isnot(None),
            Article.created_at.isnot(None),
            Article.created_at > Article.fetched_at,
        ).all()

        bad = [a for a in candidates if (a.created_at - a.fetched_at) > tolerance]

        print(f"Candidate rows (created_at > fetched_at): {len(candidates)}")
        print(f"Mis-stamped copies (delta > {args.tolerance_minutes} min): {len(bad)}")

        if not bad:
            print("Nothing to repair. ✅")
            return

        # Show a small before/after sample.
        print("\nSample (up to 8):")
        for a in bad[:8]:
            print(f"  id={a.id} user={a.user_id} country={a.country!r} "
                  f"created_at={a.created_at} -> fetched_at={a.fetched_at}")

        # Show how many bad rows currently land on each (created_at) day — the
        # buckets the heatmap is over-counting right now.
        from collections import Counter
        by_day = Counter(a.created_at.date().isoformat() for a in bad)
        print("\nBad rows currently bucketed by created_at day (top 10):")
        for day, cnt in sorted(by_day.items(), key=lambda x: -x[1])[:10]:
            print(f"  {day}: {cnt}")

        if not args.apply:
            print("\nDRY RUN — no changes written. Re-run with --apply to fix.")
            return

        print(f"\nApplying fix to {len(bad)} rows...")
        fixed = 0
        for a in bad:
            a.created_at = a.fetched_at
            fixed += 1
            if fixed % args.batch == 0:
                db.commit()
                print(f"  committed {fixed}/{len(bad)}")
        db.commit()
        print(f"✅ Repaired {fixed} rows. The heatmap should now reflect real dates.")
    except Exception as e:
        db.rollback()
        print(f"❌ Repair failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

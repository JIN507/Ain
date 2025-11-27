from collections import defaultdict
import json

from models import init_db, get_db, Country, Source


def main() -> None:
    """Export current countries & sources from ain_news.db as VERIFIED_FEEDS dict.

    Run this locally (NOT on Render):

        cd backend
        python export_feeds_from_db.py

    Then copy the printed dict and paste it into VERIFIED_FEEDS in seed_data.py.
    """
    # Ensure tables exist
    init_db()
    db = get_db()
    try:
        countries = db.query(Country).all()
        sources = db.query(Source).all()

        # Map country_id -> country_name (Arabic)
        country_names = {c.id: c.name_ar for c in countries}

        verified_feeds = defaultdict(list)

        for s in sources:
            country_name = country_names.get(s.country_id, s.country_name or "غير معروف")
            verified_feeds[country_name].append(
                {
                    "name": s.name,
                    "url": s.url,
                    # reliability not stored in DB; default to "high" for now
                    "reliability": "high",
                    "enabled": bool(s.enabled),
                }
            )

        print("VERIFIED_FEEDS = ")
        # json.dumps gives us nicely formatted UTF-8-safe output
        print(json.dumps(verified_feeds, ensure_ascii=False, indent=4))
    finally:
        db.close()


if __name__ == "__main__":
    main()

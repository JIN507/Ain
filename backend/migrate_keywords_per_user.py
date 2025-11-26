import sqlite3
import os

DB_PATH = "ain_news.db"


def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("1) Inspect existing keywords schema...")
    cur.execute("PRAGMA table_info(keywords)")
    cols = cur.fetchall()
    print("   Columns:")
    for c in cols:
        print("    ", c)

    print("\n2) Create new table keywords_new with per-user unique constraint...")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS keywords_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            text_ar VARCHAR(200) NOT NULL,
            text_en VARCHAR(200),
            text_fr VARCHAR(200),
            text_tr VARCHAR(200),
            text_ur VARCHAR(200),
            text_zh VARCHAR(200),
            text_ru VARCHAR(200),
            text_es VARCHAR(200),
            enabled BOOLEAN DEFAULT 1,
            created_at DATETIME,
            UNIQUE(user_id, text_ar)
        );
        """
    )

    print("3) Copy data from old keywords to keywords_new...")
    cur.execute(
        """
        INSERT INTO keywords_new (
            id, user_id, text_ar, text_en, text_fr, text_tr,
            text_ur, text_zh, text_ru, text_es, enabled, created_at
        )
        SELECT
            id, user_id, text_ar, text_en, text_fr, text_tr,
            text_ur, text_zh, text_ru, text_es, enabled, created_at
        FROM keywords;
        """
    )

    print("4) Drop old keywords table...")
    cur.execute("DROP TABLE keywords;")

    print("5) Rename keywords_new -> keywords...")
    cur.execute("ALTER TABLE keywords_new RENAME TO keywords;")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete. 'keywords' is now unique per (user_id, text_ar).")


if __name__ == "__main__":
    main()

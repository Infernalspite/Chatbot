"""
Run this ONCE to add recommendation columns to the products table
and create the product_embeddings table.
Works with both MySQL and PostgreSQL.

Usage:  python migrate_recommendations.py
"""

from database import DB_connection, DB_TYPE


def run_migration():
    conn = DB_connection()
    try:
        with conn.cursor() as cur:
            if DB_TYPE == "mysql":
                cur.execute("""
                    ALTER TABLE products
                        ADD COLUMN IF NOT EXISTS category     VARCHAR(120) NULL,
                        ADD COLUMN IF NOT EXISTS sub_category VARCHAR(120) NULL,
                        ADD COLUMN IF NOT EXISTS description  TEXT         NULL,
                        ADD COLUMN IF NOT EXISTS tags         TEXT         NULL
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS product_embeddings (
                        product_id INT         NOT NULL PRIMARY KEY,
                        model      VARCHAR(80) NOT NULL DEFAULT 'voyage-3',
                        embedding  LONGTEXT    NOT NULL,
                        updated_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                    )
                """)
            else:
                for col, coltype in [
                    ("category",     "VARCHAR(120)"),
                    ("sub_category", "VARCHAR(120)"),
                    ("description",  "TEXT"),
                    ("tags",         "TEXT"),
                ]:
                    cur.execute(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {col} {coltype}")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS product_embeddings (
                        product_id INTEGER     NOT NULL PRIMARY KEY
                                   REFERENCES products(id) ON DELETE CASCADE,
                        model      VARCHAR(80) NOT NULL DEFAULT 'voyage-3',
                        embedding  TEXT        NOT NULL,
                        updated_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)

        conn.commit()
        print("Migration complete — recommendation columns & table ready.")
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()

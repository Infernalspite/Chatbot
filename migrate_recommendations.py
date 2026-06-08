"""
STEP 1 — Run this ONCE to add recommendation columns to your existing DB.
Usage:  python migrate_recommendations.py
"""

import pymysql
from database import DB_connection   # re-uses your existing connector


def run_migration():
    conn = DB_connection()
    try:
        with conn.cursor() as cur:

            # ── 1. Add optional metadata columns to products ──────────────
            # (safe: ALTER IGNORE silently skips if column already exists)
            alter_stmts = [
                """
                ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS category     VARCHAR(120)  NULL,
                    ADD COLUMN IF NOT EXISTS sub_category VARCHAR(120)  NULL,
                    ADD COLUMN IF NOT EXISTS description  TEXT          NULL,
                    ADD COLUMN IF NOT EXISTS tags         JSON          NULL
                """,
            ]
            for stmt in alter_stmts:
                cur.execute(stmt)

            # ── 2. Create dedicated embeddings table ──────────────────────
            # Stores the Anthropic voyage-3 embedding (1024 dims) as JSON.
            # We keep embeddings separate so the products table stays slim.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS product_embeddings (
                    product_id   INT           NOT NULL,
                    model        VARCHAR(80)   NOT NULL DEFAULT 'voyage-3',
                    embedding    LONGTEXT      NOT NULL,   -- JSON float array
                    updated_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                              ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (product_id),
                    CONSTRAINT fk_pe_product
                        FOREIGN KEY (product_id) REFERENCES products(id)
                        ON DELETE CASCADE
                )
            """)

            conn.commit()
            print("✅  Migration complete — columns & product_embeddings table ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()

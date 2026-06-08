"""
Run this ONCE to add recommendation columns to the products table
and create the product_embeddings table.

Usage:  python3.11 migrate_recommendations.py
"""

from database import DB_connection


def run_migration():
    conn = DB_connection()
    try:
        with conn.cursor() as cur:

            # Add optional metadata columns to products if they don't exist
            for col, coltype in [
                ("category",     "VARCHAR(120)"),
                ("sub_category", "VARCHAR(120)"),
                ("description",  "TEXT"),
                ("tags",         "TEXT"),
            ]:
                cur.execute(f"""
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS {col} {coltype}
                """)

            # Create product_embeddings table
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
        print("Migration complete — columns & product_embeddings table ready.")
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()

"""
setup_db.py — Create PostgreSQL schema and seed data from the MySQL dump.
Run once:  python3.11 setup_db.py
"""

import json
from database import DB_connection
from auth import hash_password


def setup():
    conn = DB_connection()
    try:
        with conn.cursor() as cur:

            # ── 1. Create tables ─────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id       SERIAL PRIMARY KEY,
                    name     VARCHAR(100) NOT NULL,
                    email    VARCHAR(150) NOT NULL UNIQUE,
                    role     VARCHAR(20)  DEFAULT 'user',
                    password VARCHAR(255)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id          SERIAL PRIMARY KEY,
                    name        VARCHAR(120) NOT NULL,
                    price       DECIMAL(8,2) NOT NULL,
                    stock       INTEGER      DEFAULT 0,
                    image_url   VARCHAR(500),
                    category    VARCHAR(120),
                    sub_category VARCHAR(120),
                    description TEXT,
                    tags        TEXT
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id         SERIAL PRIMARY KEY,
                    order_id   INTEGER REFERENCES orders(id),
                    product_id INTEGER REFERENCES products(id),
                    quantity   INTEGER DEFAULT 1
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS product_embeddings (
                    product_id INTEGER     NOT NULL PRIMARY KEY
                               REFERENCES products(id) ON DELETE CASCADE,
                    model      VARCHAR(80) NOT NULL DEFAULT 'voyage-3',
                    embedding  TEXT        NOT NULL,
                    updated_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ── 2. Seed users (only if table is empty) ───────────────────────
            cur.execute("SELECT COUNT(*) AS cnt FROM users")
            if cur.fetchone()["cnt"] == 0:
                users = [
                    (1,  "Arjun Mehta", "arjun@example.com",         "user",    "1234"),
                    (2,  "Sara Lopes",  "sara@example.com",          "manager", "1234"),
                    (3,  "James Okafor","james@example.com",          "user",    "1234"),
                    (4,  "Gokul",       "togokulj@gmail.com",        "admin",   "1234"),
                    (8,  "John",        "john@example.com",           "admin",   "1234"),
                    (9,  "Cassie",      "cassie@example.com",         "manager", "1234"),
                    (10, "Maddie",      "maddie@example.com",         "manager", "1234"),
                    (11, "Test User",   "test_b9020b@example.com",    "user",    "my_secure_password"),
                    (12, "deez",        "deez@gmail.com",             "user",    "deez"),
                ]
                for uid, name, email, role, pwd in users:
                    cur.execute("""
                        INSERT INTO users (name, email, role, password)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (email) DO NOTHING
                    """, (name, email, role, hash_password(pwd)))
                print(f"  Seeded {len(users)} users.")
            else:
                print("  Users already seeded — skipping.")

            # ── 3. Seed products (only if table is empty) ────────────────────
            cur.execute("SELECT COUNT(*) AS cnt FROM products")
            if cur.fetchone()["cnt"] == 0:
                products = [
                    (1,  "Wireless Mouse",              29.99, 100, "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80"),
                    (2,  "Mechanical Keyboard",         89.99,  50, "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80"),
                    (3,  "USB-C Hub",                   49.99,  80, "https://images.unsplash.com/photo-1468495244123-6c6c332eeece?w=600&auto=format&fit=crop&q=80"),
                    (4,  "Webcam HD",                   79.99,  30, "https://images.unsplash.com/photo-1603481588273-2f908a9a7a1b?w=600&auto=format&fit=crop&q=80"),
                    (5,  "watch",                       33.00,   2, "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80"),
                    (7,  "GEFORCE RTX 5010",            95.00,   2, "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=600&auto=format&fit=crop&q=80"),
                    (9,  "Noise-Canceling Headphones", 149.99,  45, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80"),
                    (10, "Wireless Charging Pad",       19.99, 120, "https://images.unsplash.com/photo-1622445262465-2481c4574875?w=600&auto=format&fit=crop&q=80"),
                    (11, "Portable Bluetooth Speaker",  39.99,  85, "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&auto=format&fit=crop&q=80"),
                    (12, "Smart Fitness Band",          59.99,  60, "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=600&auto=format&fit=crop&q=80"),
                    (13, "Leather Desk Organizer",      34.50,  25, "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"),
                    (14, "Ergonomic Office Chair",     249.00,  15, "https://images.unsplash.com/photo-1505797149-43b0069ec26b?w=600&auto=format&fit=crop&q=80"),
                    (15, "Dimmable Desk Lamp",          29.99,  40, "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop&q=80"),
                    (16, "Dual Monitor Arm",            89.99,  18, "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?w=600&auto=format&fit=crop&q=80"),
                    (17, "Minimalist Wallet",           24.99, 150, "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80"),
                    (18, "Travel Backpack",             69.99,  55, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80"),
                    (19, "Polarized Sunglasses",        45.00,  70, "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&auto=format&fit=crop&q=80"),
                    (20, "Insulated Water Bottle",      22.50, 200, "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80"),
                    (21, "Cork Yoga Mat",               49.99,  30, "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600&auto=format&fit=crop&q=80"),
                    (22, "Adjustable Dumbbell Set",    189.99,  12, "https://images.unsplash.com/photo-1638536532686-d610adfc8e5c?w=600&auto=format&fit=crop&q=80"),
                    (23, "High-Density Foam Roller",    19.99,  50, "https://images.unsplash.com/photo-1600881333168-2ef49b341f30?w=600&auto=format&fit=crop&q=80"),
                    (24, "Resistance Bands Kit",        15.99, 100, "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=600&auto=format&fit=crop&q=80"),
                    (25, "French Press Coffee Maker",   27.99,  40, "https://images.unsplash.com/photo-1577968897866-be8441db7a67?w=600&auto=format&fit=crop&q=80"),
                    (26, "Electric Milk Frother",       12.99,  80, "https://images.unsplash.com/photo-1578593139857-e6f7ec62f1c8?w=600&auto=format&fit=crop&q=80"),
                    (27, "Damascus Steel Chef Knife",   89.00,  20, "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80"),
                    (28, "Ceramic Coffee Mug",          14.99, 110, "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80"),
                    (29, "Double-Walled Glass Cups",    18.99,  65, "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80"),
                    (30, "Vertical Ergonomic Mouse",    39.99,  45, "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80"),
                    (31, "4K Computer Monitor",        329.99,  10, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80"),
                    (32, "Laptop Stand Holder",         24.99,  75, "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?w=600&auto=format&fit=crop&q=80"),
                    (33, "Felt Desk Mat",               19.50,  90, "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"),
                    (34, "Ambient LED Light Strip",     15.99, 130, "https://images.unsplash.com/photo-1565814636199-ae8133055c1c?w=600&auto=format&fit=crop&q=80"),
                    (35, "Smart Home Assistant Plug",   11.99, 160, "https://images.unsplash.com/photo-1558002038-1055907df827?w=600&auto=format&fit=crop&q=80"),
                    (36, "Aromatherapy Diffuser",       29.99,  42, "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&auto=format&fit=crop&q=80"),
                    (37, "Handmade Scented Candle",     16.50,  85, "https://images.unsplash.com/photo-1603006905003-be475563bc59?w=600&auto=format&fit=crop&q=80"),
                    (38, "Indoor Bonsai Tree",          45.00,   8, "https://images.unsplash.com/photo-1613143341151-576f30d075eb?w=600&auto=format&fit=crop&q=80"),
                    (39, "Self-Watering Planter",       18.00,  50, "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=600&auto=format&fit=crop&q=80"),
                    (40, "Canvas Tote Bag",             12.00, 200, "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80"),
                    (41, "Leather Passport Holder",     28.00,  35, "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600&auto=format&fit=crop&q=80"),
                    (42, "Stainless Steel Straws",       7.99, 300, "https://images.unsplash.com/photo-1592861956120-e524fc739696?w=600&auto=format&fit=crop&q=80"),
                    (43, "Cast Iron Skillet",           34.99,  28, "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=600&auto=format&fit=crop&q=80"),
                    (44, "Bamboo Cutting Board",        21.99,  60, "https://images.unsplash.com/photo-1574634534894-89d7576c8259?w=600&auto=format&fit=crop&q=80"),
                    (45, "Herb Garden Starter Kit",     24.99,  45, "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=600&auto=format&fit=crop&q=80"),
                    (46, "Automatic Soap Dispenser",    19.99,  70, "https://images.unsplash.com/photo-1608248597279-f99d160bfcbc?w=600&auto=format&fit=crop&q=80"),
                    (47, "Memory Foam Pillow",          39.99,  30, "https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=600&auto=format&fit=crop&q=80"),
                    (48, "Soft Cotton Bath Towel",      14.50, 120, "https://images.unsplash.com/photo-1563453392212-326f5e854473?w=600&auto=format&fit=crop&q=80"),
                    (49, "Compact Travel Umbrella",     15.99,  90, "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=600&auto=format&fit=crop&q=80"),
                    (50, "Rechargeable Hand Warmer",    18.50,  65, "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&auto=format&fit=crop&q=80"),
                    (51, "Running Waist Pack",          12.99, 110, "https://images.unsplash.com/photo-1530143311094-34d807799e8f?w=600&auto=format&fit=crop&q=80"),
                    (52, "Waterproof Phone Pouch",       9.99, 150, "https://images.unsplash.com/photo-1523206489230-c012c64b2b48?w=600&auto=format&fit=crop&q=80"),
                    (53, "Reusable Food Storage Bags",  16.99,  80, "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=600&auto=format&fit=crop&q=80"),
                    (54, "Beeswax Food Wraps",          13.50,  95, "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600&auto=format&fit=crop&q=80"),
                    (55, "Desk Fountain Pen",           26.00,  40, "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80"),
                    (56, "Hardcover Bullet Journal",    18.99,  85, "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&auto=format&fit=crop&q=80"),
                    (57, "Gel Ink Pens Set",             8.50, 140, "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80"),
                    (58, "Adjustable Laptop Table",     39.99,  35, "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"),
                ]
                for row in products:
                    cur.execute("""
                        INSERT INTO products (name, price, stock, image_url)
                        VALUES (%s, %s, %s, %s)
                    """, (row[1], row[2], row[3], row[4]))
                print(f"  Seeded {len(products)} products.")
            else:
                print("  Products already seeded — skipping.")

            # ── 4. Seed orders (only if table is empty) ──────────────────────
            cur.execute("SELECT COUNT(*) AS cnt FROM orders")
            if cur.fetchone()["cnt"] == 0:
                # Get actual user IDs (seeded without fixed IDs in Postgres SERIAL)
                cur.execute("SELECT id FROM users ORDER BY id LIMIT 1")
                first_user = cur.fetchone()
                if first_user:
                    uid = first_user["id"]
                    cur.execute("INSERT INTO orders (user_id) VALUES (%s)", (uid,))
                    cur.execute("INSERT INTO orders (user_id) VALUES (%s)", (uid,))
                print("  Seeded sample orders.")
            else:
                print("  Orders already seeded — skipping.")

        conn.commit()
        print("\nDatabase setup complete.")

    except Exception as e:
        conn.rollback()
        print(f"Error during setup: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    setup()

"""
setup_db.py — Create schema and seed all data.
Works with both MySQL and PostgreSQL.

Run once:  python setup_db.py   (or python3.11 setup_db.py on Replit)
"""

from database import DB_connection, DB_TYPE
from auth import hash_password


def setup():
    conn = DB_connection()
    try:
        with conn.cursor() as cur:

            if DB_TYPE == "mysql":
                _create_tables_mysql(cur)
            else:
                _create_tables_postgres(cur)

            _seed_users(cur)
            _seed_products(cur)

        conn.commit()
        print("\nDatabase setup complete.")
    except Exception as e:
        conn.rollback()
        print(f"Error during setup: {e}")
        raise
    finally:
        conn.close()


# ── MySQL schema ───────────────────────────────────────────────────────────────
def _create_tables_mysql(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INT AUTO_INCREMENT PRIMARY KEY,
            name     VARCHAR(100) NOT NULL,
            email    VARCHAR(150) NOT NULL UNIQUE,
            role     VARCHAR(20)  DEFAULT 'user',
            password VARCHAR(255)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(120) NOT NULL,
            price        DECIMAL(8,2) NOT NULL,
            stock        INT          DEFAULT 0,
            image_url    VARCHAR(500),
            category     VARCHAR(120),
            sub_category VARCHAR(120),
            description  TEXT,
            tags         TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            order_id   INT,
            product_id INT,
            quantity   INT DEFAULT 1,
            FOREIGN KEY (order_id)   REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_embeddings (
            product_id INT          NOT NULL PRIMARY KEY,
            model      VARCHAR(80)  NOT NULL DEFAULT 'voyage-3',
            embedding  LONGTEXT     NOT NULL,
            updated_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)
    print("  MySQL tables ready.")


# ── PostgreSQL schema ──────────────────────────────────────────────────────────
def _create_tables_postgres(cur):
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
            id           SERIAL PRIMARY KEY,
            name         VARCHAR(120) NOT NULL,
            price        DECIMAL(8,2) NOT NULL,
            stock        INTEGER      DEFAULT 0,
            image_url    VARCHAR(500),
            category     VARCHAR(120),
            sub_category VARCHAR(120),
            description  TEXT,
            tags         TEXT
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
    print("  PostgreSQL tables ready.")


# ── Seed users ─────────────────────────────────────────────────────────────────
def _seed_users(cur):
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    if cur.fetchone()["cnt"] > 0:
        print("  Users already seeded — skipping.")
        return

    users = [
        ("Arjun Mehta",  "arjun@example.com",       "user",    "1234"),
        ("Sara Lopes",   "sara@example.com",         "manager", "1234"),
        ("James Okafor", "james@example.com",        "user",    "1234"),
        ("Gokul",        "togokulj@gmail.com",       "admin",   "1234"),
        ("John",         "john@example.com",         "admin",   "1234"),
        ("Cassie",       "cassie@example.com",       "manager", "1234"),
        ("Maddie",       "maddie@example.com",       "manager", "1234"),
        ("Test User",    "test_b9020b@example.com",  "user",    "my_secure_password"),
        ("deez",         "deez@gmail.com",           "user",    "deez"),
    ]
    for name, email, role, pwd in users:
        cur.execute("""
            INSERT INTO users (name, email, role, password)
            VALUES (%s, %s, %s, %s)
        """, (name, email, role, hash_password(pwd)))
    print(f"  Seeded {len(users)} users.")


# ── Seed products ──────────────────────────────────────────────────────────────
def _seed_products(cur):
    cur.execute("SELECT COUNT(*) AS cnt FROM products")
    if cur.fetchone()["cnt"] > 0:
        print("  Products already seeded — skipping.")
        return

    products = [
        ("Wireless Mouse",             29.99, 100, "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80"),
        ("Mechanical Keyboard",        89.99,  50, "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80"),
        ("USB-C Hub",                  49.99,  80, "https://images.unsplash.com/photo-1468495244123-6c6c332eeece?w=600&auto=format&fit=crop&q=80"),
        ("Webcam HD",                  79.99,  30, "https://images.unsplash.com/photo-1603481588273-2f908a9a7a1b?w=600&auto=format&fit=crop&q=80"),
        ("watch",                      33.00,   2, "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80"),
        ("GEFORCE RTX 5010",           95.00,   2, "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=600&auto=format&fit=crop&q=80"),
        ("Noise-Canceling Headphones",149.99,  45, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80"),
        ("Wireless Charging Pad",      19.99, 120, "https://images.unsplash.com/photo-1622445262465-2481c4574875?w=600&auto=format&fit=crop&q=80"),
        ("Portable Bluetooth Speaker", 39.99,  85, "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&auto=format&fit=crop&q=80"),
        ("Smart Fitness Band",         59.99,  60, "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=600&auto=format&fit=crop&q=80"),
        ("Leather Desk Organizer",     34.50,  25, "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"),
        ("Ergonomic Office Chair",    249.00,  15, "https://images.unsplash.com/photo-1505797149-43b0069ec26b?w=600&auto=format&fit=crop&q=80"),
        ("Dimmable Desk Lamp",         29.99,  40, "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop&q=80"),
        ("Dual Monitor Arm",           89.99,  18, "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?w=600&auto=format&fit=crop&q=80"),
        ("Minimalist Wallet",          24.99, 150, "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80"),
        ("Travel Backpack",            69.99,  55, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80"),
        ("Polarized Sunglasses",       45.00,  70, "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&auto=format&fit=crop&q=80"),
        ("Insulated Water Bottle",     22.50, 200, "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80"),
        ("Cork Yoga Mat",              49.99,  30, "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600&auto=format&fit=crop&q=80"),
        ("Adjustable Dumbbell Set",   189.99,  12, "https://images.unsplash.com/photo-1638536532686-d610adfc8e5c?w=600&auto=format&fit=crop&q=80"),
        ("High-Density Foam Roller",   19.99,  50, "https://images.unsplash.com/photo-1600881333168-2ef49b341f30?w=600&auto=format&fit=crop&q=80"),
        ("Resistance Bands Kit",       15.99, 100, "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=600&auto=format&fit=crop&q=80"),
        ("French Press Coffee Maker",  27.99,  40, "https://images.unsplash.com/photo-1577968897866-be8441db7a67?w=600&auto=format&fit=crop&q=80"),
        ("Electric Milk Frother",      12.99,  80, "https://images.unsplash.com/photo-1578593139857-e6f7ec62f1c8?w=600&auto=format&fit=crop&q=80"),
        ("Damascus Steel Chef Knife",  89.00,  20, "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80"),
        ("Ceramic Coffee Mug",         14.99, 110, "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80"),
        ("Double-Walled Glass Cups",   18.99,  65, "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80"),
        ("Vertical Ergonomic Mouse",   39.99,  45, "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80"),
        ("4K Computer Monitor",       329.99,  10, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80"),
        ("Laptop Stand Holder",        24.99,  75, "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?w=600&auto=format&fit=crop&q=80"),
        ("Felt Desk Mat",              19.50,  90, "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"),
        ("Ambient LED Light Strip",    15.99, 130, "https://images.unsplash.com/photo-1565814636199-ae8133055c1c?w=600&auto=format&fit=crop&q=80"),
        ("Smart Home Assistant Plug",  11.99, 160, "https://images.unsplash.com/photo-1558002038-1055907df827?w=600&auto=format&fit=crop&q=80"),
        ("Aromatherapy Diffuser",      29.99,  42, "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&auto=format&fit=crop&q=80"),
        ("Handmade Scented Candle",    16.50,  85, "https://images.unsplash.com/photo-1603006905003-be475563bc59?w=600&auto=format&fit=crop&q=80"),
        ("Indoor Bonsai Tree",         45.00,   8, "https://images.unsplash.com/photo-1613143341151-576f30d075eb?w=600&auto=format&fit=crop&q=80"),
        ("Self-Watering Planter",      18.00,  50, "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=600&auto=format&fit=crop&q=80"),
        ("Canvas Tote Bag",            12.00, 200, "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80"),
        ("Leather Passport Holder",    28.00,  35, "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600&auto=format&fit=crop&q=80"),
        ("Stainless Steel Straws",      7.99, 300, "https://images.unsplash.com/photo-1592861956120-e524fc739696?w=600&auto=format&fit=crop&q=80"),
        ("Cast Iron Skillet",          34.99,  28, "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=600&auto=format&fit=crop&q=80"),
        ("Bamboo Cutting Board",       21.99,  60, "https://images.unsplash.com/photo-1574634534894-89d7576c8259?w=600&auto=format&fit=crop&q=80"),
        ("Herb Garden Starter Kit",    24.99,  45, "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=600&auto=format&fit=crop&q=80"),
        ("Automatic Soap Dispenser",   19.99,  70, "https://images.unsplash.com/photo-1608248597279-f99d160bfcbc?w=600&auto=format&fit=crop&q=80"),
        ("Memory Foam Pillow",         39.99,  30, "https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=600&auto=format&fit=crop&q=80"),
        ("Soft Cotton Bath Towel",     14.50, 120, "https://images.unsplash.com/photo-1563453392212-326f5e854473?w=600&auto=format&fit=crop&q=80"),
        ("Compact Travel Umbrella",    15.99,  90, "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=600&auto=format&fit=crop&q=80"),
        ("Rechargeable Hand Warmer",   18.50,  65, "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&auto=format&fit=crop&q=80"),
        ("Running Waist Pack",         12.99, 110, "https://images.unsplash.com/photo-1530143311094-34d807799e8f?w=600&auto=format&fit=crop&q=80"),
        ("Waterproof Phone Pouch",      9.99, 150, "https://images.unsplash.com/photo-1523206489230-c012c64b2b48?w=600&auto=format&fit=crop&q=80"),
        ("Reusable Food Storage Bags", 16.99,  80, "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=600&auto=format&fit=crop&q=80"),
        ("Beeswax Food Wraps",         13.50,  95, "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600&auto=format&fit=crop&q=80"),
        ("Desk Fountain Pen",          26.00,  40, "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80"),
        ("Hardcover Bullet Journal",   18.99,  85, "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&auto=format&fit=crop&q=80"),
        ("Gel Ink Pens Set",            8.50, 140, "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80"),
        ("Adjustable Laptop Table",    39.99,  35, "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"),
    ]
    for name, price, stock, img in products:
        cur.execute("""
            INSERT INTO products (name, price, stock, image_url)
            VALUES (%s, %s, %s, %s)
        """, (name, price, stock, img))
    print(f"  Seeded {len(products)} products.")


if __name__ == "__main__":
    setup()

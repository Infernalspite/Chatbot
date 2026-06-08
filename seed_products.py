import pymysql
from decimal import Decimal

# Define 50 high-quality products
products_seed = [
    {
        "name": "Noise-Canceling Headphones",
        "price": 149.99,
        "stock": 45,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Wireless Charging Pad",
        "price": 19.99,
        "stock": 120,
        "image_url": "https://images.unsplash.com/photo-1622445262465-2481c4574875?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Portable Bluetooth Speaker",
        "price": 39.99,
        "stock": 85,
        "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Smart Fitness Band",
        "price": 59.99,
        "stock": 60,
        "image_url": "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Leather Desk Organizer",
        "price": 34.50,
        "stock": 25,
        "image_url": "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Ergonomic Office Chair",
        "price": 249.00,
        "stock": 15,
        "image_url": "https://images.unsplash.com/photo-1505797149-43b0069ec26b?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Dimmable Desk Lamp",
        "price": 29.99,
        "stock": 40,
        "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Dual Monitor Arm",
        "price": 89.99,
        "stock": 18,
        "image_url": "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Minimalist Wallet",
        "price": 24.99,
        "stock": 150,
        "image_url": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Travel Backpack",
        "price": 69.99,
        "stock": 55,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Polarized Sunglasses",
        "price": 45.00,
        "stock": 70,
        "image_url": "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Insulated Water Bottle",
        "price": 22.50,
        "stock": 200,
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Cork Yoga Mat",
        "price": 49.99,
        "stock": 30,
        "image_url": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Adjustable Dumbbell Set",
        "price": 189.99,
        "stock": 12,
        "image_url": "https://images.unsplash.com/photo-1638536532686-d610adfc8e5c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "High-Density Foam Roller",
        "price": 19.99,
        "stock": 50,
        "image_url": "https://images.unsplash.com/photo-1600881333168-2ef49b341f30?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Resistance Bands Kit",
        "price": 15.99,
        "stock": 100,
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "French Press Coffee Maker",
        "price": 27.99,
        "stock": 40,
        "image_url": "https://images.unsplash.com/photo-1577968897866-be8441db7a67?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Electric Milk Frother",
        "price": 12.99,
        "stock": 80,
        "image_url": "https://images.unsplash.com/photo-1578593139857-e6f7ec62f1c8?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Damascus Steel Chef Knife",
        "price": 89.00,
        "stock": 20,
        "image_url": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Ceramic Coffee Mug",
        "price": 14.99,
        "stock": 110,
        "image_url": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Double-Walled Glass Cups",
        "price": 18.99,
        "stock": 65,
        "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Vertical Ergonomic Mouse",
        "price": 39.99,
        "stock": 45,
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "4K Computer Monitor",
        "price": 329.99,
        "stock": 10,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Laptop Stand Holder",
        "price": 24.99,
        "stock": 75,
        "image_url": "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Felt Desk Mat",
        "price": 19.50,
        "stock": 90,
        "image_url": "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Ambient LED Light Strip",
        "price": 15.99,
        "stock": 130,
        "image_url": "https://images.unsplash.com/photo-1565814636199-ae8133055c1c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Smart Home Assistant Plug",
        "price": 11.99,
        "stock": 160,
        "image_url": "https://images.unsplash.com/photo-1558002038-1055907df827?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Aromatherapy Diffuser",
        "price": 29.99,
        "stock": 42,
        "image_url": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Handmade Scented Candle",
        "price": 16.50,
        "stock": 85,
        "image_url": "https://images.unsplash.com/photo-1603006905003-be475563bc59?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Indoor Bonsai Tree",
        "price": 45.00,
        "stock": 8,
        "image_url": "https://images.unsplash.com/photo-1613143341151-576f30d075eb?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Self-Watering Planter",
        "price": 18.00,
        "stock": 50,
        "image_url": "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Canvas Tote Bag",
        "price": 12.00,
        "stock": 200,
        "image_url": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Leather Passport Holder",
        "price": 28.00,
        "stock": 35,
        "image_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Stainless Steel Straws",
        "price": 7.99,
        "stock": 300,
        "image_url": "https://images.unsplash.com/photo-1592861956120-e524fc739696?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Cast Iron Skillet",
        "price": 34.99,
        "stock": 28,
        "image_url": "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Bamboo Cutting Board",
        "price": 21.99,
        "stock": 60,
        "image_url": "https://images.unsplash.com/photo-1574634534894-89d7576c8259?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Herb Garden Starter Kit",
        "price": 24.99,
        "stock": 45,
        "image_url": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Automatic Soap Dispenser",
        "price": 19.99,
        "stock": 70,
        "image_url": "https://images.unsplash.com/photo-1608248597279-f99d160bfcbc?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Memory Foam Pillow",
        "price": 39.99,
        "stock": 30,
        "image_url": "https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Soft Cotton Bath Towel",
        "price": 14.50,
        "stock": 120,
        "image_url": "https://images.unsplash.com/photo-1563453392212-326f5e854473?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Compact Travel Umbrella",
        "price": 15.99,
        "stock": 90,
        "image_url": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Rechargeable Hand Warmer",
        "price": 18.50,
        "stock": 65,
        "image_url": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Running Waist Pack",
        "price": 12.99,
        "stock": 110,
        "image_url": "https://images.unsplash.com/photo-1530143311094-34d807799e8f?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Waterproof Phone Pouch",
        "price": 9.99,
        "stock": 150,
        "image_url": "https://images.unsplash.com/photo-1523206489230-c012c64b2b48?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Reusable Food Storage Bags",
        "price": 16.99,
        "stock": 80,
        "image_url": "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Beeswax Food Wraps",
        "price": 13.50,
        "stock": 95,
        "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Desk Fountain Pen",
        "price": 26.00,
        "stock": 40,
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Hardcover Bullet Journal",
        "price": 18.99,
        "stock": 85,
        "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Gel Ink Pens Set",
        "price": 8.50,
        "stock": 140,
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Adjustable Laptop Table",
        "price": 39.99,
        "stock": 35,
        "image_url": "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=80"
    }
]

def seed_db():
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='Gokulj7959$',
            database='fakedb',
            port=3030,
        )
        print("Connected to MySQL database successfully!")
        
        inserted_count = 0
        updated_count = 0
        
        with connection.cursor() as cursor:
            # Check existing products
            cursor.execute("SELECT name FROM products")
            existing_names = {row[0] for row in cursor.fetchall()}
            
            for p in products_seed:
                if p["name"] in existing_names:
                    # Update details (price, stock, image_url) for existing products to make them look premium
                    print(f"Product '{p['name']}' already exists. Updating price, stock, and image...")
                    cursor.execute(
                        "UPDATE products SET price = %s, stock = %s, image_url = %s WHERE name = %s",
                        (p["price"], p["stock"], p["image_url"], p["name"])
                    )
                    updated_count += 1
                else:
                    # Insert new product
                    print(f"Inserting product '{p['name']}'...")
                    cursor.execute(
                        "INSERT INTO products (name, price, stock, image_url) VALUES (%s, %s, %s, %s)",
                        (p["name"], p["price"], p["stock"], p["image_url"])
                    )
                    inserted_count += 1
            
            connection.commit()
            print(f"\nDone! Seeding completed: {inserted_count} new products inserted, {updated_count} products updated.")
            
    except Exception as e:
        print("Failed to seed database:", e)
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    seed_db()

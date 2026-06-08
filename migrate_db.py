import pymysql

def migrate():
    try:
        # Establish connection to the local MySQL database
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='Gokulj7959$',
            database='fakedb',
            port=3030,
        )
        print("Connected to MySQL database successfully!")
        
        with connection.cursor() as cursor:
            # Check if image_url column already exists
            cursor.execute("DESCRIBE products")
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            
            if 'image_url' not in column_names:
                print("Adding 'image_url' column to 'products' table...")
                cursor.execute("ALTER TABLE products ADD COLUMN image_url VARCHAR(500) DEFAULT NULL")
                print("Column added successfully!")
            else:
                print("'image_url' column already exists in 'products' table.")
            
            # Seed curated high-quality stock photo URLs for existing products
            seeds = {
                "Wireless Mouse": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80",
                "Mechanical Keyboard": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
                "USB-C Hub": "https://images.unsplash.com/photo-1468495244123-6c6c332eeece?w=600&auto=format&fit=crop&q=80",
                "Webcam HD": "https://images.unsplash.com/photo-1603481588273-2f908a9a7a1b?w=600&auto=format&fit=crop&q=80",
                "watch": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80",
                "GEFORCE RTX 5010": "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=600&auto=format&fit=crop&q=80"
            }
            
            for product_name, url in seeds.items():
                print(f"Updating image for '{product_name}'...")
                cursor.execute(
                    "UPDATE products SET image_url = %s WHERE name = %s AND (image_url IS NULL OR image_url = '')",
                    (url, product_name)
                )
            
            connection.commit()
            print("Database migration and image seeding completed successfully!")
            
    except Exception as e:
        print("Migration failed:", e)
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    migrate()
